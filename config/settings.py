"""Configuration settings for the MCP Client application."""

import os
from pathlib import Path
from typing import Optional
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application settings management."""
    
    # Project paths
    ROOT_DIR = Path(__file__).parent.parent
    STATIC_DIR = ROOT_DIR / "static"
    CHARTS_DIR = STATIC_DIR / "charts"
    TEMP_DIR = ROOT_DIR / "temp"
    
    # MCP Server Configuration
    MCP_SSE_URL: str = os.getenv("MCP_SSE_URL", "http://119.13.110.147:8000/sse")
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    
    # File Upload Settings
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
    ALLOWED_FILE_TYPES: list[str] = [
        "csv", "tsv", "xlsx", "xls", "json", "parquet"
    ]
    
    # Chart Settings
    CHART_WIDTH: int = int(os.getenv("CHART_WIDTH", "800"))
    CHART_HEIGHT: int = int(os.getenv("CHART_HEIGHT", "600"))
    
    # UI Settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    PAGE_TITLE: str = "MCP Data Analysis Client"
    PAGE_ICON: str = "📊"
    LAYOUT: str = "wide"
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist."""
        cls.STATIC_DIR.mkdir(exist_ok=True)
        cls.CHARTS_DIR.mkdir(exist_ok=True)
        cls.TEMP_DIR.mkdir(exist_ok=True)
        
        # Create .gitkeep for charts directory
        gitkeep = cls.CHARTS_DIR / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()
    
    @classmethod
    def get_openai_api_key(cls) -> Optional[str]:
        """Get OpenAI API key from environment or Streamlit session."""
        # First check session state (user input)
        if "openai_api_key" in st.session_state and st.session_state.openai_api_key:
            return st.session_state.openai_api_key
        
        # Fallback to environment variable
        return cls.OPENAI_API_KEY
    
    @classmethod
    def validate_config(cls) -> dict[str, bool]:
        """Validate configuration and return status."""
        status = {
            "mcp_server": bool(cls.MCP_SSE_URL),
            "openai_key": bool(cls.get_openai_api_key()),
            "directories": True
        }
        
        try:
            cls.ensure_directories()
        except Exception:
            status["directories"] = False
            
        return status

# Global settings instance
settings = Settings()