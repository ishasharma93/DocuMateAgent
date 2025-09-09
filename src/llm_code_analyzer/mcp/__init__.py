"""
Model Context Protocol (MCP) server-client implementation for Azure DevOps and GitHub integration
"""

from .server import MCPServer
from .client import MCPClient
from .azure_devops_client import AzureDevOpsClient
from .github_client import GitHubMCPClient

__all__ = ['MCPServer', 'MCPClient', 'AzureDevOpsClient', 'GitHubMCPClient']