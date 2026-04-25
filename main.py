import sys
import argparse
import os

from src.agent import AntiAgent


def main():
    parser = argparse.ArgumentParser(description="Anti — Autonomous Evolving System")
    parser.add_argument(
        "--mcp",
        action="store_true",
        help="Run as MCP server (JSON-RPC over stdin/stdout)",
    )
    args = parser.parse_args()

    if args.mcp:
        # MCP server mode: defer import to avoid initializing the agent
        # infrastructure (LLM, memory, etc.) when only the MCP protocol
        # handler is needed.
        from src.mcp_server import main as mcp_main
        mcp_main()
    else:
        # Interactive agent mode
        agent = AntiAgent()
        agent.run()


if __name__ == "__main__":
    main()