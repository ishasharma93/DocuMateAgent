# GitHub Repository Summarization Agent

A Python-based intelligent agent that analyzes GitHub repositories and generates comprehensive summary documents in markdown format to help developers understand codebases quickly.

## Features

- **Repository Analysis**: Traverse and analyze entire GitHub repositories
- **Code Structure Detection**: Identify project structure, main components, and architecture patterns
- **Language Detection**: Support for multiple programming languages and frameworks
- **Dependency Analysis**: Extract and analyze project dependencies
- **Documentation Extraction**: Parse README files, comments, and docstrings
- **Smart Summarization**: Generate intelligent summaries with key insights
- **🤖 LLM-Powered Code Analysis**: AI-driven code explanations and functionality descriptions
- **🔍 Intelligent Code Understanding**: Detailed explanations of what code actually does
- **💡 AI-Generated Recommendations**: Smart suggestions for code improvements
- **🔧 MCP Integration**: Model Context Protocol server-client for Azure DevOps & GitHub APIs
- **⚡ Multi-Platform Support**: Analyze repositories from GitHub and Azure DevOps
- **Markdown Output**: Professional markdown reports with structured information

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Before using the tool, you'll need to set up API keys:

### Required: GitHub Token
1. Go to [GitHub Settings > Tokens](https://github.com/settings/tokens)
2. Generate a new personal access token
3. Set the `GITHUB_TOKEN` environment variable or use `--token` argument

### Optional: Azure DevOps Credentials (for Azure DevOps integration)
1. Go to Azure DevOps > User Settings > Personal Access Tokens
2. Generate a new PAT with Code (read) permissions
3. Set the `AZURE_DEVOPS_ORGANIZATION` and `AZURE_DEVOPS_PAT` environment variables

### Optional: OpenAI API Key (for LLM-powered analysis)
1. Get an API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. Set the `OPENAI_API_KEY` environment variable or use `--llm-api-key` argument
3. This enables detailed code explanations and AI-driven insights

```bash
# Set environment variables
export GITHUB_TOKEN="your_github_token_here"
export AZURE_DEVOPS_ORGANIZATION="your_org_name"  # Optional, for Azure DevOps
export AZURE_DEVOPS_PAT="your_azure_devops_pat"   # Optional, for Azure DevOps
export OPENAI_API_KEY="your_openai_key_here"      # Optional, for enhanced analysis
```

## Usage

### Basic Usage

```python
from repo_summarizer import GitHubRepoSummarizer

# Initialize the summarizer (with optional LLM support)
summarizer = GitHubRepoSummarizer(
    github_token="your_token",
    llm_api_key="your_openai_key",  # Optional
    enable_llm_analysis=True  # Enable AI-powered code analysis
)

# Analyze a repository
summary = summarizer.analyze_repository("https://github.com/username/repo")

# Generate markdown report with AI explanations
markdown_report = summarizer.generate_markdown_summary(summary)

# Save to file
with open("repo_summary.md", "w") as f:
    f.write(markdown_report)
```

### MCP Integration (Azure DevOps & GitHub)

```python
from src.llm_code_analyzer import LLMCodeAnalyzer

# Initialize with MCP support for multi-platform analysis
analyzer = LLMCodeAnalyzer(
    enable_mcp=True,
    azure_devops_org="your-org",      # Optional, for Azure DevOps
    azure_devops_pat="your-pat",      # Optional, for Azure DevOps  
    github_token="your-github-token", # For GitHub
    llm_api_key="your_openai_key"     # Optional, for AI analysis
)

# Analyze GitHub repository
github_result = await analyzer.analyze_repository_with_mcp(
    "https://github.com/microsoft/vscode", "github"
)

# Analyze Azure DevOps repository
azure_result = await analyzer.analyze_repository_with_mcp(
    "https://dev.azure.com/microsoft/vscode/_git/vscode", "azure_devops"
)
```

### Command Line Usage

```bash
# Basic analysis
python main.py --repo-url https://github.com/username/repo --output summary.md

# With LLM-powered code analysis
python main.py --repo microsoft/vscode --llm-api-key your_openai_key --output vscode_analysis.md

# Quick analysis without LLM
python main.py --repo facebook/react --quick --disable-llm

# Custom LLM model
python main.py --repo django/django --llm-model gpt-3.5-turbo --output django_summary.md

# MCP Integration demo
python examples/mcp_demo.py
```

## Project Structure

```
DocuMate/
├── src/
│   ├── __init__.py
│   ├── repo_summarizer.py      # Main summarization engine
│   ├── code_analyzer.py        # Code analysis utilities
│   ├── github_client.py        # GitHub API client
│   ├── markdown_generator.py   # Markdown report generator
│   └── llm_code_analyzer/      # LLM integration with MCP support
│       ├── __init__.py
│       ├── llm_code_analyzer.py
│       └── mcp/               # Model Context Protocol integration
│           ├── __init__.py
│           ├── server.py      # MCP server base
│           ├── client.py      # MCP client base
│           ├── azure_devops_client.py  # Azure DevOps API
│           └── github_client.py        # GitHub API
├── tests/
│   ├── __init__.py
│   ├── test_repo_summarizer.py
│   ├── test_code_analyzer.py
│   ├── test_mcp_basic.py       # MCP functionality tests
│   └── test_llm_code_analyzer_mcp.py  # LLM-MCP integration tests
├── examples/
│   ├── sample_summary.md
│   └── mcp_demo.py             # MCP integration demo
├── main.py                     # CLI entry point
├── requirements.txt
├── MCP_INTEGRATION.md          # MCP documentation
└── README.md
```

## Configuration

The agent can be configured through environment variables or configuration files:

### Environment Variables

- `GITHUB_TOKEN`: GitHub personal access token for API access
- `AZURE_DEVOPS_ORGANIZATION`: Azure DevOps organization name (optional)
- `AZURE_DEVOPS_PAT`: Azure DevOps Personal Access Token (optional)
- `OPENAI_API_KEY`: OpenAI API key for LLM-powered code analysis (optional)
- `MAX_FILE_SIZE`: Maximum file size to analyze (default: 1MB)
- `MAX_FILES_TO_ANALYZE`: Maximum number of files to analyze (default: 500)
- `MAX_FILES_FOR_LLM_ANALYSIS`: Maximum files for LLM analysis (default: 15)
- `MAX_CODE_LENGTH_FOR_LLM`: Maximum code length for LLM analysis (default: 8000 chars)
- `MAX_CONCURRENT_LLM_REQUESTS`: Concurrent LLM requests (default: 3)

### Configuration Files

Copy `.env.example` to `.env` and update with your values.

## Output Format

The generated markdown summary includes:

1. **Repository Overview** - Basic stats, languages, topics
2. **Project Structure** - File organization and directory breakdown  
3. **Technology Stack** - Frameworks, tools, and technologies used
4. **Dependencies** - Production and development dependencies
5. **Code Metrics** - Lines of code, complexity analysis
6. **Architecture & Patterns** - Detected architectural patterns
7. **🤖 Code Analysis & Explanations** - AI-powered code understanding
   - Detailed file-by-file analysis
   - Functionality explanations
   - Key components identification
   - Code pattern recognition
   - Improvement suggestions
8. **Documentation Quality** - Assessment of documentation coverage
9. **Development Workflow** - CI/CD, testing, and development setup
10. **Recommendations** - AI-enhanced suggestions for improvement

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License
