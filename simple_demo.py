#!/usr/bin/env python3
"""
Simple ADO MCP Demo - Quick test of the analysis flow
Customize the configuration section below for your ADO setup
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION - Modify these values for your ADO setup
# =============================================================================

# ADO Configuration (set these to your actual values)
ADO_ORG = "your-organization"           # Your ADO organization name
ADO_PROJECT = "your-project"            # Your ADO project name  
ADO_REPO = "your-repository"            # Your ADO repository name

# File to analyze (optional - leave empty to auto-select)
TARGET_FILE = ""                        # e.g., "src/main.py" or leave empty

# =============================================================================

async def quick_demo():
    """
    Quick demo of ADO MCP analysis
    """
    print("🚀 Quick ADO MCP Demo")
    print("=" * 40)
    
    analyzer = None
    try:
        # Initialize
        print("📊 Initializing analyzer...")
        analyzer = LLMCodeAnalyzer()
        await analyzer.initialize_mcp()
        print("✅ Connected to MCP")
        
        # List repositories to verify connection
        print("\n📋 Testing repository access...")
        repos = await analyzer.list_repositories()
        print(f"✅ Found {len(repos)} repositories")
        
        # Use configured repo or first available
        if f"{ADO_ORG}/{ADO_PROJECT}/{ADO_REPO}" in repos:
            target_repo = f"{ADO_ORG}/{ADO_PROJECT}/{ADO_REPO}"
            print(f"🎯 Using configured repo: {target_repo}")
        elif repos:
            target_repo = repos[0]
            print(f"🎯 Using first available repo: {target_repo}")
        else:
            print("❌ No repositories found!")
            return
        
        # Get repository files
        print(f"\n📁 Getting files from {target_repo}...")
        files = await analyzer.get_repository_files(target_repo)
        print(f"✅ Found {len(files)} files")
        
        # Select file to analyze
        if TARGET_FILE and TARGET_FILE in files:
            selected_file = TARGET_FILE
        else:
            # Auto-select a code file
            code_files = [f for f in files if any(f.endswith(ext) for ext in 
                         ['.py', '.js', '.ts', '.cs', '.java', '.cpp', '.c', '.rb', '.go'])]
            selected_file = code_files[0] if code_files else files[0] if files else None
        
        if not selected_file:
            print("❌ No suitable file found for analysis")
            return
            
        print(f"🔍 Analyzing file: {selected_file}")
        
        # Get and analyze file content
        content = await analyzer.get_file_content(target_repo, selected_file)
        if content:
            print(f"✅ Retrieved file content ({len(content)} chars)")
            
            # Quick LLM analysis
            print("🤖 Running LLM analysis...")
            analysis = await analyzer.analyze_code_with_llm(content, selected_file)
            
            if analysis:
                print("✅ Analysis completed!")
                print("\n📝 Analysis Result:")
                print("-" * 50)
                print(analysis[:800] + "..." if len(analysis) > 800 else analysis)
                print("-" * 50)
            else:
                print("❌ LLM analysis failed")
        else:
            print("❌ Failed to get file content")
            
        print("\n🎉 Demo completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        logger.exception("Demo failed")
        
    finally:
        if analyzer:
            try:
                await analyzer.cleanup()
                print("🧹 Cleaned up")
            except:
                pass

def check_config():
    """
    Check if configuration looks valid
    """
    if ADO_ORG == "your-organization":
        print("⚠️  WARNING: Please update the configuration section in this file!")
        print("   Set ADO_ORG, ADO_PROJECT, and ADO_REPO to your actual values")
        print("   The demo will still run but may not find your specific repository")
        input("\nPress Enter to continue anyway...")

if __name__ == "__main__":
    print("Simple ADO MCP Analysis Demo")
    check_config()
    asyncio.run(quick_demo())
