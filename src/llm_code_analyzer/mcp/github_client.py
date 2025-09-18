"""
GitHub MCP server-client implementation for repository analysis
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional
import aiohttp
import base64

from .server import MCPServer

logger = logging.getLogger(__name__)


class GitHubMCPClient(MCPServer):
    """
    GitHub MCP server that provides tools for repository analysis
    """
    
    def __init__(self, 
                 github_token: Optional[str] = None,
                 api_version: str = "2022-11-28"):
        """
        Initialize GitHub MCP server
        
        Args:
            github_token: GitHub personal access token
            api_version: GitHub API version
        """
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.api_version = api_version
        
        if not self.github_token:
            logger.warning("GitHub token not configured. API rate limits will be very restrictive.")
        
        self.base_url = "https://api.github.com"
        self.session: Optional[aiohttp.ClientSession] = None
        
        super().__init__(name="github", version="1.0.0")
    
    def _setup_tools(self):
        """Setup GitHub specific tools"""
        
        # Repository analysis tools
        self.register_tool(
            "get_repository_info",
            self._get_repository_info,
            "Get detailed information about a GitHub repository",
            {
                "owner": {
                    "type": "string",
                    "description": "Repository owner (username or organization)"
                },
                "repo": {
                    "type": "string", 
                    "description": "Repository name"
                }
            }
        )
        
        self.register_tool(
            "get_repository_contents",
            self._get_repository_contents,
            "Get repository contents and file structure",
            {
                "owner": {
                    "type": "string",
                    "description": "Repository owner"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name"
                },
                "path": {
                    "type": "string",
                    "description": "Path to explore (default: root)",
                    "default": ""
                },
                "ref": {
                    "type": "string",
                    "description": "Branch, tag, or commit SHA",
                    "default": "main"
                }
            }
        )
        
        self.register_tool(
            "get_file_content",
            self._get_file_content,
            "Get content of a specific file",
            {
                "owner": {
                    "type": "string",
                    "description": "Repository owner"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name"
                },
                "path": {
                    "type": "string",
                    "description": "File path"
                },
                "ref": {
                    "type": "string",
                    "description": "Branch, tag, or commit SHA",
                    "default": "main"
                }
            }
        )
        
        self.register_tool(
            "get_commits",
            self._get_commits,
            "Get commit history for a repository",
            {
                "owner": {
                    "type": "string",
                    "description": "Repository owner"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name"
                },
                "sha": {
                    "type": "string",
                    "description": "Branch or commit SHA",
                    "default": "main"
                },
                "per_page": {
                    "type": "integer",
                    "description": "Number of commits per page (max 100)",
                    "default": 10
                },
                "page": {
                    "type": "integer", 
                    "description": "Page number",
                    "default": 1
                }
            }
        )
        
        self.register_tool(
            "get_pull_requests",
            self._get_pull_requests,
            "Get pull requests for a repository",
            {
                "owner": {
                    "type": "string",
                    "description": "Repository owner"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name"
                },
                "state": {
                    "type": "string",
                    "description": "PR state (open, closed, all)",
                    "default": "open"
                },
                "per_page": {
                    "type": "integer",
                    "description": "Number of PRs per page (max 100)",
                    "default": 10
                }
            }
        )
        
        self.register_tool(
            "get_branches",
            self._get_branches,
            "Get branches for a repository",
            {
                "owner": {
                    "type": "string",
                    "description": "Repository owner"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name"
                },
                "per_page": {
                    "type": "integer",
                    "description": "Number of branches per page (max 100)",
                    "default": 10
                }
            }
        )
        
        self.register_tool(
            "get_languages",
            self._get_languages,
            "Get programming languages used in the repository",
            {
                "owner": {
                    "type": "string",
                    "description": "Repository owner"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name"
                }
            }
        )
        
        self.register_tool(
            "search_code",
            self._search_code,
            "Search for code in the repository",
            {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional)"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name (optional)"
                },
                "per_page": {
                    "type": "integer",
                    "description": "Number of results per page (max 100)",
                    "default": 10
                }
            }
        )
    
    async def _ensure_session(self):
        """Ensure HTTP session is available"""
        if not self.session:
            headers = {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": self.api_version
            }
            if self.github_token:
                headers["Authorization"] = f"Bearer {self.github_token}"
            self.session = aiohttp.ClientSession(headers=headers)
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to GitHub API"""
        await self._ensure_session()
        
        try:
            url = f"{self.base_url}/{endpoint}"
            async with self.session.get(url, params=params) as response:
                if response.status == 401:
                    raise Exception("Authentication failed. Check your GitHub token.")
                elif response.status == 403:
                    # Check for rate limiting
                    if "rate limit" in (await response.text()).lower():
                        raise Exception("GitHub API rate limit exceeded. Please wait or use a token.")
                    else:
                        raise Exception("Access forbidden. Check your token permissions.")
                elif response.status == 404:
                    raise Exception("Repository or resource not found.")
                elif response.status != 200:
                    raise Exception(f"GitHub API request failed with status {response.status}: {await response.text()}")
                
                return await response.json()
        except Exception as e:
            logger.error(f"GitHub API request failed: {e}")
            raise
    
    async def _get_repository_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information"""
        return await self._make_request(f"repos/{owner}/{repo}")
    
    async def _get_repository_contents(self, 
                                     owner: str, 
                                     repo: str,
                                     path: str = "",
                                     ref: str = "main") -> Dict[str, Any]:
        """Get repository contents"""
        endpoint = f"repos/{owner}/{repo}/contents"
        if path:
            endpoint += f"/{path}"
        
        params = {"ref": ref}
        return await self._make_request(endpoint, params)
    
    async def _get_file_content(self, 
                               owner: str,
                               repo: str, 
                               path: str,
                               ref: str = "main") -> Dict[str, Any]:
        """Get file content"""
        endpoint = f"repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref}
        response = await self._make_request(endpoint, params)
        
        # Decode content if it's base64 encoded
        if response.get("encoding") == "base64" and "content" in response:
            import base64
            content = base64.b64decode(response["content"]).decode('utf-8', errors='ignore')
            response["decoded_content"] = content
        
        return response
    
    async def _get_commits(self, 
                          owner: str,
                          repo: str,
                          sha: str = "main",
                          per_page: int = 10,
                          page: int = 1) -> Dict[str, Any]:
        """Get commit history"""
        endpoint = f"repos/{owner}/{repo}/commits"
        params = {
            "sha": sha,
            "per_page": min(per_page, 100),
            "page": page
        }
        commits = await self._make_request(endpoint, params)
        return {"commits": commits, "count": len(commits)}
    
    async def _get_pull_requests(self,
                                owner: str,
                                repo: str, 
                                state: str = "open",
                                per_page: int = 10) -> Dict[str, Any]:
        """Get pull requests"""
        endpoint = f"repos/{owner}/{repo}/pulls"
        params = {
            "state": state,
            "per_page": min(per_page, 100)
        }
        prs = await self._make_request(endpoint, params)
        return {"pull_requests": prs, "count": len(prs)}
    
    async def _get_branches(self,
                           owner: str,
                           repo: str,
                           per_page: int = 10) -> Dict[str, Any]:
        """Get repository branches"""
        endpoint = f"repos/{owner}/{repo}/branches"
        params = {"per_page": min(per_page, 100)}
        branches = await self._make_request(endpoint, params)
        return {"branches": branches, "count": len(branches)}
    
    async def _get_languages(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository languages"""
        endpoint = f"repos/{owner}/{repo}/languages"
        return await self._make_request(endpoint)
    
    async def _search_code(self,
                          query: str,
                          owner: Optional[str] = None,
                          repo: Optional[str] = None,
                          per_page: int = 10) -> Dict[str, Any]:
        """Search for code"""
        # Build search query
        search_query = query
        if owner and repo:
            search_query += f" repo:{owner}/{repo}"
        elif owner:
            search_query += f" user:{owner}"
        
        endpoint = "search/code"
        params = {
            "q": search_query,
            "per_page": min(per_page, 100)
        }
        return await self._make_request(endpoint, params)