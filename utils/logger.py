"""
utils/logger.py - Comprehensive logging utility for MCP Client
Save this as utils/logger.py
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
import json
from typing import Optional, Dict, Any
import traceback

class MCPClientLogger:
    """Custom logger for MCP Client with file and console output."""
    
    def __init__(self, name: str = "mcp_client", log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        self.logger.handlers = []
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # File handler for all logs
        log_file = self.log_dir / f"mcp_client_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(file_handler)
        
        # File handler for errors only
        error_file = self.log_dir / f"mcp_errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(error_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(error_handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        self.logger.addHandler(console_handler)
        
        # Connection log file for detailed connection debugging
        self.connection_log = self.log_dir / f"connection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        self.logger.info(f"Logger initialized. Logs directory: {self.log_dir.absolute()}")
    
    def log_connection_attempt(self, url: str, method: str = "connect"):
        """Log a connection attempt with details."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "url": url,
            "event": "connection_attempt"
        }
        
        self.logger.info(f"Attempting connection to {url} using {method}")
        
        # Write to connection log
        with open(self.connection_log, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def log_connection_response(self, url: str, status_code: Optional[int] = None, 
                               error: Optional[str] = None, success: bool = False):
        """Log connection response details."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "status_code": status_code,
            "error": error,
            "success": success,
            "event": "connection_response"
        }
        
        if success:
            self.logger.info(f"Successfully connected to {url} (Status: {status_code})")
        else:
            self.logger.error(f"Connection failed to {url} - Error: {error} (Status: {status_code})")
        
        # Write to connection log
        with open(self.connection_log, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def log_tool_call(self, tool_name: str, params: Dict[str, Any], result: Optional[Any] = None, 
                     error: Optional[str] = None):
        """Log MCP tool calls."""
        # Don't log sensitive data
        safe_params = self._sanitize_params(params)
        
        if error:
            self.logger.error(f"Tool call failed: {tool_name} - Error: {error}")
            self.logger.debug(f"Parameters: {safe_params}")
        else:
            self.logger.debug(f"Tool call successful: {tool_name}")
            self.logger.debug(f"Parameters: {safe_params}")
    
    def log_exception(self, exception: Exception, context: str = ""):
        """Log exceptions with full traceback."""
        error_msg = f"Exception in {context}: {str(exception)}"
        self.logger.error(error_msg)
        self.logger.debug(f"Traceback:\n{traceback.format_exc()}")
        
        # Write detailed error to connection log
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "exception",
            "context": context,
            "error": str(exception),
            "type": type(exception).__name__,
            "traceback": traceback.format_exc()
        }
        
        with open(self.connection_log, 'a') as f:
            f.write(json.dumps(error_entry) + '\n')
    
    def log_session_state(self, session_state: Dict[str, Any]):
        """Log current session state for debugging."""
        safe_state = {
            "mcp_connected": session_state.get("mcp_connected", False),
            "uploaded_files_count": len(session_state.get("uploaded_files", {})),
            "loaded_dataframes_count": len(session_state.get("loaded_dataframes", {})),
            "generated_charts_count": len(session_state.get("generated_charts", {})),
            "has_api_key": bool(session_state.get("openai_api_key", ""))
        }
        
        self.logger.debug(f"Session state: {safe_state}")
    
    def log_network_details(self, url: str):
        """Log network details for debugging connectivity."""
        import socket
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        hostname = parsed.hostname
        port = parsed.port or 80
        
        details = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "hostname": hostname,
            "port": port,
            "event": "network_check"
        }
        
        # Try to resolve hostname
        try:
            ip_address = socket.gethostbyname(hostname)
            details["ip_address"] = ip_address
            self.logger.info(f"Resolved {hostname} to {ip_address}")
        except socket.gaierror as e:
            details["dns_error"] = str(e)
            self.logger.error(f"DNS resolution failed for {hostname}: {e}")
        
        # Test socket connection
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((hostname, port))
            sock.close()
            
            if result == 0:
                details["socket_connection"] = "success"
                self.logger.info(f"Socket connection successful to {hostname}:{port}")
            else:
                details["socket_connection"] = f"failed_code_{result}"
                self.logger.error(f"Socket connection failed to {hostname}:{port} (Error code: {result})")
        except Exception as e:
            details["socket_error"] = str(e)
            self.logger.error(f"Socket test failed: {e}")
        
        # Write to connection log
        with open(self.connection_log, 'a') as f:
            f.write(json.dumps(details) + '\n')
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from parameters before logging."""
        safe_params = {}
        for key, value in params.items():
            if key.lower() in ['api_key', 'password', 'token', 'secret', 'openai_api_key']:
                safe_params[key] = "***REDACTED***"
            elif key == 'file_content' and isinstance(value, str) and len(value) > 100:
                safe_params[key] = f"<binary_data_{len(value)}_chars>"
            else:
                safe_params[key] = value
        return safe_params
    
    def get_recent_logs(self, lines: int = 50) -> str:
        """Get recent log entries for display."""
        log_file = self.log_dir / f"mcp_client_{datetime.now().strftime('%Y%m%d')}.log"
        if log_file.exists():
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        return "No logs found for today."
    
    def get_connection_logs(self) -> str:
        """Get connection-specific logs."""
        if self.connection_log.exists():
            with open(self.connection_log, 'r') as f:
                return f.read()
        return "No connection logs found."

# Global logger instance
logger = MCPClientLogger()

# Convenience functions
def log_info(message: str):
    logger.logger.info(message)

def log_error(message: str):
    logger.logger.error(message)

def log_debug(message: str):
    logger.logger.debug(message)

def log_warning(message: str):
    logger.logger.warning(message)

def log_connection(url: str, success: bool, error: Optional[str] = None, status_code: Optional[int] = None):
    logger.log_connection_response(url, status_code, error, success)

def log_exception(e: Exception, context: str = ""):
    logger.log_exception(e, context)