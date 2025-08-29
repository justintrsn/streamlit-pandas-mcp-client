"""Logging configuration for pandas-chat-app"""

import logging
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler
import streamlit as st


class AppLogger:
    """Centralized logging system with file and Streamlit handlers"""
    
    def __init__(
        self,
        name: str = "pandas_chat",
        log_dir: str = "logs",
        app_log_file: str = "app.log",
        mcp_log_file: str = "mcp_calls.log",
        log_level: str = "INFO",
        max_bytes: int = 10_485_760,  # 10MB
        backup_count: int = 5
    ):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Main app logger
        self.logger = self._setup_logger(
            f"{name}.app",
            self.log_dir / app_log_file,
            log_level,
            max_bytes,
            backup_count
        )
        
        # MCP calls logger (separate for detailed tool tracking)
        self.mcp_logger = self._setup_logger(
            f"{name}.mcp",
            self.log_dir / mcp_log_file,
            log_level,
            max_bytes,
            backup_count,
            detailed=True
        )
        
        # Store recent logs for UI display
        self.recent_logs = []
        self.max_recent = 100
        
    def _setup_logger(
        self,
        logger_name: str,
        log_file: Path,
        level: str,
        max_bytes: int,
        backup_count: int,
        detailed: bool = False
    ) -> logging.Logger:
        """Setup individual logger with handlers"""
        
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level.upper()))
        
        # Clear existing handlers
        logger.handlers = []
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        
        # Format based on detail level
        if detailed:
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(funcName)-20s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console handler for development
        if sys.stdout.isatty():
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = logging.Formatter(
                '%(levelname)-8s | %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.DEBUG)
            logger.addHandler(console_handler)
        
        return logger
    
    def log(
        self,
        level: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None
    ):
        """General logging method"""
        log_method = getattr(self.logger, level.lower())
        
        # Add extra data if provided
        if extra:
            message = f"{message} | {json.dumps(extra, default=str)}"
        
        log_method(message)
        
        # Store in recent logs
        self._add_recent(level.upper(), message)
        
    def log_mcp_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Log MCP tool calls with detailed info"""
        
        # Truncate large content
        display_args = arguments.copy()
        if "content" in display_args:
            display_args["content"] = f"<{len(str(arguments['content']))} chars>"
        if "html_content" in display_args:
            display_args["html_content"] = f"<{len(str(arguments['html_content']))} chars>"
            
        log_data = {
            "tool": tool_name,
            "args": display_args,
            "duration_ms": duration_ms,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
        if not success and error:
            log_data["error"] = error
            
        # Truncate result for logging
        if isinstance(result, str) and len(result) > 500:
            log_data["result"] = result[:500] + "...<truncated>"
        elif isinstance(result, dict):
            if "html_content" in result:
                result_copy = result.copy()
                result_copy["html_content"] = f"<{len(result['html_content'])} chars>"
                log_data["result"] = result_copy
            else:
                log_data["result"] = result
        else:
            log_data["result"] = result
            
        # Log to MCP logger
        if success:
            self.mcp_logger.info(f"Tool: {tool_name} | {json.dumps(log_data, default=str)}")
        else:
            self.mcp_logger.error(f"Tool: {tool_name} | {json.dumps(log_data, default=str)}")
            
        # Store for UI display
        self._add_recent("MCP", json.dumps(log_data, default=str))
        
        # Update Streamlit session state if available
        try:
            if "tool_logs" not in st.session_state:
                st.session_state.tool_logs = []
            st.session_state.tool_logs.append(log_data)
            
            # Keep only last 50 in session
            if len(st.session_state.tool_logs) > 50:
                st.session_state.tool_logs = st.session_state.tool_logs[-50:]
        except:
            pass  # Session state not available
            
    def log_file_operation(
        self,
        operation: str,
        filename: str,
        size_bytes: Optional[int] = None,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Log file upload/processing operations"""
        
        log_data = {
            "operation": operation,
            "filename": filename,
            "timestamp": datetime.now().isoformat()
        }
        
        if size_bytes:
            log_data["size_kb"] = round(size_bytes / 1024, 2)
            
        if not success and error:
            log_data["error"] = error
            
        level = "info" if success else "error"
        self.log(level, f"File {operation}: {filename}", log_data)
        
    def log_openai_call(
        self,
        messages_count: int,
        tools_count: int,
        model: str,
        response_time_ms: float,
        tokens_used: Optional[Dict[str, int]] = None
    ):
        """Log OpenAI API calls"""
        
        log_data = {
            "model": model,
            "messages": messages_count,
            "tools": tools_count,
            "response_ms": response_time_ms,
            "timestamp": datetime.now().isoformat()
        }
        
        if tokens_used:
            log_data["tokens"] = tokens_used
            
        self.log("info", f"OpenAI API call to {model}", log_data)
        
    def log_chart_creation(
        self,
        chart_type: str,
        dataframe: str,
        filepath: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log chart generation events"""
        
        log_data = {
            "chart_type": chart_type,
            "dataframe": dataframe,
            "filepath": filepath,
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            log_data["metadata"] = metadata
            
        self.log("info", f"Chart created: {chart_type} for {dataframe}", log_data)
        self._add_recent("CHART", f"{chart_type} created for {dataframe}")
        
    def _add_recent(self, level: str, message: str):
        """Add to recent logs buffer"""
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "level": level,
            "message": message[:200]  # Truncate for display
        }
        
        self.recent_logs.append(entry)
        if len(self.recent_logs) > self.max_recent:
            self.recent_logs.pop(0)
            
    def get_recent_logs(
        self,
        count: int = 20,
        level_filter: Optional[str] = None
    ) -> list:
        """Get recent log entries for UI display"""
        
        logs = self.recent_logs[-count:]
        
        if level_filter:
            logs = [l for l in logs if l["level"] == level_filter.upper()]
            
        return logs
        
    def clear_recent(self):
        """Clear recent logs buffer"""
        self.recent_logs = []
        
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        
        log_counts = {}
        for log in self.recent_logs:
            level = log["level"]
            log_counts[level] = log_counts.get(level, 0) + 1
            
        # Get file sizes
        app_log = self.log_dir / "app.log"
        mcp_log = self.log_dir / "mcp_calls.log"
        
        stats = {
            "recent_counts": log_counts,
            "total_recent": len(self.recent_logs),
            "app_log_size_kb": round(app_log.stat().st_size / 1024, 2) if app_log.exists() else 0,
            "mcp_log_size_kb": round(mcp_log.stat().st_size / 1024, 2) if mcp_log.exists() else 0,
        }
        
        return stats


# Global logger instance
_logger = None


def get_logger() -> AppLogger:
    """Get or create the global logger instance"""
    global _logger
    
    if _logger is None:
        # Get settings from environment or use defaults
        import os
        
        log_level = os.getenv("LOG_LEVEL", "INFO")
        log_dir = os.getenv("LOG_DIR", "logs")
        
        _logger = AppLogger(
            name="pandas_chat",
            log_dir=log_dir,
            log_level=log_level
        )
        
    return _logger