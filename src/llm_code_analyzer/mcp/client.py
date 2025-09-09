"""
Model Context Protocol (MCP) Client implementation for interacting with repository analysis servers
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import aiohttp

from .server import MCPRequest, MCPResponse

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Model Context Protocol client for communicating with repository analysis servers
    """
    
    def __init__(self, server_url: Optional[str] = None):
        """
        Initialize MCP client
        
        Args:
            server_url: URL of the MCP server (if using HTTP transport)
        """
        self.server_url = server_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.tools_cache: Optional[List[Dict[str, Any]]] = None
        self.resources_cache: Optional[List[Dict[str, Any]]] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def send_request(self, request: MCPRequest) -> MCPResponse:
        """
        Send a request to the MCP server
        
        Args:
            request: The MCP request
            
        Returns:
            MCP response
        """
        if self.server_url and self.session:
            return await self._send_http_request(request)
        else:
            # Direct server communication (for embedded servers)
            raise NotImplementedError("Direct server communication not implemented")
    
    async def _send_http_request(self, request: MCPRequest) -> MCPResponse:
        """Send HTTP request to MCP server"""
        try:
            request_data = {
                "jsonrpc": "2.0",
                "method": request.method,
                "params": request.params,
                "id": request.id or "1"
            }
            
            async with self.session.post(
                self.server_url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                response_data = await response.json()
                
                if "error" in response_data:
                    return MCPResponse(
                        error=response_data["error"],
                        id=response_data.get("id")
                    )
                else:
                    return MCPResponse(
                        result=response_data.get("result"),
                        id=response_data.get("id")
                    )
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            return MCPResponse(
                error={"code": -32603, "message": f"Transport error: {str(e)}"}
            )
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from the server
        
        Returns:
            List of available tools
        """
        request = MCPRequest(method="tools/list", params={})
        response = await self.send_request(request)
        
        if response.error:
            raise Exception(f"Failed to list tools: {response.error}")
        
        tools = response.result.get("tools", [])
        self.tools_cache = tools
        return tools
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the server
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        request = MCPRequest(
            method="tools/call",
            params={"name": name, "arguments": arguments}
        )
        response = await self.send_request(request)
        
        if response.error:
            raise Exception(f"Tool call failed: {response.error}")
        
        content = response.result.get("content", [])
        if content and content[0].get("type") == "text":
            return json.loads(content[0]["text"])
        
        return response.result
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """
        List available resources from the server
        
        Returns:
            List of available resources
        """
        request = MCPRequest(method="resources/list", params={})
        response = await self.send_request(request)
        
        if response.error:
            raise Exception(f"Failed to list resources: {response.error}")
        
        resources = response.result.get("resources", [])
        self.resources_cache = resources
        return resources
    
    async def read_resource(self, uri: str) -> Any:
        """
        Read a resource from the server
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource content
        """
        request = MCPRequest(
            method="resources/read",
            params={"uri": uri}
        )
        response = await self.send_request(request)
        
        if response.error:
            raise Exception(f"Failed to read resource: {response.error}")
        
        contents = response.result.get("contents", [])
        if contents:
            content = contents[0]
            if content.get("mimeType") == "application/json":
                return json.loads(content["text"])
            else:
                return content["text"]
        
        return None
    
    def get_cached_tools(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached tools list"""
        return self.tools_cache
    
    def get_cached_resources(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached resources list"""
        return self.resources_cache