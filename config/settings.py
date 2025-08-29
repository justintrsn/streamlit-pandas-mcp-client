"""Application settings and configuration management"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Settings:
    """Application configuration settings"""
    
    # MCP Server Settings
    mcp_sse_url: str = field(default_factory=lambda: os.getenv("MCP_SSE_URL", "http://119.13.110.147:8000/sse"))
    mcp_timeout: int = field(default_factory=lambda: int(os.getenv("MCP_TIMEOUT", "30")))
    mcp_max_retries: int = field(default_factory=lambda: int(os.getenv("MCP_MAX_RETRIES", "3")))
    
    # OpenAI Settings
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    openai_temperature: float = field(default_factory=lambda: float(os.getenv("OPENAI_TEMPERATURE", "0.7")))
    openai_max_tokens: int = field(default_factory=lambda: int(os.getenv("OPENAI_MAX_TOKENS", "1500")))
    max_tool_calls: int = field(default_factory=lambda: int(os.getenv("MAX_TOOL_CALLS", "10")))
    
    # Application Settings
    app_title: str = field(default_factory=lambda: os.getenv("APP_TITLE", "Pandas Data Chat"))
    app_icon: str = field(default_factory=lambda: os.getenv("APP_ICON", "📊"))
    app_layout: str = field(default_factory=lambda: os.getenv("APP_LAYOUT", "wide"))
    
    # File Settings
    max_file_size_mb: int = field(default_factory=lambda: int(os.getenv("MAX_FILE_SIZE_MB", "100")))
    allowed_file_types: list = field(default_factory=lambda: os.getenv(
        "ALLOWED_FILE_TYPES", 
        "csv,tsv,json,xlsx,xls,parquet"
    ).split(','))
    temp_dir: Path = field(default_factory=lambda: Path(os.getenv("TEMP_DIR", "temp")))
    
    # Logging Settings
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_dir: Path = field(default_factory=lambda: Path(os.getenv("LOG_DIR", "logs")))
    log_max_bytes: int = field(default_factory=lambda: int(os.getenv("LOG_MAX_BYTES", "10485760")))  # 10MB
    log_backup_count: int = field(default_factory=lambda: int(os.getenv("LOG_BACKUP_COUNT", "5")))
    
    # UI Settings
    sidebar_state: str = field(default_factory=lambda: os.getenv("SIDEBAR_STATE", "expanded"))
    theme: str = field(default_factory=lambda: os.getenv("THEME", "light"))
    show_debug: bool = field(default_factory=lambda: os.getenv("SHOW_DEBUG", "true").lower() == "true")
    
    # Chart Settings
    chart_height: int = field(default_factory=lambda: int(os.getenv("CHART_HEIGHT", "500")))
    chart_expand_default: bool = field(default_factory=lambda: os.getenv("CHART_EXPAND_DEFAULT", "true").lower() == "true")
    max_charts_stored: int = field(default_factory=lambda: int(os.getenv("MAX_CHARTS_STORED", "20")))
    
    # Session Settings
    message_history_limit: int = field(default_factory=lambda: int(os.getenv("MESSAGE_HISTORY_LIMIT", "50")))
    context_window: int = field(default_factory=lambda: int(os.getenv("CONTEXT_WINDOW", "6")))
    
    # Prompt Settings
    prompt_dir: Path = field(default_factory=lambda: Path("config/prompts"))
    default_prompt_file: str = field(default_factory=lambda: os.getenv("DEFAULT_PROMPT_FILE", "default.txt"))
    custom_prompt_file: str = field(default_factory=lambda: os.getenv("CUSTOM_PROMPT_FILE", "custom.txt"))
    use_custom_prompt: bool = field(default_factory=lambda: os.getenv("USE_CUSTOM_PROMPT", "false").lower() == "true")
    
    def __post_init__(self):
        """Initialize directories after dataclass creation"""
        # Ensure directories exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.prompt_dir.mkdir(parents=True, exist_ok=True)
        (self.temp_dir / "uploads").mkdir(parents=True, exist_ok=True)
        
    def update_from_dict(self, config: Dict[str, Any]):
        """Update settings from dictionary (e.g., from UI)"""
        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)
                
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary"""
        return {
            key: getattr(self, key)
            for key in self.__dataclass_fields__.keys()
        }
        
    def save_to_env(self, env_file: str = ".env"):
        """Save current settings to .env file"""
        env_path = Path(env_file)
        
        # Read existing env file
        existing_lines = []
        if env_path.exists():
            with open(env_path, 'r') as f:
                existing_lines = f.readlines()
                
        # Create a dict of existing keys
        existing_keys = {}
        for line in existing_lines:
            if '=' in line and not line.strip().startswith('#'):
                key = line.split('=')[0].strip()
                existing_keys[key] = line
                
        # Update or add new values
        new_lines = []
        settings_dict = {
            "MCP_SSE_URL": self.mcp_sse_url,
            "MCP_TIMEOUT": str(self.mcp_timeout),
            "MCP_MAX_RETRIES": str(self.mcp_max_retries),
            "OPENAI_API_KEY": self.openai_api_key,
            "OPENAI_MODEL": self.openai_model,
            "OPENAI_TEMPERATURE": str(self.openai_temperature),
            "OPENAI_MAX_TOKENS": str(self.openai_max_tokens),
            "MAX_TOOL_CALLS": str(self.max_tool_calls),
            "APP_TITLE": self.app_title,
            "APP_ICON": self.app_icon,
            "APP_LAYOUT": self.app_layout,
            "MAX_FILE_SIZE_MB": str(self.max_file_size_mb),
            "ALLOWED_FILE_TYPES": ','.join(self.allowed_file_types),
            "TEMP_DIR": str(self.temp_dir),
            "LOG_LEVEL": self.log_level,
            "LOG_DIR": str(self.log_dir),
            "LOG_MAX_BYTES": str(self.log_max_bytes),
            "LOG_BACKUP_COUNT": str(self.log_backup_count),
            "SIDEBAR_STATE": self.sidebar_state,
            "THEME": self.theme,
            "SHOW_DEBUG": str(self.show_debug).lower(),
            "CHART_HEIGHT": str(self.chart_height),
            "CHART_EXPAND_DEFAULT": str(self.chart_expand_default).lower(),
            "MAX_CHARTS_STORED": str(self.max_charts_stored),
            "MESSAGE_HISTORY_LIMIT": str(self.message_history_limit),
            "CONTEXT_WINDOW": str(self.context_window),
            "DEFAULT_PROMPT_FILE": self.default_prompt_file,
            "CUSTOM_PROMPT_FILE": self.custom_prompt_file,
            "USE_CUSTOM_PROMPT": str(self.use_custom_prompt).lower()
        }
        
        # Build new env file content
        for key, value in settings_dict.items():
            if key in existing_keys:
                # Update existing
                new_lines.append(f"{key}={value}\n")
            else:
                # Add new
                new_lines.append(f"{key}={value}\n")
                
        # Add back any existing keys not in our settings
        for key, line in existing_keys.items():
            if key not in settings_dict:
                new_lines.append(line)
                
        # Write back
        with open(env_path, 'w') as f:
            f.writelines(new_lines)
            
    def validate(self) -> tuple[bool, list[str]]:
        """Validate settings and return (is_valid, errors)"""
        errors = []
        
        # Check required fields
        if not self.mcp_sse_url:
            errors.append("MCP_SSE_URL is required")
            
        # Check file size limit
        if self.max_file_size_mb <= 0:
            errors.append("MAX_FILE_SIZE_MB must be positive")
            
        # Check OpenAI settings if key provided
        if self.openai_api_key and not self.openai_api_key.startswith("sk-"):
            errors.append("Invalid OpenAI API key format")
            
        # Check paths exist
        if not self.prompt_dir.exists():
            errors.append(f"Prompt directory does not exist: {self.prompt_dir}")
            
        return len(errors) == 0, errors


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance"""
    global _settings
    
    if _settings is None:
        _settings = Settings()
        
    return _settings


def reset_settings():
    """Reset settings to defaults"""
    global _settings
    _settings = Settings()
    return _settings