"""
Model Context Protocol (MCP) Server implementation for code repository analysis
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class MCPRequest:
    """MCP request structure"""
    method: str
    params: Dict[str, Any]
    id: Optional[str] = None


@dataclass
class MCPResponse:
    """MCP response structure"""
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class MCPServer(ABC):
    """
    Base Model Context Protocol server for repository analysis
    
    This server provides a standardized interface for LLMs to interact
    with code repositories through structured tool calls.
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        """
        Initialize MCP server
        
        Args:
            name: Server name
            version: Server version
        """
        self.name = name
        self.version = version
        self.tools: Dict[str, Callable] = {}
        self.resources: Dict[str, Any] = {}
        self._setup_tools()
    
    @abstractmethod
    def _setup_tools(self):
        """Setup available tools for this server"""
        pass
    
    def register_tool(self, name: str, handler: Callable, description: str, parameters: Dict[str, Any]):
        """
        Register a tool with the server
        
        Args:
            name: Tool name
            handler: Function to handle tool calls
            description: Tool description
            parameters: JSON schema for parameters
        """
        self.tools[name] = {
            'handler': handler,
            'description': description,
            'parameters': parameters
        }
        logger.debug(f"Registered tool: {name}")
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        Handle an MCP request
        
        Args:
            request: The MCP request
            
        Returns:
            MCP response
        """
        try:
            if request.method == "tools/list":
                return await self._list_tools()
            elif request.method == "tools/call":
                return await self._call_tool(request.params)
            elif request.method == "resources/list":
                return await self._list_resources()
            elif request.method == "resources/read":
                return await self._read_resource(request.params)
            else:
                return MCPResponse(
                    error={"code": -32601, "message": f"Method not found: {request.method}"},
                    id=request.id
                )
        except Exception as e:
            logger.error(f"Error handling request {request.method}: {e}")
            return MCPResponse(
                error={"code": -32603, "message": f"Internal error: {str(e)}"},
                id=request.id
            )
    
    async def _list_tools(self) -> MCPResponse:
        """List available tools"""
        tools_list = []
        for name, tool_info in self.tools.items():
            tools_list.append({
                "name": name,
                "description": tool_info["description"],
                "inputSchema": {
                    "type": "object",
                    "properties": tool_info["parameters"],
                    "required": list(tool_info["parameters"].keys())
                }
            })
        
        return MCPResponse(result={"tools": tools_list})
    
    async def _call_tool(self, params: Dict[str, Any]) -> MCPResponse:
        """Call a specific tool"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            return MCPResponse(
                error={"code": -32602, "message": f"Tool not found: {tool_name}"}
            )
        
        try:
            handler = self.tools[tool_name]["handler"]
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)
            
            return MCPResponse(result={"content": [{"type": "text", "text": json.dumps(result, indent=2)}]})
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return MCPResponse(
                error={"code": -32603, "message": f"Tool execution error: {str(e)}"}
            )
    
    async def _list_resources(self) -> MCPResponse:
        """List available resources"""
        resources_list = []
        for name, resource in self.resources.items():
            resources_list.append({
                "uri": f"resource://{name}",
                "name": name,
                "description": resource.get("description", ""),
                "mimeType": resource.get("mimeType", "application/json")
            })
        
        return MCPResponse(result={"resources": resources_list})
    
    async def _read_resource(self, params: Dict[str, Any]) -> MCPResponse:
        """Read a specific resource"""
        uri = params.get("uri", "")
        resource_name = uri.replace("resource://", "")
        
        if resource_name not in self.resources:
            return MCPResponse(
                error={"code": -32602, "message": f"Resource not found: {resource_name}"}
            )
        
        resource = self.resources[resource_name]
        return MCPResponse(result={
            "contents": [{
                "uri": uri,
                "mimeType": resource.get("mimeType", "application/json"),
                "text": json.dumps(resource.get("data", {}), indent=2)
            }]
        })
    
    def add_resource(self, name: str, data: Any, description: str = "", mime_type: str = "application/json"):
        """
        Add a resource to the server
        
        Args:
            name: Resource name
            data: Resource data
            description: Resource description
            mime_type: MIME type
        """
        self.resources[name] = {
            "data": data,
            "description": description,
            "mimeType": mime_type
        }
        logger.debug(f"Added resource: {name}")