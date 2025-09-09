# MCP Integration Documentation

## Model Context Protocol (MCP) Server-Client Integration

The DocuMateAgent now includes Model Context Protocol (MCP) server-client functionality for Azure DevOps and GitHub integration, providing LLMs with structured access to repository analysis tools.

### Overview

MCP provides a standardized way for Large Language Models to interact with external systems through tools and resources. Our implementation includes:

- **MCP Server Base Classes**: Standardized protocol implementation
- **Azure DevOps MCP Client**: Complete Azure DevOps API integration
- **GitHub MCP Client**: Comprehensive GitHub API integration  
- **LLM Integration**: Seamless integration with existing LLM code analyzer

### Architecture

```
src/llm_code_analyzer/
├── __init__.py                 # Package exports
├── llm_code_analyzer.py       # Enhanced LLM analyzer with MCP
└── mcp/
    ├── __init__.py            # MCP package exports
    ├── server.py              # Base MCP server implementation
    ├── client.py              # Base MCP client implementation
    ├── azure_devops_client.py # Azure DevOps API integration
    └── github_client.py       # GitHub API integration
```

### Features

#### Azure DevOps MCP Tools
- `list_repositories`: List repositories in organization/project
- `get_repository_info`: Get detailed repository information
- `get_repository_contents`: Get repository file structure
- `get_file_content`: Retrieve specific file contents
- `get_commits`: Get commit history
- `get_pull_requests`: Get pull request information

#### GitHub MCP Tools  
- `get_repository_info`: Get repository information
- `get_repository_contents`: Get repository structure
- `get_file_content`: Retrieve file contents
- `get_commits`: Get commit history
- `get_pull_requests`: Get pull requests
- `get_branches`: Get repository branches
- `get_languages`: Get programming languages used
- `search_code`: Search for code within repositories

### Configuration

#### Environment Variables

```bash
# Azure DevOps (optional)
export AZURE_DEVOPS_ORGANIZATION="your-org"
export AZURE_DEVOPS_PAT="your-personal-access-token"

# GitHub (optional)  
export GITHUB_TOKEN="your-github-token"

# OpenAI (optional, for LLM analysis)
export OPENAI_API_KEY="your-openai-key"
```

#### Programmatic Configuration

```python
from src.llm_code_analyzer import LLMCodeAnalyzer

# Initialize with MCP support
analyzer = LLMCodeAnalyzer(
    enable_mcp=True,                    # Enable MCP integration
    azure_devops_org="your-org",       # Azure DevOps organization
    azure_devops_pat="your-pat",       # Azure DevOps PAT
    github_token="your-github-token",  # GitHub token
    llm_api_key="your-openai-key"      # OpenAI API key (optional)
)
```

### Usage Examples

#### Repository Analysis

```python
import asyncio
from src.llm_code_analyzer import LLMCodeAnalyzer

async def analyze_repositories():
    analyzer = LLMCodeAnalyzer(enable_mcp=True)
    
    # Analyze GitHub repository
    github_result = await analyzer.analyze_repository_with_mcp(
        repository_url="https://github.com/microsoft/vscode",
        repository_type="github"
    )
    
    # Analyze Azure DevOps repository
    azure_result = await analyzer.analyze_repository_with_mcp(
        repository_url="https://dev.azure.com/microsoft/vscode/_git/vscode",
        repository_type="azure_devops"
    )
    
    # Get repository files for analysis
    files = await analyzer.get_mcp_repository_files(
        repository_url="https://github.com/user/repo",
        repository_type="github",
        max_files=50
    )
    
    # Cleanup
    await analyzer.close_mcp_clients()

# Run the analysis
asyncio.run(analyze_repositories())
```

#### Direct MCP Tool Usage

```python
from src.llm_code_analyzer.mcp.github_client import GitHubMCPClient
from src.llm_code_analyzer.mcp.azure_devops_client import AzureDevOpsClient

async def use_mcp_tools():
    # GitHub MCP client
    github_client = GitHubMCPClient(github_token="your-token")
    
    # Get repository information
    repo_info = await github_client._get_repository_info("owner", "repo")
    
    # Get repository languages
    languages = await github_client._get_languages("owner", "repo")
    
    # Azure DevOps MCP client
    azure_client = AzureDevOpsClient(
        organization="your-org",
        personal_access_token="your-pat"
    )
    
    # List repositories
    repos = await azure_client._list_repositories(project="your-project")
    
    # Cleanup
    await github_client.close()
    await azure_client.close()
```

### MCP Protocol Compliance

Our implementation follows the Model Context Protocol specification:

- **Tools**: Callable functions with JSON schema parameters
- **Resources**: Named data sources with URIs
- **Requests/Responses**: Standardized JSON-RPC message format
- **Error Handling**: Proper error codes and messages
- **Async Support**: Full asynchronous operation support

### Security Considerations

- **Credential Storage**: Use environment variables or secure vaults
- **Token Permissions**: Use minimal required permissions
- **Network Security**: All API calls use HTTPS
- **Error Handling**: Sensitive information not exposed in errors

### Troubleshooting

#### Common Issues

1. **MCP Not Enabled**
   ```python
   # Check MCP status
   if analyzer.mcp_enabled:
       print("MCP is enabled")
   else:
       print("MCP disabled - check credentials")
   ```

2. **Authentication Errors**
   ```bash
   # Verify credentials
   echo $GITHUB_TOKEN
   echo $AZURE_DEVOPS_PAT
   ```

3. **Network Issues**
   - Verify network connectivity to APIs
   - Check firewall and proxy settings
   - Ensure API endpoints are accessible

#### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable debug logging for detailed information
analyzer = LLMCodeAnalyzer(enable_mcp=True)
```

### Testing

Run the MCP tests to verify functionality:

```bash
# Run all MCP tests
python -m pytest tests/test_mcp_basic.py tests/test_llm_code_analyzer_mcp.py -v

# Run the demo
python examples/mcp_demo.py
```

### Contributing

When contributing to MCP functionality:

1. Follow the existing MCP protocol patterns
2. Add comprehensive tests for new tools
3. Update documentation for new features
4. Ensure backward compatibility
5. Handle errors gracefully

### Future Enhancements

Planned improvements include:

- **Resource Caching**: Cache frequently accessed repository data
- **Batch Operations**: Process multiple repositories efficiently
- **Additional Providers**: Support for GitLab, Bitbucket, etc.
- **Advanced Tools**: Code search, dependency analysis, security scanning
- **Performance Optimization**: Concurrent request handling, connection pooling