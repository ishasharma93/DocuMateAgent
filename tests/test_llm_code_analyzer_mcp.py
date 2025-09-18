"""
Tests for enhanced LLMCodeAnalyzer with MCP integration
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import os

from src.llm_code_analyzer import LLMCodeAnalyzer


class TestLLMCodeAnalyzerMCP(unittest.TestCase):
    """Test cases for LLMCodeAnalyzer MCP integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create analyzer without real credentials but with MCP enabled
        self.analyzer = LLMCodeAnalyzer(
            enable_mcp=True,
            azure_devops_org="test-org",
            azure_devops_pat="test-pat",
            github_token="test-token"
        )
    
    def test_mcp_initialization(self):
        """Test MCP components are initialized when enabled"""
        self.assertTrue(self.analyzer.mcp_enabled)
        self.assertIsNotNone(self.analyzer.azure_devops_client)
        self.assertIsNotNone(self.analyzer.github_mcp_client)
    
    def test_mcp_disabled_initialization(self):
        """Test analyzer works when MCP is disabled"""
        analyzer = LLMCodeAnalyzer(enable_mcp=False)
        self.assertFalse(analyzer.mcp_enabled)
        self.assertIsNone(analyzer.azure_devops_client)
        self.assertIsNone(analyzer.github_mcp_client)
    
    @patch.dict(os.environ, {'AZURE_DEVOPS_ORGANIZATION': 'env-org', 'GITHUB_TOKEN': 'env-token'})
    def test_environment_credential_detection(self):
        """Test MCP clients use environment variables"""
        analyzer = LLMCodeAnalyzer(enable_mcp=True)
        self.assertTrue(analyzer.mcp_enabled)
        # Should initialize clients from environment variables
        self.assertIsNotNone(analyzer.azure_devops_client)
        self.assertIsNotNone(analyzer.github_mcp_client)
    
    async def test_github_url_parsing(self):
        """Test GitHub repository URL parsing"""
        if not self.analyzer.mcp_enabled:
            self.skipTest("MCP not available")
        
        # Mock the GitHub MCP client methods
        with patch.object(self.analyzer.github_mcp_client, '_get_repository_info') as mock_repo_info:
            mock_repo_info.return_value = {"name": "test-repo", "owner": {"login": "test-owner"}}
            
            with patch.object(self.analyzer.github_mcp_client, '_get_repository_contents') as mock_contents:
                mock_contents.return_value = []
                
                with patch.object(self.analyzer.github_mcp_client, '_get_languages') as mock_languages:
                    mock_languages.return_value = {"Python": 100}
                    
                    with patch.object(self.analyzer.github_mcp_client, '_get_commits') as mock_commits:
                        mock_commits.return_value = {"commits": []}
                        
                        with patch.object(self.analyzer.github_mcp_client, '_get_branches') as mock_branches:
                            mock_branches.return_value = {"branches": []}
                            
                            with patch.object(self.analyzer.github_mcp_client, '_get_pull_requests') as mock_prs:
                                mock_prs.return_value = {"pull_requests": []}
                                
                                # Test valid GitHub URL
                                result = await self.analyzer.analyze_repository_with_mcp(
                                    "https://github.com/test-owner/test-repo",
                                    "github"
                                )
                                
                                self.assertIn("repository_info", result)
                                mock_repo_info.assert_called_once_with("test-owner", "test-repo")
    
    async def test_azure_devops_url_parsing(self):
        """Test Azure DevOps repository URL parsing"""
        if not self.analyzer.mcp_enabled:
            self.skipTest("MCP not available")
        
        # Mock the Azure DevOps MCP client methods
        with patch.object(self.analyzer.azure_devops_client, '_get_repository_info') as mock_repo_info:
            mock_repo_info.return_value = {"name": "test-repo", "project": {"name": "test-project"}}
            
            with patch.object(self.analyzer.azure_devops_client, '_get_repository_contents') as mock_contents:
                mock_contents.return_value = {"value": []}
                
                with patch.object(self.analyzer.azure_devops_client, '_get_commits') as mock_commits:
                    mock_commits.return_value = {"value": []}
                    
                    with patch.object(self.analyzer.azure_devops_client, '_get_pull_requests') as mock_prs:
                        mock_prs.return_value = {"value": []}
                        
                        # Test valid Azure DevOps URL
                        result = await self.analyzer.analyze_repository_with_mcp(
                            "https://dev.azure.com/test-org/test-project/_git/test-repo",
                            "azure_devops"
                        )
                        
                        self.assertIn("repository_info", result)
                        mock_repo_info.assert_called_once_with("test-project", "test-repo")
    
    async def test_invalid_repository_url(self):
        """Test handling of invalid repository URLs"""
        if not self.analyzer.mcp_enabled:
            self.skipTest("MCP not available")
        
        # Test invalid GitHub URL
        result = await self.analyzer.analyze_repository_with_mcp(
            "https://invalid-url.com/repo",
            "github"
        )
        self.assertIn("error", result)
        self.assertIn("Invalid GitHub repository URL", result["error"])
    
    async def test_unsupported_repository_type(self):
        """Test handling of unsupported repository types"""
        if not self.analyzer.mcp_enabled:
            self.skipTest("MCP not available")
        
        result = await self.analyzer.analyze_repository_with_mcp(
            "https://gitlab.com/user/repo",
            "gitlab"
        )
        self.assertIn("error", result)
        self.assertIn("Unsupported repository type", result["error"])
    
    async def test_github_file_retrieval(self):
        """Test GitHub file content retrieval"""
        if not self.analyzer.mcp_enabled:
            self.skipTest("MCP not available")
        
        # Mock GitHub API responses
        mock_contents = [
            {
                "type": "file",
                "path": "main.py",
                "size": 1000
            },
            {
                "type": "dir",
                "path": "src"
            }
        ]
        
        mock_file_content = {
            "decoded_content": "print('Hello, World!')\n"
        }
        
        with patch.object(self.analyzer.github_mcp_client, '_get_repository_contents') as mock_get_contents:
            mock_get_contents.return_value = mock_contents
            
            with patch.object(self.analyzer.github_mcp_client, '_get_file_content') as mock_get_file:
                mock_get_file.return_value = mock_file_content
                
                files = await self.analyzer.get_mcp_repository_files(
                    "https://github.com/test-owner/test-repo",
                    "github",
                    max_files=5
                )
                
                self.assertIn("main.py", files)
                self.assertEqual(files["main.py"], "print('Hello, World!')\n")
    
    async def test_azure_devops_file_retrieval(self):
        """Test Azure DevOps file content retrieval"""
        if not self.analyzer.mcp_enabled:
            self.skipTest("MCP not available")
        
        # Mock Azure DevOps API responses
        mock_contents = {
            "value": [
                {
                    "isFolder": False,
                    "path": "/main.py",
                    "size": 1000
                }
            ]
        }
        
        mock_file_content = {
            "content": "print('Hello from Azure DevOps!')\n"
        }
        
        with patch.object(self.analyzer.azure_devops_client, '_get_repository_contents') as mock_get_contents:
            mock_get_contents.return_value = mock_contents
            
            with patch.object(self.analyzer.azure_devops_client, '_get_file_content') as mock_get_file:
                mock_get_file.return_value = mock_file_content
                
                files = await self.analyzer.get_mcp_repository_files(
                    "https://dev.azure.com/test-org/test-project/_git/test-repo",
                    "azure_devops",
                    max_files=5
                )
                
                self.assertIn("main.py", files)
                self.assertEqual(files["main.py"], "print('Hello from Azure DevOps!')\n")
    
    async def test_close_mcp_clients(self):
        """Test MCP client cleanup"""
        if not self.analyzer.mcp_enabled:
            self.skipTest("MCP not available")
        
        # Mock close methods
        with patch.object(self.analyzer.azure_devops_client, 'close') as mock_azure_close:
            with patch.object(self.analyzer.github_mcp_client, 'close') as mock_github_close:
                await self.analyzer.close_mcp_clients()
                
                mock_azure_close.assert_called_once()
                mock_github_close.assert_called_once()
    
    def test_file_extension_filtering(self):
        """Test that only supported file extensions are processed"""
        # Test that .py files are supported
        self.assertIn('.py', self.analyzer.code_extensions)
        
        # Test that common code extensions are supported
        supported_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.go', '.rs']
        for ext in supported_extensions:
            self.assertIn(ext, self.analyzer.code_extensions)


def run_async_test(coro):
    """Helper function to run async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Convert async test methods to sync for unittest
for method_name in dir(TestLLMCodeAnalyzerMCP):
    if method_name.startswith('test_') and asyncio.iscoroutinefunction(getattr(TestLLMCodeAnalyzerMCP, method_name)):
        method = getattr(TestLLMCodeAnalyzerMCP, method_name)
        setattr(TestLLMCodeAnalyzerMCP, method_name, lambda self, m=method: run_async_test(m(self)))


if __name__ == '__main__':
    unittest.main()