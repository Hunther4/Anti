"""
MCP Server — Model Context Protocol via JSON-RPC over stdin/stdout.

This module implements the MCP specification for communication with AI clients.
Protocol: JSON-RPC 2.0 over line-delimited JSON messages on stdin/stdout.
"""
import json
import sys
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# --- Tool Registry ---

# Expose available tools from src.tools as MCP tools
from src.tools import (
    duckduckgo_search,
    fetch_url_text,
    write_file,
    read_file,
    run_local_command,
)
import src.tools as _tools_module

# Tools are exposed via their function references for direct invocation
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "duckduckgo_search": {
        "description": "Search the web using DuckDuckGo or SearxNG. Returns title, URL, and snippet for top results.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string"
                },
                "max_results": {
                    "type": "number",
                    "description": "Maximum number of results (default: 5)"
                }
            },
            "required": ["query"]
        },
        "fn": duckduckgo_search,
    },
    "fetch_url_text": {
        "description": "Fetch and extract clean text content from a URL.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch"
                }
            },
            "required": ["url"]
        },
        "fn": fetch_url_text,
    },
    "write_file": {
        "description": "Write content to a file in the workspace directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name of the file to create"
                },
                "content": {
                    "type": "string",
                    "description": "The content to write"
                }
            },
            "required": ["filename", "content"]
        },
        "fn": None,  # resolved at call time
    },
    "read_file": {
        "description": "Read content from a file in the workspace directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name of the file to read"
                }
            },
            "required": ["filename"]
        },
        "fn": None,  # resolved at call time
    },
    "run_local_command": {
        "description": "Execute a shell command locally. Security: blocks dangerous operators.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute"
                }
            },
            "required": ["command"]
        },
        "fn": run_local_command,
    },
}


def _resolve_tool_fns():
    """Resolve write_file/read_file at runtime to pass workspace path."""
    TOOL_REGISTRY["write_file"]["fn"] = _tools_module.write_file
    TOOL_REGISTRY["read_file"]["fn"] = _tools_module.read_file


# --- MCP Server Core ---


class MCPServer:
    """
    JSON-RPC 2.0 server over stdin/stdout.

    Protocol:
    - Reads each line as a JSON-RPC request
    - Writes each response as a JSON-RPC response on stdout
    - Logs errors to stderr
    """

    def __init__(self):
        _resolve_tool_fns()
        self.server_info = {
            "name": "anti-mcp-server",
            "version": "1.0.0",
        }
        self.capabilities = {
            "tools": {},
        }
        self._initialized = False

    # --- Protocol Methods ---

    def _handle_initialize(self, params: Optional[Dict]) -> Dict[str, Any]:
        """Handle initialize: negotiate protocol version."""
        self._initialized = True
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": self.server_info,
            "capabilities": self.capabilities,
            "instructions": (
                "Anti MCP Server — exposes local tools for the Anti autonomous agent. "
                "Supported tools: duckduckgo_search, fetch_url_text, write_file, read_file, run_local_command."
            ),
        }

    def _handle_tools_list(self, params: Optional[Dict]) -> Dict[str, Any]:
        """Handle tools/list: return available tools."""
        tools = []
        for name, spec in TOOL_REGISTRY.items():
            tools.append({
                "name": name,
                "description": spec["description"],
                "inputSchema": spec["inputSchema"],
            })
        return {"tools": tools}

    def _handle_tools_call(self, params: Optional[Dict]) -> Dict[str, Any]:
        """Handle tools/call: invoke a tool and return results."""
        if not params:
            return {"error": {"code": -32602, "message": "Missing params"}}

        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        if not tool_name:
            return {"error": {"code": -32602, "message": "Missing tool name"}}

        if tool_name not in TOOL_REGISTRY:
            return {"error": {"code": -32603, "message": f"Unknown tool: {tool_name}"}}

        spec = TOOL_REGISTRY[tool_name]
        fn = spec["fn"]

        if fn is None:
            return {"error": {"code": -32603, "message": f"Tool {tool_name} is not callable"}}

        try:
            import asyncio
            if asyncio.iscoroutinefunction(fn):
                result = asyncio.run(fn(**tool_args))
            else:
                result = fn(**tool_args)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(result),
                    }
                ],
                "isError": False,
            }
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error executing {tool_name}: {e}",
                    }
                ],
                "isError": True,
            }

    # --- Dispatch ---

    def _dispatch(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Dispatch a JSON-RPC request to the appropriate handler."""
        method = request.get("method")
        req_id = request.get("id")
        params = request.get("params")

        # Protocol-level errors
        if method is None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32600, "message": "Invalid Request"},
            }

        try:
            if method == "initialize":
                result = self._handle_initialize(params)
            elif method == "tools/list":
                result = self._handle_tools_list(params)
            elif method == "tools/call":
                result = self._handle_tools_call(params)
            elif method == "notifications/initialized":
                # Client signal — nothing to return
                return None
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result,
            }

        except Exception as e:
            logger.error(f"Error handling {method}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": f"Internal error: {e}"},
            }

    # --- IO Loop ---

    def run(self):
        """
        Run the MCP server loop.
        Reads JSON-RPC requests from stdin, writes responses to stdout.
        """
        _resolve_tool_fns()
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                # Malformed JSON — respond with parse error
                print(
                    json.dumps({
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": f"Parse error: {e}"},
                    }),
                    flush=True
                )
                continue

            response = self._dispatch(request)
            if response is not None:
                print(json.dumps(response), flush=True)


def main():
    """Entry point for MCP server mode."""
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()