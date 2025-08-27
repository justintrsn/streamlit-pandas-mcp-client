"""
pages/4_debug.py - Debug page for viewing logs and testing connections
Save this as pages/4_debug.py
"""

import streamlit as st
import sys
from pathlib import Path
import json
import httpx
import socket
import asyncio
from urllib.parse import urlparse
from datetime import datetime

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from utils.session_state import initialize_session_state
from utils.logger import logger
from config.settings import settings
from components.mcp_client import mcp_client, run_async_task

def test_direct_connection():
    """Test direct HTTP connection to the server."""
    st.markdown("### 🔌 Direct Connection Test")
    
    url = settings.MCP_SSE_URL
    parsed = urlparse(url)
    hostname = parsed.hostname
    port = parsed.port or 80
    
    tests = []
    
    # DNS Resolution Test
    st.markdown("#### DNS Resolution")
    try:
        ip_address = socket.gethostbyname(hostname)
        st.success(f"✅ Resolved {hostname} to {ip_address}")
        tests.append(("DNS Resolution", "Success", ip_address))
    except socket.gaierror as e:
        st.error(f"❌ DNS resolution failed: {e}")
        tests.append(("DNS Resolution", "Failed", str(e)))
    
    # Socket Connection Test
    st.markdown("#### Socket Connection")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((hostname, port))
        sock.close()
        
        if result == 0:
            st.success(f"✅ Socket connection successful to {hostname}:{port}")
            tests.append(("Socket Connection", "Success", f"{hostname}:{port}"))
        else:
            st.error(f"❌ Socket connection failed (Error code: {result})")
            tests.append(("Socket Connection", "Failed", f"Error code: {result}"))
    except Exception as e:
        st.error(f"❌ Socket test failed: {e}")
        tests.append(("Socket Connection", "Error", str(e)))
    
    # HTTP Connection Tests
    st.markdown("#### HTTP Endpoints")
    
    async def test_endpoints():
        endpoints_to_test = [
            (url, "SSE Endpoint"),
            (url.replace('/sse', '/health'), "Health Endpoint"),
            (url.replace('/sse', ''), "Base URL"),
            (f"http://{hostname}:{port}/", "Root URL")
        ]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for endpoint, name in endpoints_to_test:
                try:
                    st.write(f"Testing {name}: `{endpoint}`")
                    response = await client.get(endpoint, headers={"Accept": "text/event-stream"})
                    
                    if response.status_code == 200:
                        st.success(f"✅ {name}: Status {response.status_code}")
                        tests.append((name, "Success", f"Status {response.status_code}"))
                    else:
                        st.warning(f"⚠️ {name}: Status {response.status_code}")
                        tests.append((name, "Warning", f"Status {response.status_code}"))
                    
                    # Show response headers
                    with st.expander(f"{name} Response Headers"):
                        for key, value in response.headers.items():
                            st.text(f"{key}: {value}")
                    
                    # Show response body preview (first 500 chars)
                    if response.text:
                        with st.expander(f"{name} Response Body (preview)"):
                            st.code(response.text[:500], language="text")
                            
                except httpx.TimeoutException:
                    st.error(f"❌ {name}: Timeout")
                    tests.append((name, "Timeout", "Request timed out"))
                except Exception as e:
                    st.error(f"❌ {name}: {e}")
                    tests.append((name, "Error", str(e)))
    
    run_async_task(test_endpoints())
    
    # Summary table
    st.markdown("### 📊 Test Summary")
    import pandas as pd
    df = pd.DataFrame(tests, columns=["Test", "Result", "Details"])
    st.dataframe(df, use_container_width=True)

def view_logs():
    """View application logs."""
    st.markdown("### 📋 Application Logs")
    
    # Log controls
    col1, col2, col3 = st.columns(3)
    with col1:
        lines = st.number_input("Number of lines", min_value=10, max_value=500, value=50, step=10)
    
    with col2:
        if st.button("🔄 Refresh Logs"):
            st.rerun()
    
    with col3:
        if st.button("📁 Open Logs Directory"):
            st.info(f"Logs are stored in: {logger.log_dir.absolute()}")
    
    # Recent logs
    st.markdown("#### Recent Activity")
    recent_logs = logger.get_recent_logs(lines=lines)
    st.code(recent_logs, language="text")
    
    # Connection logs
    st.markdown("#### Connection Logs")
    connection_logs = logger.get_connection_logs()
    if connection_logs:
        # Parse and display JSON logs
        try:
            log_lines = connection_logs.strip().split('\n')
            for line in log_lines[-20:]:  # Show last 20 entries
                if line:
                    try:
                        entry = json.loads(line)
                        if entry.get("event") == "connection_attempt":
                            st.info(f"🔗 {entry['timestamp']}: Connection attempt to {entry['url']}")
                        elif entry.get("event") == "connection_response":
                            if entry.get("success"):
                                st.success(f"✅ {entry['timestamp']}: Connected (Status: {entry.get('status_code')})")
                            else:
                                st.error(f"❌ {entry['timestamp']}: Failed - {entry.get('error')}")
                        elif entry.get("event") == "exception":
                            st.error(f"💥 {entry['timestamp']}: Exception in {entry.get('context')}: {entry.get('error')}")
                    except json.JSONDecodeError:
                        st.text(line)
        except Exception as e:
            st.error(f"Error parsing logs: {e}")
            st.code(connection_logs, language="text")
    else:
        st.info("No connection logs found")

def test_mcp_tools():
    """Test MCP server tools."""
    st.markdown("### 🛠️ MCP Tools Test")
    
    if not st.session_state.get("mcp_connected", False):
        st.warning("⚠️ Not connected to MCP server. Connect first to test tools.")
        return
    
    if st.button("📋 List Available Tools"):
        with st.spinner("Fetching available tools..."):
            tools = run_async_task(mcp_client.list_available_tools())
            
            if tools:
                st.success(f"Found {len(tools)} tools")
                
                for i, tool in enumerate(tools):
                    with st.expander(f"Tool {i+1}: {tool.get('name', 'Unknown')}"):
                        st.json(tool)
            else:
                st.error("No tools found or failed to fetch tools")
    
    if st.button("ℹ️ Get Session Info"):
        with st.spinner("Getting session info..."):
            info = run_async_task(mcp_client.get_session_info())
            
            if info:
                st.success("Session info retrieved")
                st.json(info)
            else:
                st.error("Failed to get session info")

def view_session_state():
    """View current session state."""
    st.markdown("### 🔍 Session State")
    
    # Filter sensitive data
    safe_state = {}
    for key, value in st.session_state.items():
        if key in ["openai_api_key"]:
            safe_state[key] = "***REDACTED***" if value else None
        elif key in ["uploaded_files", "loaded_dataframes", "generated_charts", "chat_history"]:
            safe_state[key] = f"<{type(value).__name__} with {len(value)} items>"
        elif key == "temp_dir":
            safe_state[key] = str(value) if value else None
        else:
            safe_state[key] = value
    
    st.json(safe_state)

def main():
    """Main debug page."""
    st.set_page_config(
        page_title="Debug - MCP Client",
        page_icon="🐛",
        layout="wide"
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.title("🐛 Debug & Diagnostics")
    st.markdown("*Troubleshoot connection issues and view logs*")
    
    # Current status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.session_state.get("mcp_connected", False):
            st.success("✅ MCP Connected")
        else:
            st.error("❌ MCP Not Connected")
    
    with col2:
        st.info(f"URL: {settings.MCP_SSE_URL}")
    
    with col3:
        st.info(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    
    st.divider()
    
    # Debug tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔌 Connection Test",
        "📋 View Logs", 
        "🛠️ Test Tools",
        "🔍 Session State",
        "📖 Help"
    ])
    
    with tab1:
        test_direct_connection()
    
    with tab2:
        view_logs()
    
    with tab3:
        test_mcp_tools()
    
    with tab4:
        view_session_state()
    
    with tab5:
        st.markdown("""
        ### 🆘 Troubleshooting Guide
        
        #### Common Issues:
        
        **1. Connection Failed**
        - Check if the MCP server is running at `119.13.110.147:8000`
        - Verify network connectivity (firewall, VPN, etc.)
        - Check the Connection Test tab for specific errors
        
        **2. DNS Resolution Failed**
        - Ensure you can resolve the hostname
        - Try using IP address directly
        - Check your DNS settings
        
        **3. Socket Connection Failed**
        - Port might be blocked by firewall
        - Server might not be listening on the port
        - Check security groups in cloud provider
        
        **4. HTTP Errors**
        - 404: Endpoint not found - check URL path
        - 500: Server error - check server logs
        - Timeout: Network issues or server overloaded
        
        #### Log Files Location:
        The logs are stored in the `logs/` directory in your project folder.
        
        - `mcp_client_YYYYMMDD.log` - General application logs
        - `mcp_errors_YYYYMMDD.log` - Error logs only
        - `connection_YYYYMMDD_HHMMSS.log` - Detailed connection logs
        
        #### Quick Fixes:
        
        1. **Restart the app**: `streamlit run app.py`
        2. **Clear session**: Click "Clear All Data" in sidebar
        3. **Check server**: `curl http://119.13.110.147:8000/health`
        4. **Test with curl**: `curl -H "Accept: text/event-stream" http://119.13.110.147:8000/sse`
        """)

if __name__ == "__main__":
    main()