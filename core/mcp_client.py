"""MCP client wrapper for pandas-chat-app"""

from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import time
from mcp import ClientSession
from mcp.client.sse import sse_client
from config import get_settings
from utils import get_logger, ChartHandler


class MCPClient:
    """Handle MCP server connections and tool calls"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger()
        self.chart_handler = ChartHandler()
        self.tools: List[Dict[str, Any]] = []
        self.connected = False
        self.connection_time: Optional[datetime] = None
        
    async def connect(self) -> List[Dict[str, Any]]:
        """Connect to MCP server and retrieve tools"""
        try:
            async with sse_client(url=self.settings.mcp_sse_url) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    response = await session.list_tools()
                    
                    self.tools = []
                    for tool in response.tools:
                        self.tools.append({
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description or f"Tool: {tool.name}",
                                "parameters": tool.inputSchema if tool.inputSchema else {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                }
                            }
                        })
                    
                    self.connected = True
                    self.connection_time = datetime.now()
                    
                    self.logger.log(
                        "info",
                        f"Connected to MCP server: {len(self.tools)} tools available"
                    )
                    
                    return self.tools
                    
        except Exception as e:
            self.logger.log("error", f"Failed to connect to MCP: {str(e)}")
            self.connected = False
            raise
            
    async def call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> str:
        """Call an MCP tool and return result"""
        
        start_time = time.time()
        
        try:
            async with sse_client(url=self.settings.mcp_sse_url) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, params)
                    
                    # Parse result
                    result_str = self.parse_result(result)
                    
                    # Calculate duration
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Log the call
                    self.logger.log_mcp_call(
                        tool_name,
                        params,
                        result_str,
                        duration_ms,
                        success=True
                    )
                    
                    # Check if this is a chart creation
                    chart_info = self.chart_handler.detect_chart_in_response(
                        tool_name,
                        result_str
                    )
                    
                    if chart_info:
                        self.logger.log_chart_creation(
                            chart_info['chart_type'],
                            chart_info.get('dataframe', 'unknown'),
                            chart_info['filepath'],
                            chart_info.get('metadata')
                        )
                    
                    return result_str
                    
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Error: {str(e)}"
            
            self.logger.log_mcp_call(
                tool_name,
                params,
                error_msg,
                duration_ms,
                success=False,
                error=str(e)
            )
            
            return error_msg
            
    def parse_result(self, result) -> str:
        """Parse MCP tool call results"""
        if hasattr(result, 'content'):
            content = result.content
            if isinstance(content, list):
                text = ""
                for item in content:
                    if hasattr(item, 'text'):
                        text += item.text
                    else:
                        text += str(item)
                return text
            elif hasattr(content, 'text'):
                return content.text
            else:
                return str(content)
        return str(result)
        
    def get_tool_by_name(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool definition by name"""
        for tool in self.tools:
            if tool["function"]["name"] == tool_name:
                return tool
        return None
        
    def get_tools_by_category(self) -> Dict[str, List[str]]:
        """Get tools organized by category"""
        categories = {
            "Data Loading": [],
            "Data Analysis": [],
            "Visualization": [],
            "File Management": [],
            "Session Management": [],
            "Other": []
        }
        
        for tool in self.tools:
            name = tool["function"]["name"]
            
            if any(x in name for x in ["load", "read", "upload", "preview"]):
                categories["Data Loading"].append(name)
            elif any(x in name for x in ["pandas", "validate", "execution", "metadata"]):
                categories["Data Analysis"].append(name)
            elif any(x in name for x in ["chart", "visualization", "plot", "graph", "heatmap"]):
                categories["Visualization"].append(name)
            elif any(x in name for x in ["file", "temp", "format"]):
                categories["File Management"].append(name)
            elif any(x in name for x in ["session", "clear", "info"]):
                categories["Session Management"].append(name)
            else:
                categories["Other"].append(name)
                
        return {k: v for k, v in categories.items() if v}
        
    def is_connected(self) -> bool:
        """Check if connected to MCP server"""
        return self.connected
        
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information"""
        return {
            "connected": self.connected,
            "tools_count": len(self.tools),
            "connection_time": self.connection_time.isoformat() if self.connection_time else None,
            "server_url": self.settings.mcp_sse_url
        }
        
    def needs_file_injection(self, tool_name: str) -> bool:
        """Check if tool needs file content injection"""
        return tool_name == "upload_temp_file_tool"