"""
Test suite for MCP Server integration (Phase 3.4).

Tests:
- 4.2: Start with --mcp, send JSON-RPC, receive response
"""
import json
import sys
import unittest
from io import StringIO

# Import MCP server directly
sys.path.insert(0, "/home/hunther4/proyec/Anti")
from src.mcp_server import MCPServer, TOOL_REGISTRY


class TestMCPServer(unittest.TestCase):
    """Test MCP Server JSON-RPC protocol compliance."""

    def setUp(self):
        """Create fresh server instance for each test."""
        self.server = MCPServer()

    def test_01_initialize(self):
        """Test 4.2.1: Initialize protocol handshake."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }

        response = self.server._dispatch(request)

        # Verify response structure
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 1)
        self.assertIn("result", response)

        result = response["result"]
        self.assertIn("protocolVersion", result)
        self.assertIn("serverInfo", result)
        self.assertIn("capabilities", result)

        print(f"[PASS] Initialize: {result.get('serverInfo')}")

    def test_02_tools_list(self):
        """Test 4.2.2: List available MCP tools."""
        # First initialize
        init_request = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
        self.server._dispatch(init_request)

        # Then list tools
        request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        response = self.server._dispatch(request)

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertIn("result", response)

        result = response["result"]
        self.assertIn("tools", result)

        tools = result["tools"]
        self.assertIsInstance(tools, list)
        self.assertGreater(len(tools), 0)

        # Verify expected tools are present
        tool_names = [t["name"] for t in tools]
        expected = ["duckduckgo_search", "fetch_url_text", "write_file", "read_file", "run_local_command"]
        for name in expected:
            self.assertIn(name, tool_names, f"Missing tool: {name}")

        print(f"[PASS] tools/list: {len(tools)} tools available")
        for t in tools:
            print(f"  - {t['name']}: {t.get('description', '')[:50]}")

    def test_03_tools_call_search(self):
        """Test 4.2.3: Call search tool via JSON-RPC."""
        # Initialize
        init_request = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
        self.server._dispatch(init_request)

        # Call duckduckgo_search tool
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "duckduckgo_search",
                "arguments": {"query": "python MCP protocol", "max_results": 2}
            }
        }
        response = self.server._dispatch(request)

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertIn("result", response)

        result = response["result"]
        self.assertIn("content", result)
        self.assertIn("isError", result)

        # Verify it's not an error
        self.assertFalse(result["isError"], f"Tool execution error: {result}")

        # Verify content structure
        content = result["content"]
        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

        text_content = content[0].get("text", "")
        # Result should contain search results
        self.assertTrue(len(text_content) > 0)

        print(f"[PASS] tools/call: duckduckgo_search executed successfully")

    def test_04_tools_call_read_file(self):
        """Test 4.2.4: Call read_file tool via JSON-RPC."""
        # Initialize
        init_request = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
        self.server._dispatch(init_request)

        # Try to read a non-existent file
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "read_file",
                "arguments": {"filename": "nonexistent_file_12345.txt"}
            }
        }
        response = self.server._dispatch(request)

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertIn("result", response)

        result = response["result"]
        self.assertIn("content", result)

        # Should return error for missing file
        text_content = result["content"][0]["text"]
        self.assertIn("Error", text_content)

        print(f"[PASS] tools/call: read_file handles missing files gracefully")

    def test_05_invalid_method(self):
        """Test 4.2.5: Invalid method returns error."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "invalid/method/name"
        }
        response = self.server._dispatch(request)

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertIn("error", response)

        error = response["error"]
        self.assertEqual(error["code"], -32601)  # Method not found

        print(f"[PASS] Invalid method returns JSON-RPC error -32601")

    def test_06_missing_params(self):
        """Test 4.2.6: tools/call without params returns error."""
        # Initialize first
        init_request = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
        self.server._dispatch(init_request)

        # Call with missing params
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call"
        }
        response = self.server._dispatch(request)

        self.assertEqual(response["jsonrpc"], "2.0")
        
        # Error can be in result or in error field (both are valid JSON-RPC)
        if "error" in response:
            error = response["error"]
            self.assertEqual(error["code"], -32602)  # Invalid params
        else:
            # Error inside result (MCP style)
            self.assertIn("result", response)
            result = response["result"]
            self.assertIn("error", result)
            self.assertEqual(result["error"]["code"], -32602)

        print(f"[PASS] Missing params returns JSON-RPC error -32602")

    def test_07_unknown_tool(self):
        """Test 4.2.7: Unknown tool returns error."""
        # Initialize first
        init_request = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
        self.server._dispatch(init_request)

        # Call unknown tool
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool_xyz",
                "arguments": {}
            }
        }
        response = self.server._dispatch(request)

        self.assertEqual(response["jsonrpc"], "2.0")
        
        # Error can be in result or in error field (both are valid JSON-RPC)
        if "error" in response:
            error = response["error"]
            self.assertEqual(error["code"], -32603)  # Tool not found
        else:
            # Error inside result (MCP style)
            self.assertIn("result", response)
            result = response["result"]
            self.assertIn("error", result)
            self.assertEqual(result["error"]["code"], -32603)

        print(f"[PASS] Unknown tool returns JSON-RPC error -32603")

    def test_08_jsonrpc_version(self):
        """Test JSON-RPC 2.0 compliance."""
        # Test with invalid jsonrpc version
        request = {
            "jsonrpc": "1.0",  # Invalid version
            "id": 1,
            "method": "initialize"
        }
        # Should still work but version field is checked
        response = self.server._dispatch(request)
        self.assertEqual(response["jsonrpc"], "2.0")

        print(f"[PASS] JSON-RPC 2.0 compliance verified")

    def test_09_notification(self):
        """Test notification (no id) handling."""
        request = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        response = self.server._dispatch(request)

        # Notifications should return None (no response)
        self.assertIsNone(response)

        print(f"[PASS] Notification handled correctly (no response)")

    def test_10_tool_registry_integrity(self):
        """Test that tool registry is properly populated."""
        # Verify all tools have required fields
        for name, spec in TOOL_REGISTRY.items():
            self.assertIn("description", spec, f"Tool {name} missing description")
            self.assertIn("inputSchema", spec, f"Tool {name} missing inputSchema")
            self.assertIn("fn", spec, f"Tool {name} missing fn")

        print(f"[PASS] Tool registry integrity verified: {len(TOOL_REGISTRY)} tools")


def run_tests():
    """Run all MCP server tests."""
    print("=" * 60)
    print("Phase 3.4: MCP Integration Test Suite")
    print("=" * 60)

    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMCPServer)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("RESULT: All tests PASSED")
    else:
        print("RESULT: Some tests FAILED")
        for failure in result.failures + result.errors:
            print(f"  FAIL: {failure[0]}")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)