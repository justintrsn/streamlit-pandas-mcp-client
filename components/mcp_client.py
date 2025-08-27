import asyncio
import streamlit as st
import httpx
from typing import Dict, Any, Optional, List
from mcp import ClientSession
from mcp.client.sse import sse_client
import json
import time
from config.settings import settings
from utils.logger import logger, log_info, log_error, log_debug, log_warning, log_connection, log_exception

class MCPClient:
    """Wrapper for MCP server communication with comprehensive logging."""
    
    def __init__(self):
        self.url = settings.MCP_SSE_URL
        self.session = None
        self.connected = False
        log_info(f"MCPClient initialized with URL: {self.url}")
        
    async def connect(self) -> bool:
        """Establish connection to MCP server with detailed logging."""
        log_info("="*50)
        log_info("Starting MCP Server Connection Attempt")
        logger.log_connection_attempt(self.url, "connect")
        
        try:
            # Log network details first
            logger.log_network_details(self.url)
            
            # Test connection with different endpoints
            async with httpx.AsyncClient(timeout=10.0) as client:
                log_debug(f"Testing SSE endpoint: {self.url}")
                
                # Try SSE endpoint
                try:
                    log_debug("Attempting SSE endpoint connection...")
                    response = await client.get(
                        self.url, 
                        headers={"Accept": "text/event-stream"},
                        timeout=httpx.Timeout(10.0)
                    )
                    log_info(f"SSE endpoint response: Status {response.status_code}")
                    log_debug(f"Response headers: {dict(response.headers)}")
                    
                    if response.status_code in [200, 301, 302]:
                        log_info("SSE endpoint accessible")
                        self.connected = True
                        st.session_state.mcp_connected = True
                        log_connection(self.url, True, status_code=response.status_code)
                        return True
                    else:
                        log_warning(f"SSE endpoint returned unexpected status: {response.status_code}")
                        
                except httpx.TimeoutException as e:
                    log_warning(f"SSE endpoint timeout: {e}")
                except Exception as e:
                    log_warning(f"SSE endpoint error: {e}")
                
                # Try health endpoint as fallback
                health_url = self.url.replace('/sse', '/health')
                log_debug(f"Trying health endpoint: {health_url}")
                
                try:
                    response = await client.get(health_url, timeout=httpx.Timeout(10.0))
                    log_info(f"Health endpoint response: Status {response.status_code}")
                    
                    if response.status_code == 200:
                        log_info("Health endpoint successful, server is running")
                        self.connected = True
                        st.session_state.mcp_connected = True
                        log_connection(health_url, True, status_code=response.status_code)
                        return True
                    else:
                        log_error(f"Health endpoint failed with status: {response.status_code}")
                        
                except httpx.TimeoutException as e:
                    log_error(f"Health endpoint timeout: {e}")
                except Exception as e:
                    log_error(f"Health endpoint error: {e}")
                
                # Try base URL
                base_url = self.url.replace('/sse', '')
                log_debug(f"Trying base URL: {base_url}")
                
                try:
                    response = await client.get(base_url, timeout=httpx.Timeout(10.0))
                    log_info(f"Base URL response: Status {response.status_code}")
                    
                    if response.status_code in [200, 301, 302, 404]:
                        # Server is responding, even if endpoint not found
                        log_warning("Server is responding but SSE endpoint may not be configured correctly")
                        self.connected = True
                        st.session_state.mcp_connected = True
                        log_connection(base_url, True, status_code=response.status_code)
                        return True
                        
                except httpx.TimeoutException as e:
                    log_error(f"Base URL timeout: {e}")
                except Exception as e:
                    log_error(f"Base URL error: {e}")
            
            # If we get here, all connection attempts failed
            log_error("All connection attempts failed")
            self.connected = False
            st.session_state.mcp_connected = False
            log_connection(self.url, False, error="All connection methods failed")
            return False
            
        except Exception as e:
            log_exception(e, "MCPClient.connect")
            self.connected = False
            st.session_state.mcp_connected = False
            log_connection(self.url, False, error=str(e))
            return False
        finally:
            log_info("Connection attempt completed")
            log_info("="*50)
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call a tool on the MCP server with logging."""
        log_debug(f"Calling tool: {tool_name}")
        logger.log_tool_call(tool_name, params)
        
        try:
            async with sse_client(url=self.url) as streams:
                log_debug("SSE client connected")
                async with ClientSession(*streams) as session:
                    log_debug("Client session established")
                    await session.initialize()
                    log_debug("Session initialized")
                    
                    result = await session.call_tool(tool_name, params)
                    logger.log_tool_call(tool_name, params, result=result)
                    log_debug(f"Tool {tool_name} completed successfully")
                    return result
                    
        except Exception as e:
            log_exception(e, f"call_tool({tool_name})")
            logger.log_tool_call(tool_name, params, error=str(e))
            st.error(f"Error calling tool {tool_name}: {e}")
            return None
    
    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from the server."""
        log_debug("Listing available tools")
        try:
            async with sse_client(url=self.url) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    log_info(f"Found {len(tools)} available tools")
                    for tool in tools:
                        log_debug(f"  - {tool.get('name', 'unknown')}")
                    return tools
                    
        except Exception as e:
            log_exception(e, "list_available_tools")
            return []
    
    async def get_server_status(self) -> Dict[str, Any]:
        """Get server status and capabilities with logging."""
        log_debug("Getting server status")
        try:
            # Try to get session info as a connection test
            result = await self.call_tool("get_session_info_tool", {})
            
            if result:
                log_info("Server status: Connected (session info retrieved)")
                return {
                    "status": "connected",
                    "session_info": result,
                    "timestamp": time.time()
                }
            else:
                # Fallback to simple connectivity test
                log_debug("Session info not available, trying direct connection test")
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(self.url, headers={"Accept": "text/event-stream"})
                    if response.status_code in [200, 301, 302]:
                        log_info("Server status: Reachable")
                        return {"status": "connected", "message": "Server reachable"}
                    else:
                        log_warning(f"Server returned status {response.status_code}")
                        return {"status": "error", "message": f"HTTP {response.status_code}"}
                
        except Exception as e:
            log_exception(e, "get_server_status")
            return {"status": "error", "message": str(e)}

    # File Operations
    async def upload_file(self, file_path: str, file_name: str) -> Optional[Dict[str, Any]]:
        """Upload file to MCP server."""
        log_info(f"Uploading file: {file_name}")
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            log_debug(f"File size: {len(file_content)} bytes")
            params = {
                "file_name": file_name,
                "file_content": file_content.hex(),
                "encoding": "hex"
            }
            
            result = await self.call_tool("upload_temp_file_tool", params)
            if result:
                log_info(f"File uploaded successfully: {file_name}")
            else:
                log_error(f"File upload failed: {file_name}")
            return result
            
        except Exception as e:
            log_exception(e, f"upload_file({file_name})")
            st.error(f"Error uploading file: {e}")
            return None
    
    async def load_dataframe(self, file_name: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Load a DataFrame from uploaded file."""
        log_info(f"Loading DataFrame: {file_name}")
        params = {"file_name": file_name, **kwargs}
        return await self.call_tool("load_dataframe_tool", params)
    
    async def preview_file(self, file_name: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Preview file without loading full DataFrame."""
        log_info(f"Previewing file: {file_name}")
        params = {"file_name": file_name, **kwargs}
        return await self.call_tool("preview_file_tool", params)
    
    async def list_dataframes(self) -> Optional[List[str]]:
        """List all loaded DataFrames."""
        log_debug("Listing DataFrames")
        result = await self.call_tool("list_dataframes_tool", {})
        if result:
            dataframes = result.get("dataframes", [])
            log_info(f"Found {len(dataframes)} DataFrames")
            return dataframes
        return []
    
    async def get_dataframe_info(self, df_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific DataFrame."""
        log_debug(f"Getting info for DataFrame: {df_name}")
        params = {"dataframe_name": df_name}
        return await self.call_tool("get_dataframe_info_tool", params)
    
    async def run_pandas_code(self, code: str, df_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Execute pandas code on the server."""
        log_info("Executing pandas code")
        log_debug(f"Code length: {len(code)} characters")
        params = {"code": code, "dataframe_name": df_name}
        return await self.call_tool("run_pandas_code_tool", params)
    
    async def create_chart(self, chart_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a chart using the MCP server."""
        log_info(f"Creating chart: {chart_config.get('chart_type', 'unknown')} for {chart_config.get('dataframe_name', 'unknown')}")
        return await self.call_tool("create_chart_tool", chart_config)
    
    async def suggest_charts(self, df_name: str) -> Optional[Dict[str, Any]]:
        """Get chart suggestions for a DataFrame."""
        log_info(f"Getting chart suggestions for: {df_name}")
        params = {"dataframe_name": df_name}
        return await self.call_tool("suggest_charts_tool", params)
    
    async def create_correlation_heatmap(self, df_name: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Create correlation heatmap for numerical columns."""
        log_info(f"Creating correlation heatmap for: {df_name}")
        params = {"dataframe_name": df_name, **kwargs}
        return await self.call_tool("create_correlation_heatmap_tool", params)
    
    async def create_time_series_chart(self, df_name: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Create optimized time series chart."""
        log_info(f"Creating time series chart for: {df_name}")
        params = {"dataframe_name": df_name, **kwargs}
        return await self.call_tool("create_time_series_chart_tool", params)
    
    async def clear_session(self) -> Optional[Dict[str, Any]]:
        """Clear all data from MCP server session."""
        log_warning("Clearing server session")
        return await self.call_tool("clear_session_tool", {})
    
    async def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get current session information."""
        log_debug("Getting session info")
        return await self.call_tool("get_session_info_tool", {})

# Global client instance
mcp_client = MCPClient()

def run_async_task(coro):
    """Helper to run async tasks in Streamlit."""
    log_debug("Running async task")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)

def test_mcp_connection() -> bool:
    """Test and establish MCP connection."""
    log_info("Testing MCP connection")
    try:
        connected = run_async_task(mcp_client.connect())
        if connected:
            status = run_async_task(mcp_client.get_server_status())
            success = status.get("status") == "connected"
            st.session_state.mcp_connected = success
            mcp_client.connected = success
            log_info(f"Connection test result: {'Success' if success else 'Failed'}")
            return success
        return False
    except Exception as e:
        log_exception(e, "test_mcp_connection")
        st.session_state.mcp_connected = False
        return False

def establish_mcp_connection() -> bool:
    """Establish and maintain MCP connection."""
    log_info("Establishing MCP connection")
    logger.log_session_state(st.session_state)
    
    try:
        connected = run_async_task(mcp_client.connect())
        if connected:
            st.session_state.mcp_connected = True
            mcp_client.connected = True
            log_info("MCP connection established successfully")
            
            # List available tools for debugging
            tools = run_async_task(mcp_client.list_available_tools())
            log_info(f"Available tools: {len(tools)}")
            
            return True
        else:
            log_error("Failed to establish MCP connection")
            return False
    except Exception as e:
        log_exception(e, "establish_mcp_connection")
        st.session_state.mcp_connected = False
        return False

def display_connection_status():
    """Display MCP server connection status."""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.session_state.get("mcp_connected", False):
            st.success("🟢 Connected to MCP Server")
        else:
            st.error("🔴 Not connected to MCP Server")
    
    with col2:
        if not st.session_state.get("mcp_connected", False):
            if st.button("🔗 Connect", key="connect_mcp"):
                with st.spinner("Connecting..."):
                    if establish_mcp_connection():
                        st.success("✅ Connected!")
                        st.rerun()
                    else:
                        st.error("❌ Connection failed! Check logs for details")
        else:
            if st.button("🔄 Reconnect", key="reconnect_mcp"):
                with st.spinner("Reconnecting..."):
                    if establish_mcp_connection():
                        st.success("✅ Reconnected!")
                        st.rerun()
    
    with col3:
        st.code(settings.MCP_SSE_URL, language="text")
    
    # Add log viewer button
    if st.button("📋 View Logs", key="view_logs"):
        with st.expander("Recent Logs", expanded=True):
            st.code(logger.get_recent_logs(lines=30), language="text")
        
        with st.expander("Connection Logs", expanded=False):
            st.code(logger.get_connection_logs(), language="json")

def ensure_mcp_connection():
    """Ensure MCP connection is established."""
    if not st.session_state.get("mcp_connected", False):
        log_warning("MCP connection not established, attempting to connect")
        with st.spinner("Connecting to MCP server..."):
            connected = establish_mcp_connection()
            if not connected:
                st.error("Failed to connect to MCP server. Check logs for details.")
                
                # Show recent logs
                st.markdown("### Recent Logs:")
                st.code(logger.get_recent_logs(lines=20), language="text")
                st.stop()
    
    return mcp_client