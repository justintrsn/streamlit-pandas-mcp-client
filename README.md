# 🐼 Pandas Data Chat - Streamlit MCP Client

A powerful, AI-powered data analysis assistant that combines Streamlit, OpenAI, and Model Context Protocol (MCP) to provide natural language data analysis capabilities.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-red)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-green)
![MCP](https://img.shields.io/badge/MCP-Compatible-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🌟 Features

### 📊 Data Analysis
- **Multi-format Support**: Load CSV, Excel (XLSX/XLS), JSON, and Parquet files
- **Natural Language Queries**: Ask questions about your data in plain English
- **Pandas Integration**: Full pandas operations through MCP tools
- **Statistical Analysis**: Automated data profiling and statistics

### 📈 Visualizations
- **Interactive Charts**: Create bar, line, pie, scatter plots
- **Correlation Heatmaps**: Visualize relationships in your data
- **Time Series Analysis**: Plot and analyze temporal data
- **Export Options**: Download charts as HTML files

### 🤖 AI-Powered
- **OpenAI Integration**: Uses GPT-4 models for intelligent responses
- **Tool Orchestration**: Automatically chains MCP tools for complex analyses
- **Context Awareness**: Maintains conversation history
- **Custom Prompts**: Configure system prompts for specific use cases

### 🔧 MCP Tools
- **20+ Tools Available**: Data loading, transformation, visualization
- **Server-Side Processing**: Efficient handling of large datasets
- **Real-time Execution**: See tool calls and results as they happen

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- An OpenAI API key
- MCP server running (see [MCP Server Setup](#mcp-server-setup))

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/streamlit-mcp-client.git
cd streamlit-mcp-client
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
# Create .env file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

4. **Run the application**
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## 📁 Project Structure

```
streamlit-mcp-client/
├── app.py                  # Main application (Home page)
├── pages/                  # Streamlit pages
│   ├── 1._📁_Files.py     # File management page
│   └── 2._📊_Charts.py    # Charts gallery page
├── components/             # UI components
│   ├── chat.py            # Chat interface
│   ├── sidebar.py         # Sidebar with settings
│   ├── file_manager.py    # File upload/management
│   └── connection_status.py # MCP connection status
├── core/                   # Core functionality
│   ├── mcp_client.py      # MCP server communication
│   ├── openai_handler.py  # OpenAI API integration
│   └── session.py         # Session state management
├── utils/                  # Utility functions
│   ├── async_helpers.py   # Async operation helpers
│   ├── chart_handler.py   # Chart detection/display
│   └── logger.py          # Logging system
├── config/                 # Configuration
│   ├── settings.py        # App settings
│   ├── prompt_manager.py  # System prompt management
│   └── prompts/           # Prompt templates
├── logs/                   # Application logs
├── temp/                   # Temporary file storage
└── requirements.txt        # Python dependencies
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# MCP Server Configuration
MCP_SSE_URL=http://localhost:8000/sse
MCP_TIMEOUT=30

# OpenAI Configuration
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=1500

# Application Settings
APP_TITLE=Pandas Data Chat
APP_ICON=📊
APP_LAYOUT=wide
MAX_FILE_SIZE_MB=100
```

### MCP Server Setup

The application requires an MCP server running with pandas tools. Example server setup:

```python
# mcp_server.py
from mcp.server import Server
from mcp.server.sse import sse_handler

# Initialize server with pandas tools
server = Server("pandas-server")

# Add your tools here
# ...

# Run server
if __name__ == "__main__":
    from mcp.server.sse import run_sse
    run_sse(server, port=8000)
```

## 📖 Usage Guide

### 1. Connect to MCP Server

1. Open the sidebar (left side)
2. Enter your OpenAI API key
3. Click "🔄 Connect to MCP"
4. Verify connection status shows green

### 2. Upload Data Files

1. Navigate to **📁 Files** page
2. Upload your data files (CSV, Excel, JSON, or Parquet)
3. Files are automatically prepared for analysis

### 3. Analyze with Chat

1. Go to **🏠 Home** page
2. Ask questions about your data:
   - "Load sales.csv and show me a summary"
   - "Create a bar chart of top 10 products"
   - "Find correlations between price and quantity"
   - "Clean the data and remove duplicates"

### 4. View Charts

1. Navigate to **📊 Charts** page
2. View all generated visualizations
3. Download individual charts or export entire gallery

## 🛠️ Available MCP Tools

### Data Loading
- `upload_temp_file_tool` - Upload file content to server
- `load_dataframe_tool` - Load file into pandas DataFrame
- `preview_file_tool` - Preview file contents

### Data Analysis
- `run_pandas_code_tool` - Execute pandas operations
- `get_dataframe_info_tool` - Get DataFrame structure
- `list_dataframes_tool` - List available DataFrames
- `validate_pandas_code_tool` - Validate code before execution

### Visualization
- `create_chart_tool` - Create various chart types
- `create_correlation_heatmap_tool` - Generate correlation matrices
- `create_time_series_chart_tool` - Create time series plots
- `get_chart_html_tool` - Retrieve chart HTML content

## 🎨 Customization

### Custom System Prompts

1. Navigate to Sidebar → **📝 Prompt** tab
2. Toggle "Use Custom Prompt"
3. Edit the prompt template
4. Save changes

### Display Settings

- Adjust chart heights in Charts page
- Configure sidebar state (expanded/collapsed)
- Modify temperature and token limits for OpenAI

## 🐛 Troubleshooting

### MCP Connection Issues

```
Error: Failed to connect to MCP server
```
**Solution:**
- Verify MCP server is running
- Check the SSE URL is correct
- Ensure no firewall blocking the connection

### OpenAI API Errors

```
Error: Invalid API key
```
**Solution:**
- Verify your OpenAI API key is correct
- Check you have sufficient credits
- Ensure the selected model is available

### File Upload Issues

```
Error: File too large
```
**Solution:**
- Check file size limit in settings (default: 100MB)
- Consider splitting large files
- Use Parquet format for better compression

## 📊 Example Queries

### Basic Analysis
```
"Load data.csv and show me the first 10 rows"
"What are the column types in my dataset?"
"Show me basic statistics for all numeric columns"
```

### Data Cleaning
```
"Check for missing values in the dataset"
"Remove duplicate rows based on 'id' column"
"Fill missing values with the mean"
```

### Visualizations
```
"Create a bar chart of sales by category"
"Show me a correlation heatmap"
"Plot revenue over time as a line chart"
"Create a scatter plot of price vs quantity"
```

### Advanced Analysis
```
"Group by category and calculate average sales"
"Find the top 10 customers by total purchases"
"Calculate month-over-month growth rate"
"Perform a pivot table analysis"
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Streamlit](https://streamlit.io/) for the amazing web framework
- [OpenAI](https://openai.com/) for GPT models
- [Model Context Protocol](https://github.com/anthropics/mcp) for tool orchestration
- [Pandas](https://pandas.pydata.org/) for data manipulation

## 📧 Contact

For questions or support, please open an issue on GitHub or contact the maintainers.

---

**Note:** This is an active project under development. Features and APIs may change.