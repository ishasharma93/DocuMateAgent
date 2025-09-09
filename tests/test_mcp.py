"""
Tests for MCP (Model Context Protocol) server-client implementations
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import json

from src.llm_code_analyzer.mcp.server import MCPServer, MCPRequest, MCPResponse
from src.llm_code_analyzer.mcp.client import MCPClient
from src.llm_code_analyzer.mcp.azure_devops_client import AzureDevOpsClient
from src.llm_code_analyzer.mcp.github_client import GitHubMCPClient


class TestMCPServer(unittest.TestCase):
    """Test cases for MCP Server base class"""
    
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
    
    def test_add_resource(self):
        """Test resource addition"""
        test_data = {"key": "value", "number": 42}
        self.server.add_resource("test_resource", test_data, "Test resource")
        
        self.assertIn("test_resource", self.server.resources)
        self.assertEqual(self.server.resources["test_resource"]["data"], test_data)
    
    async def test_list_resources(self):
        """Test resources listing"""
        self.server.add_resource("test_resource", {"test": "data"})
        
        request = MCPRequest(method="resources/list", params={})
        response = await self.server.handle_request(request)
        
        self.assertIsNone(response.error)
        self.assertIn("resources", response.result)
        self.assertEqual(len(response.result["resources"]), 1)


class TestMCPClient(unittest.TestCase):
    """Test cases for MCP Client"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = MCPClient()
    
    @patch('aiohttp.ClientSession.post')
    async def test_http_request(self, mock_post):
        """Test HTTP request handling"""
        mock_response = Mock()
        mock_response.json = AsyncMock(return_value={
            "jsonrpc": "2.0",
            "result": {"tools": []},
            "id": "1"
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        
        self.client.server_url = "http://test-server"
        self.client.session = Mock()
        
        request = MCPRequest(method="tools/list", params={})
        response = await self.client._send_http_request(request)
        
        self.assertIsNone(response.error)
        self.assertEqual(response.result["tools"], [])


class TestAzureDevOpsClient(unittest.TestCase):
    """Test cases for Azure DevOps MCP Client"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = AzureDevOpsClient(
            organization="test-org",
            personal_access_token="test-pat"
        )
    
    def test_initialization(self):
        """Test Azure DevOps client initialization"""
        self.assertEqual(self.client.organization, "test-org")
        self.assertEqual(self.client.personal_access_token, "test-pat")
        self.assertIsNotNone(self.client.auth_header)
        self.assertEqual(self.client.name, "azure_devops")
    
    def test_tools_setup(self):
        """Test that Azure DevOps tools are properly registered"""
        expected_tools = [
            "list_repositories",
            "get_repository_info", 
            "get_repository_contents",
            "get_file_content",
            "get_commits",
            "get_pull_requests"
        ]
        
        for tool_name in expected_tools:
            self.assertIn(tool_name, self.client.tools)
    
    @patch('aiohttp.ClientSession.get')
    async def test_list_repositories(self, mock_get):
        """Test listing repositories"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "value": [
                {"name": "test-repo", "id": "123", "url": "https://test.com"}
            ],
            "count": 1
        })
        mock_get.return_value.__aenter__.return_value = mock_response
        
        self.client.session = Mock()
        result = await self.client._list_repositories(project="test-project")
        
        self.assertIn("value", result)
        self.assertEqual(len(result["value"]), 1)
        self.assertEqual(result["value"][0]["name"], "test-repo")


class TestGitHubMCPClient(unittest.TestCase):
    """Test cases for GitHub MCP Client"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = GitHubMCPClient(github_token="test-token")
    
    def test_initialization(self):
        """Test GitHub client initialization"""
        self.assertEqual(self.client.github_token, "test-token")
        self.assertEqual(self.client.name, "github")
    
    def test_tools_setup(self):
        """Test that GitHub tools are properly registered"""
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
            self.assertIn(tool_name, self.client.tools)
    
    @patch('aiohttp.ClientSession.get')
    async def test_get_repository_info(self, mock_get):
        """Test getting repository information"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "description": "Test repository",
            "language": "Python"
        })
        mock_get.return_value.__aenter__.return_value = mock_response
        
        self.client.session = Mock()
        result = await self.client._get_repository_info("owner", "test-repo")
        
        self.assertEqual(result["name"], "test-repo")
        self.assertEqual(result["language"], "Python")
    
    @patch('aiohttp.ClientSession.get')
    async def test_get_languages(self, mock_get):
        """Test getting repository languages"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "Python": 15234,
            "JavaScript": 8456,
            "CSS": 2341
        })
        mock_get.return_value.__aenter__.return_value = mock_response
        
        self.client.session = Mock()
        result = await self.client._get_languages("owner", "test-repo")
        
        self.assertIn("Python", result)
        self.assertIn("JavaScript", result)
        self.assertEqual(result["Python"], 15234)


class TestMCPIntegration(unittest.TestCase):
    """Integration tests for MCP components"""
    
    async def test_server_client_communication(self):
        """Test communication between server and client"""
        # Create a test server
        class TestServer(MCPServer):
            def _setup_tools(self):
                self.register_tool(
                    "echo",
                    lambda message: {"echo": message},
                    "Echo tool",
                    {"message": {"type": "string"}}
                )
        
        server = TestServer("test", "1.0.0")
        
        # Test direct communication (simulating embedded server)
        request = MCPRequest(method="tools/list", params={})
        response = await server.handle_request(request)
        
        self.assertIsNone(response.error)
        self.assertEqual(len(response.result["tools"]), 1)
        self.assertEqual(response.result["tools"][0]["name"], "echo")
        
        # Test tool call
        call_request = MCPRequest(
            method="tools/call",
            params={"name": "echo", "arguments": {"message": "Hello MCP"}}
        )
        call_response = await server.handle_request(call_request)
        
        self.assertIsNone(call_response.error)
        content = json.loads(call_response.result["content"][0]["text"])
        self.assertEqual(content["echo"], "Hello MCP")


def run_async_test(coro):
    """Helper function to run async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Convert async test methods to sync for unittest
for cls in [TestMCPServer, TestMCPClient, TestAzureDevOpsClient, TestGitHubMCPClient, TestMCPIntegration]:
    for method_name in dir(cls):
        if method_name.startswith('test_') and asyncio.iscoroutinefunction(getattr(cls, method_name)):
            method = getattr(cls, method_name)
            setattr(cls, method_name, lambda self, m=method: run_async_test(m(self)))


if __name__ == '__main__':
    unittest.main()