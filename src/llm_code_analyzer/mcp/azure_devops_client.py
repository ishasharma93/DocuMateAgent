"""
Azure DevOps MCP server-client implementation for repository analysis
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional
import aiohttp
import base64

from .server import MCPServer

logger = logging.getLogger(__name__)


class AzureDevOpsClient(MCPServer):
    """
    Azure DevOps MCP server that provides tools for repository analysis
    """
    
    def __init__(self, 
                 organization: Optional[str] = None,
                 personal_access_token: Optional[str] = None,
                 api_version: str = "7.0"):
        """
        Initialize Azure DevOps MCP server
        
        Args:
            organization: Azure DevOps organization name
            personal_access_token: Personal Access Token for authentication
            api_version: API version to use
        """
        self.organization = organization or os.getenv('AZURE_DEVOPS_ORGANIZATION')
        self.personal_access_token = personal_access_token or os.getenv('AZURE_DEVOPS_PAT')
        self.api_version = api_version
        
        if not self.organization or not self.personal_access_token:
            logger.warning("Azure DevOps credentials not configured. Some functionality will be limited.")
        
        # Create auth header
        self.auth_header = None
        if self.personal_access_token:
            encoded_pat = base64.b64encode(f":{self.personal_access_token}".encode()).decode()
            self.auth_header = f"Basic {encoded_pat}"
        
        self.base_url = f"https://dev.azure.com/{self.organization}"
        self.session: Optional[aiohttp.ClientSession] = None
        
        super().__init__(name="azure_devops", version="1.0.0")
    
    def _setup_tools(self):
        """Setup Azure DevOps specific tools"""
        
        # Repository analysis tools
        self.register_tool(
            "list_repositories",
            self._list_repositories,
            "List repositories in the Azure DevOps organization",
            {
                "project": {
                    "type": "string",
                    "description": "Project name (optional, lists all projects if not specified)"
                }
            }
        )
        
        self.register_tool(
            "get_repository_info",
            self._get_repository_info,
            "Get detailed information about a specific repository",
            {
                "project": {
                    "type": "string", 
                    "description": "Project name"
                },
                "repository": {
                    "type": "string",
                    "description": "Repository name or ID"
                }
            }
        )
        
        self.register_tool(
            "get_repository_contents",
            self._get_repository_contents,
            "Get repository file contents and structure",
            {
                "project": {
                    "type": "string",
                    "description": "Project name"
                },
                "repository": {
                    "type": "string", 
                    "description": "Repository name or ID"
                },
                "path": {
                    "type": "string",
                    "description": "Path to explore (default: root)",
                    "default": ""
                },
                "recursionLevel": {
                    "type": "string",
                    "description": "Recursion level (None, OneLevel, OneLevelPlusNestedEmptyFolders, Full)",
                    "default": "OneLevel"
                }
            }
        )
        
        self.register_tool(
            "get_file_content",
            self._get_file_content,
            "Get content of a specific file",
            {
                "project": {
                    "type": "string",
                    "description": "Project name"
                },
                "repository": {
                    "type": "string",
                    "description": "Repository name or ID"
                },
                "path": {
                    "type": "string",
                    "description": "File path"
                },
                "version": {
                    "type": "string", 
                    "description": "Version descriptor (branch, tag, commit)",
                    "default": "main"
                }
            }
        )
        
        self.register_tool(
            "get_commits",
            self._get_commits,
            "Get commit history for a repository",
            {
                "project": {
                    "type": "string",
                    "description": "Project name"
                },
                "repository": {
                    "type": "string",
                    "description": "Repository name or ID" 
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name",
                    "default": "main"
                },
                "top": {
                    "type": "integer",
                    "description": "Number of commits to retrieve",
                    "default": 10
                }
            }
        )
        
        self.register_tool(
            "get_pull_requests",
            self._get_pull_requests,
            "Get pull requests for a repository", 
            {
                "project": {
                    "type": "string",
                    "description": "Project name"
                },
                "repository": {
                    "type": "string",
                    "description": "Repository name or ID"
                },
                "status": {
                    "type": "string",
                    "description": "PR status filter (active, completed, abandoned, all)",
                    "default": "active"
                }
            }
        )
    
    async def _ensure_session(self):
        """Ensure HTTP session is available"""
        if not self.session:
            headers = {}
            if self.auth_header:
                headers["Authorization"] = self.auth_header
            self.session = aiohttp.ClientSession(headers=headers)
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to Azure DevOps API"""
        await self._ensure_session()
        
        try:
            full_url = f"{self.base_url}/_apis/{url}"
            params = params or {}
            params["api-version"] = self.api_version
            
            async with self.session.get(full_url, params=params) as response:
                if response.status == 401:
                    raise Exception("Authentication failed. Check your Personal Access Token.")
                elif response.status != 200:
                    raise Exception(f"API request failed with status {response.status}: {await response.text()}")
                
                return await response.json()
        except Exception as e:
            logger.error(f"Azure DevOps API request failed: {e}")
            raise
    
    async def _list_repositories(self, project: Optional[str] = None) -> Dict[str, Any]:
        """List repositories in the organization or project"""
        if project:
            url = f"git/repositories"
            params = {"project": project}
        else:
            # List all projects first, then get repositories for each
            projects_url = "projects"
            projects_response = await self._make_request(projects_url)
            
            all_repos = []
            for project_info in projects_response.get("value", []):
                try:
                    project_name = project_info["name"]
                    repos_response = await self._make_request("git/repositories", {"project": project_name})
                    for repo in repos_response.get("value", []):
                        repo["project"] = project_name
                        all_repos.append(repo)
                except Exception as e:
                    logger.warning(f"Failed to get repositories for project {project_info.get('name')}: {e}")
            
            return {"value": all_repos, "count": len(all_repos)}
        
        return await self._make_request(url, params)
    
    async def _get_repository_info(self, project: str, repository: str) -> Dict[str, Any]:
        """Get detailed repository information"""
        url = f"git/repositories/{repository}"
        params = {"project": project}
        return await self._make_request(url, params)
    
    async def _get_repository_contents(self, 
                                     project: str, 
                                     repository: str,
                                     path: str = "",
                                     recursionLevel: str = "OneLevel") -> Dict[str, Any]:
        """Get repository contents"""
        url = f"git/repositories/{repository}/items"
        params = {
            "project": project,
            "scopePath": path if path else "/",
            "recursionLevel": recursionLevel
        }
        return await self._make_request(url, params)
    
    async def _get_file_content(self, 
                               project: str,
                               repository: str, 
                               path: str,
                               version: str = "main") -> Dict[str, Any]:
        """Get file content"""
        url = f"git/repositories/{repository}/items"
        params = {
            "project": project,
            "path": path,
            "version": version,
            "includeContent": "true"
        }
        response = await self._make_request(url, params)
        
        # Decode content if it's base64 encoded
        if response.get("contentMetadata", {}).get("encoding") == "base64":
            import base64
            content = base64.b64decode(response["content"]).decode('utf-8', errors='ignore')
            response["content"] = content
        
        return response
    
    async def _get_commits(self, 
                          project: str,
                          repository: str,
                          branch: str = "main",
                          top: int = 10) -> Dict[str, Any]:
        """Get commit history"""
        url = f"git/repositories/{repository}/commits"
        params = {
            "project": project,
            "searchCriteria.itemVersion.version": branch,
            "searchCriteria.itemVersion.versionType": "branch",
            "$top": top
        }
        return await self._make_request(url, params)
    
    async def _get_pull_requests(self,
                                project: str,
                                repository: str, 
                                status: str = "active") -> Dict[str, Any]:
        """Get pull requests"""
        url = f"git/repositories/{repository}/pullrequests"
        params = {
            "project": project,
            "searchCriteria.status": status
        }
        return await self._make_request(url, params)