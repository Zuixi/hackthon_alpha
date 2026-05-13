"""Tool registry — register, discover, and dispatch agent tools.

Simplified from Hermes tools/registry.py. Each tool registers a name,
schema, and async handler. The registry provides OpenAI-format definitions
for the LLM and dispatches calls by name.

Includes repair_tool_args / coerce_tool_args for robustness against
malformed LLM outputs.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolEntry:
    name: str
    schema: Dict[str, Any]
    handler: Callable
    is_async: bool = True
    description: str = ""


def tool_error(message: str, **extra) -> str:
    result = {"success": False, "error": message}
    result.update(extra)
    return json.dumps(result, ensure_ascii=False)


def tool_result(data: Any) -> str:
    if isinstance(data, str):
        return data
    return json.dumps(data, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Argument repair & type coercion
# ---------------------------------------------------------------------------

def repair_tool_args(raw_json: str) -> str:
    """Try to fix common LLM JSON errors: trailing commas, unquoted keys,
    unclosed braces/brackets, single-quoted strings."""
    if not raw_json or not raw_json.strip():
        return "{}"
    s = raw_json.strip()

    # Balance unclosed braces/brackets (close inner first)
    open_braces = s.count("{") - s.count("}")
    open_brackets = s.count("[") - s.count("]")
    if open_brackets > 0:
        s += "]" * open_brackets
    if open_braces > 0:
        s += "}" * open_braces

    # Remove trailing commas before } or ]
    s = re.sub(r",\s*([}\]])", r"\1", s)

    # Replace single quotes with double quotes (simple heuristic)
    try:
        json.loads(s)
        return s
    except json.JSONDecodeError:
        pass

    try:
        s2 = s.replace("'", '"')
        json.loads(s2)
        return s2
    except (json.JSONDecodeError, ValueError):
        pass

    # Try wrapping bare value in braces
    if not s.startswith("{") and not s.startswith("["):
        try:
            wrapped = "{" + s + "}"
            json.loads(wrapped)
            return wrapped
        except (json.JSONDecodeError, ValueError):
            pass

    return s


def coerce_tool_args(args: dict, schema: dict) -> dict:
    """Cast argument values to the types declared in the JSON schema."""
    properties = schema.get("properties", {})
    if not properties:
        return args

    coerced = dict(args)
    for key, prop in properties.items():
        if key not in coerced:
            continue
        val = coerced[key]
        ptype = prop.get("type", "")

        try:
            if ptype == "integer" and not isinstance(val, int):
                coerced[key] = int(val)
            elif ptype == "number" and not isinstance(val, (int, float)):
                coerced[key] = float(val)
            elif ptype == "boolean" and not isinstance(val, bool):
                if isinstance(val, str):
                    coerced[key] = val.lower() in ("true", "1", "yes")
                else:
                    coerced[key] = bool(val)
            elif ptype == "string" and not isinstance(val, str):
                coerced[key] = str(val)
        except (ValueError, TypeError):
            pass

    return coerced


class ToolRegistry:
    """Central registry for agent tools."""

    def __init__(self):
        self._tools: Dict[str, ToolEntry] = {}

    def register(
        self,
        name: str,
        schema: Dict[str, Any],
        handler: Callable,
        is_async: bool = True,
        description: str = "",
    ) -> None:
        if name in self._tools:
            logger.warning("Overwriting tool registration: %s", name)
        self._tools[name] = ToolEntry(
            name=name,
            schema=schema,
            handler=handler,
            is_async=is_async,
            description=description or schema.get("description", ""),
        )

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def get_tool_schema(self, name: str) -> Dict[str, Any]:
        """Return input_schema for a tool (for coerce_tool_args)."""
        entry = self._tools.get(name)
        if not entry:
            return {}
        return entry.schema.get("parameters", entry.schema.get("input_schema", {}))

    def get_definitions(self) -> List[Dict[str, Any]]:
        """Return tool definitions in the internal format (name, description, input_schema)."""
        defs = []
        for entry in self._tools.values():
            defs.append({
                "name": entry.name,
                "description": entry.schema.get("description", entry.description),
                "input_schema": entry.schema.get("parameters", entry.schema.get("input_schema", {})),
            })
        return defs

    async def dispatch(self, name: str, arguments: Dict[str, Any]) -> str:
        entry = self._tools.get(name)
        if not entry:
            return tool_error(f"Unknown tool: {name}")
        try:
            if entry.is_async:
                result = await entry.handler(arguments)
            else:
                result = entry.handler(arguments)
            return tool_result(result)
        except Exception as e:
            logger.error("Tool dispatch error for %s: %s", name, e)
            return tool_error(str(e))

    @property
    def tool_names(self) -> List[str]:
        return list(self._tools.keys())


registry = ToolRegistry()
