#!/usr/bin/env python3
"""
Demo script to test ADO MCP analysis flow
This script demonstrates connecting to ADO via MCP and analyzing repository files
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from llm_code_analyzer.llm_code_analyzer import LLMCodeAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def demo_ado_mcp_flow():
    """
    Demo the complete ADO MCP analysis flow
    """
    print("🚀 Starting ADO MCP Analysis Flow Demo")
    print("=" * 50)
    
    try:
        # Step 1: Initialize LLM Code Analyzer
        print("\n📊 Step 1: Initializing LLM Code Analyzer...")
        analyzer = LLMCodeAnalyzer()
        print("✅ LLM Code Analyzer initialized successfully")
        
        # Step 2: Initialize MCP connection (assuming ADO is configured)
        print("\n🔌 Step 2: Initializing MCP connection...")
        # This will use the default MCP configuration
        await analyzer.initialize_mcp()
        print("✅ MCP connection established")
        
        # Step 3: Test repository listing
        print("\n📋 Step 3: Testing repository listing...")
        repos = await analyzer.list_repositories()
        print(f"✅ Found {len(repos)} repositories")
        
        if repos:
            print("Available repositories:")
            for i, repo in enumerate(repos[:5], 1):  # Show first 5 repos
                print(f"  {i}. {repo}")
            if len(repos) > 5:
                print(f"  ... and {len(repos) - 5} more repositories")
        else:
            print("⚠️  No repositories found")
            return
        
        # Step 4: Select a repository for analysis
        print("\n🎯 Step 4: Selecting repository for analysis...")
        # Use the first repository for demo
        selected_repo = repos[0]
        print(f"Selected repository: {selected_repo}")
        
        # Step 5: Get repository files
        print("\n📁 Step 5: Retrieving repository files...")
        files = await analyzer.get_repository_files(selected_repo)
        print(f"✅ Retrieved {len(files)} files from repository")
        
        if files:
            print("Repository files:")
            for i, file_path in enumerate(files[:10], 1):  # Show first 10 files
                print(f"  {i}. {file_path}")
            if len(files) > 10:
                print(f"  ... and {len(files) - 10} more files")
        else:
            print("⚠️  No files found in repository")
            return
        
        # Step 6: Analyze a specific file
        print("\n🔍 Step 6: Analyzing file content...")
        # Select a code file for analysis (prefer .py, .js, .cs, etc.)
        code_files = [f for f in files if any(f.endswith(ext) for ext in ['.py', '.js', '.ts', '.cs', '.java', '.cpp', '.c'])]
        
        if code_files:
            selected_file = code_files[0]
            print(f"Analyzing file: {selected_file}")
            
            # Get file content
            content = await analyzer.get_file_content(selected_repo, selected_file)
            if content:
                print(f"✅ Retrieved file content ({len(content)} characters)")
                
                # Analyze with LLM
                print("\n🤖 Step 7: Performing LLM analysis...")
                analysis = await analyzer.analyze_code_with_llm(content, selected_file)
                
                if analysis:
                    print("✅ LLM analysis completed successfully")
                    print("\n📝 Analysis Results:")
                    print("-" * 40)
                    # Print first 500 characters of analysis
                    preview = analysis[:500] + "..." if len(analysis) > 500 else analysis
                    print(preview)
                    print("-" * 40)
                else:
                    print("❌ LLM analysis failed")
            else:
                print("❌ Failed to retrieve file content")
        else:
            print("⚠️  No code files found for analysis")
        
        # Step 8: Test repository summary
        print("\n📊 Step 8: Generating repository summary...")
        summary = await analyzer.analyze_repository_with_mcp(selected_repo)
        
        if summary:
            print("✅ Repository summary generated successfully")
            print("\n📋 Repository Summary:")
            print("=" * 50)
            # Print first 1000 characters of summary
            summary_preview = summary[:1000] + "..." if len(summary) > 1000 else summary
            print(summary_preview)
            print("=" * 50)
        else:
            print("❌ Failed to generate repository summary")
        
        print("\n🎉 Demo completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        logger.exception("Demo failed")
        return False
    
    finally:
        # Cleanup
        try:
            await analyzer.cleanup()
            print("🧹 Cleanup completed")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
    
    return True

async def demo_with_specific_repo():
    """
    Demo with a specific repository (you can modify this)
    """
    print("\n🎯 Custom Repository Demo")
    print("=" * 30)
    
    # You can modify these values for your specific test case
    org_name = "your-org"  # Replace with actual org
    project_name = "your-project"  # Replace with actual project
    repo_name = "your-repo"  # Replace with actual repo
    
    try:
        analyzer = LLMCodeAnalyzer()
        await analyzer.initialize_mcp()
        
        repo_identifier = f"{org_name}/{project_name}/{repo_name}"
        print(f"Analyzing specific repository: {repo_identifier}")
        
        summary = await analyzer.analyze_repository_with_mcp(repo_identifier)
        
        if summary:
            print("✅ Analysis completed")
            print("\nSummary:")
            print(summary)
        else:
            print("❌ Analysis failed")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        try:
            await analyzer.cleanup()
        except:
            pass

def main():
    """
    Main function to run the demo
    """
    print("ADO MCP Analysis Flow Demo")
    print("Choose demo mode:")
    print("1. Full flow demo (discover repos and analyze)")
    print("2. Specific repository demo")
    print("3. Exit")
    
    try:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            success = asyncio.run(demo_ado_mcp_flow())
            if success:
                print("\n✅ All systems working correctly!")
            else:
                print("\n❌ Some issues detected. Check the logs above.")
                
        elif choice == "2":
            print("\n⚠️  Please modify the repository details in demo_with_specific_repo() function")
            asyncio.run(demo_with_specific_repo())
            
        elif choice == "3":
            print("👋 Goodbye!")
            
        else:
            print("❌ Invalid choice")
            
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
