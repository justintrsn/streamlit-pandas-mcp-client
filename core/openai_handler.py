"""OpenAI API handler for pandas-chat-app"""

import json
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import streamlit as st
from openai import OpenAI
from config import get_settings, get_prompt_manager
from utils import get_logger, ChartHandler, run_async
from .mcp_client import MCPClient


class OpenAIHandler:
    """Handle OpenAI API interactions and tool orchestration"""
    
    def __init__(self, mcp_client: MCPClient):
        self.settings = get_settings()
        self.logger = get_logger()
        self.prompt_manager = get_prompt_manager()
        self.chart_handler = ChartHandler()
        self.mcp_client = mcp_client
        self.client: Optional[OpenAI] = None
        
    def initialize(self, api_key: str):
        """Initialize OpenAI client with API key"""
        self.client = OpenAI(api_key=api_key)
        self.settings.openai_api_key = api_key
        
    def process_message(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        file_contents: Dict[str, str]
    ) -> Tuple[str, List[int]]:
        """
        Process messages with OpenAI and handle tool calls.
        
        Returns:
            Tuple of (response_text, chart_indices)
        """
        if not self.client:
            return "Please enter your OpenAI API key.", []
            
        total_tool_calls = 0
        tool_logs = []
        chart_indices = []
        
        while total_tool_calls < self.settings.max_tool_calls:
            # Call OpenAI
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=self.settings.openai_temperature,
                max_tokens=self.settings.openai_max_tokens
            )
            
            # Log OpenAI call
            response_time_ms = (time.time() - start_time) * 1000
            self.logger.log_openai_call(
                messages_count=len(messages),
                tools_count=len(tools),
                model=self.settings.openai_model,
                response_time_ms=response_time_ms,
                tokens_used={
                    "prompt": response.usage.prompt_tokens if response.usage else 0,
                    "completion": response.usage.completion_tokens if response.usage else 0,
                    "total": response.usage.total_tokens if response.usage else 0
                } if response.usage else None
            )
            
            assistant_message = response.choices[0].message
            
            # If no tool calls, return the response
            if not assistant_message.tool_calls:
                st.session_state.tool_logs = tool_logs
                return assistant_message.content, chart_indices
                
            # Add assistant message
            messages.append({
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in assistant_message.tool_calls
                ]
            })
            
            # Execute tool calls
            for tool_call in assistant_message.tool_calls:
                total_tool_calls += 1
                if total_tool_calls > self.settings.max_tool_calls:
                    break
                    
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                # Handle file injection
                if self.mcp_client.needs_file_injection(tool_name):
                    filename = tool_args.get("filename", "")
                    if filename in file_contents:
                        tool_args["content"] = file_contents[filename]
                        st.info(f"📤 Injecting content for {filename}")
                        
                # Execute tool with status display
                result = self.execute_tool_with_status(
                    tool_name,
                    tool_args,
                    tool_logs
                )
                
                # Check for chart creation
                if tool_name in self.chart_handler.chart_tools:
                    chart_info = self.handle_chart_creation(tool_name, result)
                    if chart_info:
                        chart_indices.append(chart_info['index'])
                        
                # Add result to messages
                if len(result) > 5000:
                    result = result[:5000] + "\n...(truncated)"
                    
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
                
        # Final response
        st.session_state.tool_logs = tool_logs
        
        final_response = self.client.chat.completions.create(
            model=self.settings.openai_model,
            messages=messages,
            temperature=self.settings.openai_temperature,
            max_tokens=self.settings.openai_max_tokens
        )
        
        return final_response.choices[0].message.content, chart_indices
        
    def execute_tool_with_status(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_logs: List[Dict]
    ) -> str:
        """Execute tool and display status"""
        
        # Log entry
        log_entry = {
            "tool": tool_name,
            "args": tool_args,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        
        with st.status(f"Calling {tool_name}...", expanded=True) as status:
            # Show arguments
            display_args = self.format_args_for_display(tool_args)
            status.write(f"**Arguments:** `{json.dumps(display_args, indent=2)}`")
            
            # Call tool
            result = run_async(self.mcp_client.call_tool(tool_name, tool_args))
            log_entry["result"] = result[:500]
            
            # Parse and show result
            self.display_tool_result(result, status, tool_name, log_entry)
            
        tool_logs.append(log_entry)
        return result
        
    def format_args_for_display(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Format arguments for display, truncating large content"""
        display_args = args.copy()
        
        # Truncate large fields
        for key in ["content", "html_content", "code"]:
            if key in display_args and isinstance(display_args[key], str):
                if len(display_args[key]) > 100:
                    display_args[key] = f"<{len(args[key])} chars>"
                    
        return display_args
        
    def display_tool_result(
        self,
        result: str,
        status,
        tool_name: str,
        log_entry: Dict
    ):
        """Display tool execution result in status"""
        try:
            result_data = json.loads(result)
            success = result_data.get("success", False)
            
            if success:
                status.write(f"✅ **Success!**")
                
                # Show relevant fields
                if "filepath" in result_data:
                    status.write(f"Filepath: `{result_data['filepath']}`")
                if "dataframe_info" in result_data:
                    info = result_data["dataframe_info"]
                    status.write(f"Shape: {info.get('shape', '?')}")
                if "chart_type" in result_data:
                    status.write(f"Chart: {result_data['chart_type']}")
                    
                status.update(label=f"✅ {tool_name}", state="complete")
            else:
                error = result_data.get("error", "Unknown error")
                status.write(f"❌ **Failed:** {error}")
                status.update(label=f"❌ {tool_name}: {error[:50]}", state="error")
                log_entry["error"] = error
        except:
            # Non-JSON result
            if "error" in result.lower():
                status.update(label=f"⚠️ {tool_name}", state="error")
            else:
                status.update(label=f"✅ {tool_name}", state="complete")
            status.write(f"Result: {result[:200]}...")
            
    def handle_chart_creation(self, tool_name: str, result: str) -> Optional[Dict[str, Any]]:
        """Handle chart creation and fetch HTML"""
        
        chart_info = self.chart_handler.detect_chart_in_response(tool_name, result)
        
        if not chart_info:
            return None
            
        # Automatically fetch HTML content
        try:
            html_result = run_async(
                self.mcp_client.call_tool(
                    "get_chart_html_tool",
                    {"filepath": chart_info['filepath']}
                )
            )
            
            html_data = json.loads(html_result)
            
            if html_data.get('success'):
                # Store chart
                index = self.chart_handler.store_chart(
                    chart_info,
                    html_data['html_content']
                )
                
                # Display inline
                self.chart_handler.display_chart(
                    html_data['html_content'],
                    title=chart_info.get('chart_type', 'Chart')
                )
                
                return {'index': index, 'info': chart_info}
        except Exception as e:
            self.logger.log("error", f"Failed to fetch chart HTML: {str(e)}")
            st.warning(f"Chart created but could not display: {chart_info['filename']}")
            
        return None
        
    def prepare_system_prompt(self, file_contents: Dict[str, str]) -> str:
        """Prepare system prompt with context"""
        
        files_info = ", ".join(file_contents.keys()) if file_contents else ""
        
        return self.prompt_manager.get_formatted_prompt(
            use_custom=self.settings.use_custom_prompt,
            files_info=files_info,
            additional_context={
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "model": self.settings.openai_model,
                "tools_available": len(self.mcp_client.tools)
            }
        )
        
    def prepare_messages(
        self,
        user_prompt: str,
        file_contents: Dict[str, str]
    ) -> List[Dict[str, str]]:
        """Prepare messages for API call"""
        
        system_prompt = self.prepare_system_prompt(file_contents)
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if st.session_state.get('messages'):
            recent_messages = st.session_state.messages[-self.settings.context_window:]
            for msg in recent_messages:
                if msg["role"] in ["user", "assistant"]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                    
        return messages