"""
Example demonstrating Azure DevOps and GitHub MCP integration with LLM Code Analyzer
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from src
sys.path.append(str(Path(__file__).parent.parent))

from src.llm_code_analyzer import LLMCodeAnalyzer


async def demo_mcp_integration():
    """Demonstrate MCP integration with Azure DevOps and GitHub"""
    
    print("🤖 LLM Code Analyzer with MCP Integration Demo")
    print("=" * 50)
    
    # Initialize LLM Code Analyzer with MCP support
    analyzer = LLMCodeAnalyzer(
        enable_mcp=True,
        # Note: In real usage, provide actual credentials
        azure_devops_org="your-org",  # Set AZURE_DEVOPS_ORGANIZATION env var
        azure_devops_pat="your-pat",  # Set AZURE_DEVOPS_PAT env var
        github_token="your-token"     # Set GITHUB_TOKEN env var
    )
    
    print(f"✅ MCP Integration Status: {'Enabled' if analyzer.mcp_enabled else 'Disabled'}")
    
    if analyzer.azure_devops_client:
        print("✅ Azure DevOps MCP Client: Initialized")
        # List available tools
        tools = analyzer.azure_devops_client.tools
        print(f"   Available Azure DevOps Tools: {', '.join(tools.keys())}")
    else:
        print("❌ Azure DevOps MCP Client: Not available (missing credentials)")
    
    if analyzer.github_mcp_client:
        print("✅ GitHub MCP Client: Initialized") 
        # List available tools
        tools = analyzer.github_mcp_client.tools
        print(f"   Available GitHub Tools: {', '.join(tools.keys())}")
    else:
        print("❌ GitHub MCP Client: Not available (missing credentials)")
    
    print("\n📊 Example Repository Analysis (Mock)")
    print("-" * 40)
    
    # Example 1: GitHub Repository Analysis
    print("\n🔍 GitHub Repository Analysis Example:")
    github_url = "https://github.com/microsoft/vscode"
    
    try:
        # This would work with real credentials
        result = await analyzer.analyze_repository_with_mcp(github_url, "github")
        if "error" in result:
            print(f"   Status: {result['error']}")
        else:
            print(f"   ✅ Analysis completed for {github_url}")
            print(f"   Repository Info: {result.get('repository_info', {}).get('name', 'N/A')}")
            print(f"   Languages: {list(result.get('languages', {}).keys())[:3]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Example 2: Azure DevOps Repository Analysis
    print("\n🔍 Azure DevOps Repository Analysis Example:")
    azure_url = "https://dev.azure.com/microsoft/vscode/_git/vscode"
    
    try:
        # This would work with real credentials
        result = await analyzer.analyze_repository_with_mcp(azure_url, "azure_devops")
        if "error" in result:
            print(f"   Status: {result['error']}")
        else:
            print(f"   ✅ Analysis completed for {azure_url}")
            print(f"   Repository Info: {result.get('repository_info', {}).get('name', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Example 3: File Content Retrieval
    print("\n📄 File Content Retrieval Example:")
    try:
        files = await analyzer.get_mcp_repository_files(
            github_url, 
            "github", 
            max_files=5
        )
        if files:
            print(f"   ✅ Retrieved {len(files)} files")
            for file_path in list(files.keys())[:3]:
                print(f"   - {file_path} ({len(files[file_path])} chars)")
        else:
            print("   ❌ No files retrieved (credentials required)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n🛠️  MCP Server Tools Available:")
    print("-" * 40)
    
    if analyzer.azure_devops_client:
        print("\nAzure DevOps Tools:")
        for tool_name, tool_info in analyzer.azure_devops_client.tools.items():
            print(f"  • {tool_name}: {tool_info['description']}")
    
    if analyzer.github_mcp_client:
        print("\nGitHub Tools:")
        for tool_name, tool_info in analyzer.github_mcp_client.tools.items():
            print(f"  • {tool_name}: {tool_info['description']}")
    
    # Cleanup
    await analyzer.close_mcp_clients()
    print("\n✅ MCP clients closed")
    
    print("\n" + "=" * 50)
    print("Demo completed! To use with real repositories:")
    print("1. Set AZURE_DEVOPS_ORGANIZATION and AZURE_DEVOPS_PAT environment variables")
    print("2. Set GITHUB_TOKEN environment variable") 
    print("3. Provide valid repository URLs")
    print("4. Optionally set OPENAI_API_KEY for LLM-powered analysis")


async def demo_mcp_tools_directly():
    """Demonstrate direct MCP tool usage"""
    print("\n🔧 Direct MCP Tool Usage Demo")
    print("=" * 40)
    
    # Create MCP clients directly
    from src.llm_code_analyzer.mcp.azure_devops_client import AzureDevOpsClient
    from src.llm_code_analyzer.mcp.github_client import GitHubMCPClient
    from src.llm_code_analyzer.mcp.server import MCPRequest
    
    # Azure DevOps MCP Server
    azure_server = AzureDevOpsClient(
        organization="demo-org",
        personal_access_token="demo-pat"
    )
    
    print("🔹 Azure DevOps MCP Server:")
    
    # List tools
    tools_request = MCPRequest(method="tools/list", params={})
    tools_response = await azure_server.handle_request(tools_request)
    
    if not tools_response.error:
        tools = tools_response.result["tools"]
        print(f"   Available tools: {len(tools)}")
        for tool in tools[:3]:  # Show first 3 tools
            print(f"   - {tool['name']}: {tool['description']}")
    
    # GitHub MCP Server
    github_server = GitHubMCPClient(github_token="demo-token")
    
    print("\n🔹 GitHub MCP Server:")
    
    # List tools
    tools_response = await github_server.handle_request(tools_request)
    
    if not tools_response.error:
        tools = tools_response.result["tools"]
        print(f"   Available tools: {len(tools)}")
        for tool in tools[:3]:  # Show first 3 tools
            print(f"   - {tool['name']}: {tool['description']}")
    
    # Cleanup
    await azure_server.close()
    await github_server.close()


def main():
    """Main demo function"""
    print("Starting MCP Integration Demo...")
    
    # Run the demos
    asyncio.run(demo_mcp_integration())
    asyncio.run(demo_mcp_tools_directly())


if __name__ == "__main__":
    main()