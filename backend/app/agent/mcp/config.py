"""MCP server configuration parsing.

Reads MCP server definitions from YAML config or environment.

Example config::

    mcp_servers:
      filesystem:
        command: "npx"
        args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        timeout: 120
      remote_api:
        url: "https://my-mcp-server.example.com/mcp"
        headers:
          Authorization: "Bearer sk-..."
        transport: sse
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _interpolate_env_vars(config: dict) -> dict:
    """Replace ${ENV_VAR} placeholders with environment variable values."""
    result = {}
    for key, value in config.items():
        if isinstance(value, str):
            result[key] = re.sub(
                r'\$\{(\w+)\}',
                lambda m: os.environ.get(m.group(1), m.group(0)),
                value,
            )
        elif isinstance(value, dict):
            result[key] = _interpolate_env_vars(value)
        elif isinstance(value, list):
            result[key] = [
                re.sub(r'\$\{(\w+)\}', lambda m: os.environ.get(m.group(1), m.group(0)), v)
                if isinstance(v, str) else v
                for v in value
            ]
        else:
            result[key] = value
    return result


def load_mcp_config(config_path: Optional[str] = None) -> Dict[str, dict]:
    """Load MCP server configurations.

    Args:
        config_path: Path to YAML config file, or JSON string, or None.
    """
    if not config_path:
        return {}

    config_path = config_path.strip()

    # JSON string
    if config_path.startswith("{"):
        try:
            raw = json.loads(config_path)
            servers = raw.get("mcp_servers", raw)
            return {name: _interpolate_env_vars(cfg) for name, cfg in servers.items()}
        except json.JSONDecodeError as e:
            logger.error("Failed to parse MCP config JSON: %s", e)
            return {}

    # YAML file
    path = Path(config_path)
    if not path.exists():
        logger.warning("MCP config file not found: %s", path)
        return {}

    try:
        import yaml
        with open(path) as f:
            raw = yaml.safe_load(f)
        servers = raw.get("mcp_servers", {})
        if not isinstance(servers, dict):
            return {}
        return {name: _interpolate_env_vars(cfg) for name, cfg in servers.items()}
    except Exception as e:
        logger.error("Failed to load MCP config from %s: %s", path, e)
        return {}
