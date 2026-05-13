"""MCP client — connect to external MCP servers and register their tools.

Simplified from Hermes tools/mcp_tool.py. Supports stdio and HTTP/SSE transports.
Each MCP server runs in a background asyncio task. Discovered tools are registered
into the agent ToolRegistry.
"""

import asyncio
import json
import logging
import os
import threading
from typing import Any, Callable, Dict, List, Optional

from app.agent.tools.registry import ToolRegistry, tool_error

logger = logging.getLogger(__name__)

_mcp_loop: Optional[asyncio.AbstractEventLoop] = None
_mcp_thread: Optional[threading.Thread] = None
_servers: Dict[str, "MCPServerTask"] = {}


def _ensure_mcp_loop() -> asyncio.AbstractEventLoop:
    """Get or create the dedicated MCP event loop running in a daemon thread."""
    global _mcp_loop, _mcp_thread
    if _mcp_loop is not None and _mcp_loop.is_running():
        return _mcp_loop

    loop = asyncio.new_event_loop()

    def _run():
        asyncio.set_event_loop(loop)
        loop.run_forever()

    _mcp_thread = threading.Thread(target=_run, daemon=True, name="mcp-loop")
    _mcp_thread.start()
    _mcp_loop = loop
    return loop


def _run_on_mcp_loop(coro):
    """Run a coroutine on the MCP event loop and return the result."""
    loop = _ensure_mcp_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=120)


class MCPServerTask:
    """Manages a single MCP server connection."""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self._session = None
        self._task: Optional[asyncio.Task] = None
        self._ready = asyncio.Event()
        self._tools: Dict[str, Any] = {}
        self.tool_timeout = config.get("timeout", 120)

    def _is_http(self) -> bool:
        return bool(self.config.get("url"))

    async def start(self):
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._run())
        try:
            await asyncio.wait_for(self._ready.wait(), timeout=self.config.get("connect_timeout", 60))
        except asyncio.TimeoutError:
            logger.error("MCP server '%s' connection timeout", self.name)

    async def _run(self):
        try:
            if self._is_http():
                await self._run_http()
            else:
                await self._run_stdio()
        except Exception as e:
            logger.error("MCP server '%s' error: %s", self.name, e)

    async def _run_stdio(self):
        try:
            from mcp import ClientSession
            from mcp.client.stdio import stdio_client, StdioServerParameters
        except ImportError:
            logger.error("MCP SDK not installed. Run: pip install mcp")
            return

        command = self.config.get("command", "")
        args = self.config.get("args", [])
        env = {**os.environ, **(self.config.get("env") or {})}

        params = StdioServerParameters(command=command, args=args, env=env)

        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                self._session = session
                await session.initialize()
                await self._discover_tools()
                self._ready.set()
                # Keep connection alive
                try:
                    await asyncio.Future()  # block forever
                except asyncio.CancelledError:
                    pass

    async def _run_http(self):
        try:
            from mcp import ClientSession
        except ImportError:
            logger.error("MCP SDK not installed. Run: pip install mcp")
            return

        url = self.config.get("url", "")
        transport = self.config.get("transport", "").lower()
        headers = self.config.get("headers", {})

        if transport == "sse":
            try:
                from mcp.client.sse import sse_client
            except ImportError:
                logger.error("MCP SSE client not available")
                return
            async with sse_client(url, headers=headers) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    self._session = session
                    await session.initialize()
                    await self._discover_tools()
                    self._ready.set()
                    try:
                        await asyncio.Future()
                    except asyncio.CancelledError:
                        pass
        else:
            try:
                from mcp.client.streamable_http import streamablehttp_client
            except ImportError:
                try:
                    from mcp.client.streamable_http import streamable_http_client as streamablehttp_client
                except ImportError:
                    logger.error("MCP Streamable HTTP client not available")
                    return
            async with streamablehttp_client(url, headers=headers) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    self._session = session
                    await session.initialize()
                    await self._discover_tools()
                    self._ready.set()
                    try:
                        await asyncio.Future()
                    except asyncio.CancelledError:
                        pass

    async def _discover_tools(self):
        if not self._session:
            return
        result = await self._session.list_tools()
        for tool in result.tools:
            self._tools[tool.name] = tool
        logger.info("MCP server '%s': discovered %d tool(s): %s",
                     self.name, len(self._tools), list(self._tools.keys()))

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        if not self._session:
            return tool_error(f"MCP server '{self.name}' not connected")
        try:
            result = await asyncio.wait_for(
                self._session.call_tool(tool_name, arguments),
                timeout=self.tool_timeout,
            )
            parts = []
            for content in result.content:
                if hasattr(content, "text"):
                    parts.append(content.text)
                else:
                    parts.append(str(content))
            return "\n".join(parts)
        except asyncio.TimeoutError:
            return tool_error(f"MCP tool '{tool_name}' timeout ({self.tool_timeout}s)")
        except Exception as e:
            logger.error("MCP tool '%s' error: %s", tool_name, e)
            return tool_error(str(e))

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        schemas = []
        for name, tool in self._tools.items():
            schema = {
                "name": f"mcp_{self.name}_{name}",
                "description": tool.description or f"MCP tool: {name}",
                "input_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else {"type": "object", "properties": {}},
            }
            schemas.append(schema)
        return schemas

    async def shutdown(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass


def _make_tool_handler(server_name: str, tool_name: str, server: MCPServerTask):
    """Create a sync handler that bridges to the MCP async call."""
    async def handler(args: dict) -> str:
        return await server.call_tool(tool_name, args)
    return handler


def register_mcp_servers(servers_config: Dict[str, dict], tool_registry: ToolRegistry) -> List[str]:
    """Connect to MCP servers and register their tools.

    Returns list of registered tool names.
    """
    if not servers_config:
        return []

    registered = []
    loop = _ensure_mcp_loop()

    async def _connect_all():
        tasks = []
        for name, config in servers_config.items():
            if config.get("enabled") is False:
                continue
            server = MCPServerTask(name, config)
            _servers[name] = server
            tasks.append(server.start())

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        for name, server in _servers.items():
            for schema in server.get_tool_schemas():
                tool_name = schema["name"]
                original_name = tool_name.replace(f"mcp_{name}_", "", 1)
                handler = _make_tool_handler(name, original_name, server)
                tool_registry.register(
                    name=tool_name,
                    schema=schema,
                    handler=handler,
                    is_async=True,
                )
                registered.append(tool_name)

    future = asyncio.run_coroutine_threadsafe(_connect_all(), loop)
    try:
        future.result(timeout=120)
    except Exception as e:
        logger.error("MCP server registration error: %s", e)

    if registered:
        logger.info("MCP: registered %d tool(s) from %d server(s)", len(registered), len(_servers))

    return registered


def shutdown_mcp_servers():
    """Shutdown all MCP server connections."""
    if not _servers or not _mcp_loop:
        return

    async def _shutdown():
        for server in _servers.values():
            await server.shutdown()
        _servers.clear()

    future = asyncio.run_coroutine_threadsafe(_shutdown(), _mcp_loop)
    try:
        future.result(timeout=10)
    except Exception:
        pass
