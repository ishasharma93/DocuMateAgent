"""
Simplified tests for MCP (Model Context Protocol) core functionality
"""

import unittest
import asyncio
from unittest.mock import Mock
import json

from src.llm_code_analyzer.mcp.server import MCPServer, MCPRequest, MCPResponse


class TestMCPServerBasic(unittest.TestCase):
    """Basic test cases for MCP Server functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        class TestServer(MCPServer):
            def _setup_tools(self):
                self.register_tool(
                    "test_tool",
                    self.test_handler,
                    "A test tool",
                    {"param1": {"type": "string", "description": "Test parameter"}}
                )
            
            def test_handler(self, param1: str) -> dict:
                return {"result": f"Hello {param1}"}
        
        self.server = TestServer("test_server", "1.0.0")
    
    def test_initialization(self):
        """Test server initialization"""
        self.assertEqual(self.server.name, "test_server")
        self.assertEqual(self.server.version, "1.0.0")
        self.assertIn("test_tool", self.server.tools)
    
    def test_tool_registration(self):
        """Test tool registration"""
        self.server.register_tool(
            "new_tool",
            lambda x: {"value": x},
            "New test tool",
            {"input": {"type": "string"}}
        )
        self.assertIn("new_tool", self.server.tools)
    
    def test_add_resource(self):
        """Test resource addition"""
        test_data = {"key": "value", "number": 42}
        self.server.add_resource("test_resource", test_data, "Test resource")
        
        self.assertIn("test_resource", self.server.resources)
        self.assertEqual(self.server.resources["test_resource"]["data"], test_data)


class TestMCPServerAsync(unittest.TestCase):
    """Async test cases for MCP Server"""
    
    def setUp(self):
        """Set up test fixtures"""
        class TestServer(MCPServer):
            def _setup_tools(self):
                self.register_tool(
                    "test_tool",
                    self.test_handler,
                    "A test tool",
                    {"param1": {"type": "string", "description": "Test parameter"}}
                )
            
            def test_handler(self, param1: str) -> dict:
                return {"result": f"Hello {param1}"}
        
        self.server = TestServer("test_server", "1.0.0")
    
    async def test_list_tools(self):
        """Test tools listing"""
        request = MCPRequest(method="tools/list", params={})
        response = await self.server.handle_request(request)
        
        self.assertIsNone(response.error)
        self.assertIn("tools", response.result)
        self.assertEqual(len(response.result["tools"]), 1)
        self.assertEqual(response.result["tools"][0]["name"], "test_tool")
    
    async def test_call_tool(self):
        """Test tool calling"""
        request = MCPRequest(
            method="tools/call",
            params={"name": "test_tool", "arguments": {"param1": "World"}}
        )
        response = await self.server.handle_request(request)
        
        self.assertIsNone(response.error)
        self.assertIn("content", response.result)
        
        # Parse the JSON response
        content_text = response.result["content"][0]["text"]
        result = json.loads(content_text)
        self.assertEqual(result["result"], "Hello World")
    
    async def test_call_nonexistent_tool(self):
        """Test calling non-existent tool"""
        request = MCPRequest(
            method="tools/call",
            params={"name": "nonexistent", "arguments": {}}
        )
        response = await self.server.handle_request(request)
        
        self.assertIsNotNone(response.error)
        self.assertEqual(response.error["code"], -32602)
    
    async def test_list_resources(self):
        """Test resources listing"""
        self.server.add_resource("test_resource", {"test": "data"})
        
        request = MCPRequest(method="resources/list", params={})
        response = await self.server.handle_request(request)
        
        self.assertIsNone(response.error)
        self.assertIn("resources", response.result)
        self.assertEqual(len(response.result["resources"]), 1)


class TestMCPClientConfiguration(unittest.TestCase):
    """Test MCP client configurations"""
    
    def test_azure_devops_client_configuration(self):
        """Test Azure DevOps client configuration"""
        from src.llm_code_analyzer.mcp.azure_devops_client import AzureDevOpsClient
        
        client = AzureDevOpsClient(
            organization="test-org",
            personal_access_token="test-pat"
        )
        
        self.assertEqual(client.organization, "test-org")
        self.assertEqual(client.personal_access_token, "test-pat")
        self.assertEqual(client.name, "azure_devops")
        self.assertIsNotNone(client.auth_header)
    
    def test_github_client_configuration(self):
        """Test GitHub client configuration"""
        from src.llm_code_analyzer.mcp.github_client import GitHubMCPClient
        
        client = GitHubMCPClient(github_token="test-token")
        
        self.assertEqual(client.github_token, "test-token")
        self.assertEqual(client.name, "github")
    
    def test_azure_devops_tools_setup(self):
        """Test Azure DevOps tools are registered"""
        from src.llm_code_analyzer.mcp.azure_devops_client import AzureDevOpsClient
        
        client = AzureDevOpsClient(
            organization="test-org",
            personal_access_token="test-pat"
        )
        
        expected_tools = [
            "list_repositories",
            "get_repository_info", 
            "get_repository_contents",
            "get_file_content",
            "get_commits",
            "get_pull_requests"
        ]
        
        for tool_name in expected_tools:
            self.assertIn(tool_name, client.tools)
    
    def test_github_tools_setup(self):
        """Test GitHub tools are registered"""
        from src.llm_code_analyzer.mcp.github_client import GitHubMCPClient
        
        client = GitHubMCPClient(github_token="test-token")
        
        expected_tools = [
            "get_repository_info",
            "get_repository_contents",
            "get_file_content",
            "get_commits",
            "get_pull_requests",
            "get_branches",
            "get_languages",
            "search_code"
        ]
        
        for tool_name in expected_tools:
            self.assertIn(tool_name, client.tools)


def run_async_test(coro):
    """Helper function to run async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Convert async test methods to sync for unittest
for method_name in dir(TestMCPServerAsync):
    if method_name.startswith('test_') and asyncio.iscoroutinefunction(getattr(TestMCPServerAsync, method_name)):
        method = getattr(TestMCPServerAsync, method_name)
        setattr(TestMCPServerAsync, method_name, lambda self, m=method: run_async_test(m(self)))


if __name__ == '__main__':
    unittest.main()