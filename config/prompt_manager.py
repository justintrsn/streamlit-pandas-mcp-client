"""Prompt management for system messages"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import streamlit as st


class PromptManager:
    """Manage system prompts for the chat application"""
    
    def __init__(self, prompt_dir: Path = Path("config/prompts")):
        self.prompt_dir = prompt_dir
        self.prompt_dir.mkdir(parents=True, exist_ok=True)
        
        self.default_prompt_path = self.prompt_dir / "default.txt"
        self.custom_prompt_path = self.prompt_dir / "custom.txt"
        
        # Create default prompt if it doesn't exist
        self._ensure_default_prompt()
        
    def _ensure_default_prompt(self):
        """Create default prompt file if it doesn't exist"""
        if not self.default_prompt_path.exists():
            self.default_prompt_path.write_text(self.get_default_prompt_template())
            
        # Create custom prompt from default if it doesn't exist
        if not self.custom_prompt_path.exists():
            self.custom_prompt_path.write_text(self.get_default_prompt_template())
            
    def get_default_prompt_template(self) -> str:
        """Get the default system prompt template"""
        return """You are a data analysis assistant with MCP server access.

{files_info}

## Your Capabilities:
- Load and analyze data files (CSV, Excel, JSON, Parquet)
- Execute pandas operations for data manipulation
- Create interactive visualizations (charts, graphs, heatmaps)
- Perform statistical analysis and calculations
- Clean and transform data

## Important Instructions:
1. When files are uploaded, you MUST:
   - FIRST use upload_temp_file_tool to upload to server
   - THEN use load_dataframe_tool with the returned filepath
   - FINALLY use analysis tools to process the data

2. For data analysis:
   - Be thorough and systematic
   - Check data quality and report issues
   - Suggest appropriate analyses based on data structure
   - Create visualizations when they would be helpful

3. For visualizations:
   - Choose appropriate chart types for the data
   - Include clear titles and labels
   - Use create_chart_tool, create_correlation_heatmap_tool, or create_time_series_chart_tool
   - After creating a chart, always mention it was created successfully

4. Communication style:
   - Be clear and concise
   - Explain your reasoning
   - Highlight important findings
   - Suggest next steps when appropriate

Remember: Chain tools together to complete complex analyses. Always verify data is loaded before attempting operations."""
        
    def load_prompt(self, use_custom: bool = False) -> str:
        """Load prompt from file"""
        prompt_path = self.custom_prompt_path if use_custom else self.default_prompt_path
        
        try:
            return prompt_path.read_text()
        except FileNotFoundError:
            # Fallback to default template
            return self.get_default_prompt_template()
            
    def save_custom_prompt(self, prompt_text: str):
        """Save custom prompt to file"""
        self.custom_prompt_path.write_text(prompt_text)
        
    def get_formatted_prompt(
        self,
        use_custom: bool = False,
        files_info: str = "",
        tools_info: Optional[List[Dict[str, Any]]] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get formatted prompt with context"""
        base_prompt = self.load_prompt(use_custom)
        
        # Format files info
        if files_info:
            files_section = f"""
IMPORTANT: The user has uploaded these files that are ready for analysis:
{files_info}

To analyze these files, you MUST:
1. FIRST use upload_temp_file_tool with the filename to upload it to the server
2. THEN use load_dataframe_tool with the filepath returned from the upload
3. FINALLY use run_pandas_code_tool or other tools to analyze

The file contents will be automatically injected when you call upload_temp_file_tool.
"""
        else:
            files_section = "No files have been uploaded yet. The user can upload CSV, Excel, JSON, or Parquet files for analysis."
            
        # Replace placeholder
        formatted = base_prompt.replace("{files_info}", files_section)
        
        # Add tools section
        if tools_info:
            formatted += "\n\n## Available MCP Tools:\n"
            for tool in tools_info:
                name = tool["function"]["name"]
                desc = tool["function"].get("description", "No description")
                params = tool["function"].get("parameters", {}).get("properties", {})
                formatted += f"\n**{name}**:\n  {desc}\n"
                if params:
                    formatted += "  Parameters:\n"
                    for param_name, param_info in params.items():
                        param_desc = param_info.get("description", "")
                        param_type = param_info.get("type", "")
                        formatted += f"    - {param_name} ({param_type}): {param_desc}\n"
        
        # Add any additional context
        if additional_context:
            context_lines = []
            for key, value in additional_context.items():
                context_lines.append(f"{key}: {value}")
            if context_lines:
                formatted += "\n\n## Additional Context:\n" + "\n".join(context_lines)
                
        return formatted
        
    def reset_custom_prompt(self):
        """Reset custom prompt to default"""
        self.custom_prompt_path.write_text(self.get_default_prompt_template())
        
    def get_prompt_preview(self, use_custom: bool = False, max_lines: int = 20) -> str:
        """Get a preview of the prompt"""
        prompt = self.load_prompt(use_custom)
        lines = prompt.split('\n')[:max_lines]
        
        if len(prompt.split('\n')) > max_lines:
            lines.append("... (truncated)")
            
        return '\n'.join(lines)
        
    def create_prompt_editor_ui(self):
        """Create Streamlit UI for editing prompts"""
        st.subheader("📝 Prompt Configuration")
        
        # Toggle between default and custom
        use_custom = st.checkbox(
            "Use Custom Prompt",
            value=st.session_state.get('use_custom_prompt', False),
            help="Toggle between default and custom system prompts"
        )
        st.session_state.use_custom_prompt = use_custom
        
        # Tabs for viewing/editing
        tab1, tab2 = st.tabs(["View", "Edit"])
        
        with tab1:
            # Show current prompt
            st.caption("Current System Prompt:")
            current_prompt = self.load_prompt(use_custom)
            st.text_area(
                "Prompt",
                value=current_prompt,
                height=300,
                disabled=True,
                key="prompt_view"
            )
            
        with tab2:
            if use_custom:
                # Edit custom prompt
                st.caption("Edit Custom Prompt:")
                edited_prompt = st.text_area(
                    "Custom Prompt",
                    value=self.load_prompt(True),
                    height=400,
                    key="prompt_edit",
                    help="Edit your custom system prompt. Changes are saved automatically."
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Save Changes"):
                        self.save_custom_prompt(edited_prompt)
                        st.success("Custom prompt saved!")
                        
                with col2:
                    if st.button("🔄 Reset to Default"):
                        self.reset_custom_prompt()
                        st.success("Custom prompt reset to default!")
                        st.rerun()
            else:
                st.info("Enable 'Use Custom Prompt' to edit the system prompt")
                
    def compare_prompts(self) -> Dict[str, Any]:
        """Compare default and custom prompts"""
        default_prompt = self.load_prompt(False)
        custom_prompt = self.load_prompt(True)
        
        default_lines = default_prompt.split('\n')
        custom_lines = custom_prompt.split('\n')
        
        return {
            'default_length': len(default_prompt),
            'custom_length': len(custom_prompt),
            'default_lines': len(default_lines),
            'custom_lines': len(custom_lines),
            'is_different': default_prompt != custom_prompt,
            'length_diff': len(custom_prompt) - len(default_prompt),
            'line_diff': len(custom_lines) - len(default_lines)
        }


# Global instance
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get or create the global prompt manager instance"""
    global _prompt_manager
    
    if _prompt_manager is None:
        from .settings import get_settings
        settings = get_settings()
        _prompt_manager = PromptManager(settings.prompt_dir)
        
    return _prompt_manager