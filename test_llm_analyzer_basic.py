#!/usr/bin/env python3
"""
Simple test script for LLM Code Analyzer MCP functionality

This is a simplified test to verify that the MCP client can connect to Azure DevOps
and the basic flow is working, with fallback mocks for testing.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.llm_code_analyzer.llm_code_analyzer import LLMCodeAnalyzer


async def test_basic_mcp_connection():
    """Test basic MCP connection and initialization"""
    print("🔧 Testing LLM Code Analyzer initialization...")
    
    # Test with environment variables or fallback values
    analyzer = LLMCodeAnalyzer(
        enable_mcp=True,
        azure_devops_org=os.getenv('AZURE_DEVOPS_ORGANIZATION', 'test-org'),
        azure_devops_pat=os.getenv('AZURE_DEVOPS_PAT', 'test-pat'),
        api_key=os.getenv('OPENAI_API_KEY', 'test-key'),
        model="gpt-4"
    )
    
    print(f"✅ Analyzer initialized")
    print(f"   MCP Enabled: {analyzer.mcp_enabled}")
    print(f"   Azure DevOps Client: {analyzer.azure_devops_client is not None}")
    print(f"   LLM Client: {analyzer.client is not None}")
    
    return analyzer


async def test_repository_analysis_mock():
    """Test repository analysis with mocked responses"""
    print("\n📋 Testing repository analysis (mocked)...")
    
    analyzer = await test_basic_mcp_connection()
    
    if not analyzer.azure_devops_client:
        print("❌ Azure DevOps client not available")
        return
    
    # Mock repository data
    mock_repo_info = {
        "id": "test-repo-id",
        "name": "demo-repository",
        "project": {"name": "demo-project", "id": "project-id"},
        "size": 1024000,
        "defaultBranch": "refs/heads/main"
    }
    
    mock_contents = {
        "value": [
            {"path": "/main.py", "isFolder": False, "size": 500},
            {"path": "/src/api.py", "isFolder": False, "size": 800},
            {"path": "/src", "isFolder": True}
        ]
    }
    
    mock_commits = {
        "value": [
            {
                "commitId": "abc123",
                "comment": "Initial commit",
                "author": {"name": "Test Author", "email": "test@example.com"}
            }
        ]
    }
    
    # Patch the ADO client methods
    with patch.object(analyzer.azure_devops_client, '_get_repository_info') as mock_repo:
        mock_repo.return_value = mock_repo_info
        
        with patch.object(analyzer.azure_devops_client, '_get_repository_contents') as mock_contents_call:
            mock_contents_call.return_value = mock_contents
            
            with patch.object(analyzer.azure_devops_client, '_get_commits') as mock_commits_call:
                mock_commits_call.return_value = mock_commits
                
                with patch.object(analyzer.azure_devops_client, '_get_pull_requests') as mock_prs:
                    mock_prs.return_value = {"value": []}
                    
                    # Test repository analysis
                    test_repo_url = "https://dev.azure.com/test-org/test-project/_git/test-repo"
                    
                    result = await analyzer.analyze_repository_with_mcp(
                        test_repo_url,
                        "azure_devops"
                    )
                    
                    print(f"✅ Repository analysis completed")
                    print(f"   Repository: {result['repository_info']['name']}")
                    print(f"   Project: {result['repository_info']['project']['name']}")
                    print(f"   Contents: {len(result['contents']['value'])} items")
                    print(f"   Commits: {len(result['recent_commits']['value'])} commits")
                    
                    return result


async def test_file_retrieval_mock():
    """Test file retrieval with mocked responses"""
    print("\n📄 Testing file retrieval (mocked)...")
    
    analyzer = await test_basic_mcp_connection()
    
    if not analyzer.azure_devops_client:
        print("❌ Azure DevOps client not available")
        return {}
    
    # Mock file contents
    sample_files = {
        "main.py": '''#!/usr/bin/env python3
"""Main application entry point"""
import asyncio
from src.api import create_app

async def main():
    app = create_app()
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())
''',
        "src/api.py": '''"""API module"""
from fastapi import FastAPI

def create_app():
    app = FastAPI(title="Demo API")
    return app
'''
    }
    
    # Mock file listing
    mock_contents = {
        "value": [
            {"path": "/main.py", "isFolder": False, "size": len(sample_files["main.py"])},
            {"path": "/src/api.py", "isFolder": False, "size": len(sample_files["src/api.py"])}
        ]
    }
    
    # Mock file content retrieval
    def mock_get_file_content(project, repo, path):
        file_key = path.lstrip('/')
        if file_key in sample_files:
            return {"content": sample_files[file_key]}
        else:
            raise Exception(f"File not found: {path}")
    
    with patch.object(analyzer.azure_devops_client, '_get_repository_contents') as mock_contents_call:
        mock_contents_call.return_value = mock_contents
        
        with patch.object(analyzer.azure_devops_client, '_get_file_content') as mock_file_content:
            mock_file_content.side_effect = mock_get_file_content
            
            # Test file retrieval
            test_repo_url = "https://dev.azure.com/test-org/test-project/_git/test-repo"
            
            files = await analyzer.get_mcp_repository_files(
                test_repo_url,
                "azure_devops",
                max_files=10
            )
            
            print(f"✅ File retrieval completed")
            print(f"   Files retrieved: {len(files)}")
            for file_path, content in files.items():
                print(f"   📝 {file_path}: {len(content)} characters")
            
            return files


async def test_analysis_methods():
    """Test specific analysis methods"""
    print("\n🔍 Testing analysis methods...")
    
    analyzer = await test_basic_mcp_connection()
    
    # Test file selection
    sample_files = {
        "main.py": "# Main file\nprint('hello')",
        "src/api.py": "# API file\nfrom fastapi import FastAPI",
        "tests/test_main.py": "# Test file\nimport unittest",
        "README.md": "# Documentation\nThis is a readme"
    }
    
    selected = analyzer._select_files_for_analysis(sample_files)
    print(f"📊 File selection test:")
    print(f"   Input files: {len(sample_files)}")
    print(f"   Selected files: {len(selected)}")
    for file_path in selected.keys():
        print(f"   ✅ {file_path}")
    
    # Test prompt creation
    print(f"\n📝 Prompt creation test:")
    if sample_files:
        file_path, content = list(sample_files.items())[0]
        prompt = analyzer._create_analysis_prompt(file_path, content, "Python")
        print(f"   File: {file_path}")
        print(f"   Prompt length: {len(prompt):,} characters")
        print(f"   Prompt preview: {prompt[:100]}...")


async def run_all_tests():
    """Run all tests"""
    print("🚀 Starting LLM Code Analyzer MCP Tests")
    print("=" * 60)
    
    try:
        # Test 1: Basic initialization
        await test_basic_mcp_connection()
        
        # Test 2: Repository analysis
        await test_repository_analysis_mock()
        
        # Test 3: File retrieval  
        await test_file_retrieval_mock()
        
        # Test 4: Analysis methods
        await test_analysis_methods()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("\nTo test with real data, set these environment variables:")
        print("  AZURE_DEVOPS_ORGANIZATION")
        print("  AZURE_DEVOPS_PAT")
        print("  OPENAI_API_KEY (or Azure OpenAI variables)")
        print("\nThen run:")
        print("  python demo_llm_code_analyzer_flow.py --repo-url <your_ado_repo_url>")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point"""
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Run tests
    asyncio.run(run_all_tests())


if __name__ == '__main__':
    main()
