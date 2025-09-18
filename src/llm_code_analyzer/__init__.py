"""
LLM Code Analyzer package with MCP server-client support for Azure DevOps and GitHub
"""

from .llm_code_analyzer import LLMCodeAnalyzer, CodeExplanation, analyze_codebase_sync

__all__ = ['LLMCodeAnalyzer', 'CodeExplanation', 'analyze_codebase_sync']