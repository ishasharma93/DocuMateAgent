"""
Comprehensive tests for the Azure DevOps MCP client flow and file analysis
Tests the complete flow: ADO MCP connection -> file retrieval -> LLM analysis
"""

import unittest
import asyncio
import os
import json
import logging
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, List

from src.llm_code_analyzer.llm_code_analyzer import LLMCodeAnalyzer, CodeExplanation


class TestADOMCPAnalysisFlow(unittest.TestCase):
    """Test the complete ADO MCP client analysis flow"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock environment variables for testing
        self.test_org = "test-organization"
        self.test_pat = "test-personal-access-token"
        self.test_project = "test-project"
        self.test_repo = "test-repository"
        
        # Create analyzer with test credentials
        self.analyzer = LLMCodeAnalyzer(
            enable_mcp=True,
            azure_devops_org=self.test_org,
            azure_devops_pat=self.test_pat,
            api_key="test-api-key",  # Mock API key for LLM
            model="gpt-4"
        )
        
        # Sample repository URL
        self.test_repo_url = f"https://dev.azure.com/{self.test_org}/{self.test_project}/_git/{self.test_repo}"
        
        # Sample file contents for testing
        self.sample_files = {
            "main.py": '''#!/usr/bin/env python3
"""
Main application entry point
"""
import asyncio
import logging
from src.api import create_app
from src.database import initialize_db

logger = logging.getLogger(__name__)

async def main():
    """Initialize and run the application"""
    logger.info("Starting application...")
    
    # Initialize database
    await initialize_db()
    
    # Create and configure app
    app = create_app()
    
    # Start server
    await app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    asyncio.run(main())
''',
            "src/api.py": '''"""
API layer for the application
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .routes import user_router, data_router
from .auth import AuthMiddleware

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Test API",
        description="A test API application",
        version="1.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add authentication middleware
    app.add_middleware(AuthMiddleware)
    
    # Include routers
    app.include_router(user_router, prefix="/api/users")
    app.include_router(data_router, prefix="/api/data")
    
    return app
''',
            "src/database.py": '''"""
Database connection and initialization
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Create session factory
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def initialize_db():
    """Initialize database tables and connections"""
    try:
        # Test connection
        async with engine.begin() as conn:
            logger.info("Database connection established")
            
        # Create tables if needed
        # await create_tables()
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

async def get_db_session() -> AsyncSession:
    """Get database session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
''',
            "tests/test_api.py": '''"""
Tests for API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from src.api import create_app

@pytest.fixture
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)

def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200

def test_user_creation(client):
    """Test user creation endpoint"""
    user_data = {
        "name": "Test User",
        "email": "test@example.com"
    }
    response = client.post("/api/users", json=user_data)
    assert response.status_code == 201
    assert response.json()["name"] == "Test User"
''',
            "requirements.txt": '''fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
asyncpg==0.29.0
pytest==7.4.3
pytest-asyncio==0.21.1
''',
            "README.md": '''# Test Repository

This is a test repository for demonstrating the ADO MCP analysis flow.

## Features
- FastAPI web application
- Async database integration
- User management
- Data processing endpoints

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Configure database connection
3. Run: `python main.py`
'''
        }
    
    def test_analyzer_initialization_with_ado_mcp(self):
        """Test that the analyzer initializes correctly with ADO MCP enabled"""
        self.assertTrue(self.analyzer.mcp_enabled)
        self.assertIsNotNone(self.analyzer.azure_devops_client)
        
        # Verify ADO client is configured with correct organization
        self.assertEqual(self.analyzer.azure_devops_client.organization, self.test_org)
    
    def test_analyzer_initialization_without_credentials(self):
        """Test analyzer behavior when ADO credentials are missing"""
        with patch.dict(os.environ, {}, clear=True):
            analyzer = LLMCodeAnalyzer(enable_mcp=True)
            # Should still initialize but with warnings
            self.assertTrue(analyzer.mcp_enabled)
    
    async def test_ado_repository_analysis_success(self):
        """Test successful ADO repository analysis using MCP"""
        if not self.analyzer.mcp_enabled or not self.analyzer.azure_devops_client:
            self.skipTest("ADO MCP client not available")
        
        # Mock ADO API responses
        mock_repo_info = {
            "id": "test-repo-id",
            "name": self.test_repo,
            "project": {
                "name": self.test_project,
                "id": "test-project-id"
            },
            "size": 1024000,
            "defaultBranch": "refs/heads/main"
        }
        
        mock_contents = {
            "value": [
                {
                    "objectId": "file1-id",
                    "path": "/main.py",
                    "isFolder": False,
                    "size": 500
                },
                {
                    "objectId": "file2-id", 
                    "path": "/src/api.py",
                    "isFolder": False,
                    "size": 800
                },
                {
                    "objectId": "dir1-id",
                    "path": "/src",
                    "isFolder": True
                }
            ]
        }
        
        mock_commits = {
            "value": [
                {
                    "commitId": "commit1-id",
                    "comment": "Initial commit",
                    "author": {
                        "name": "Test Author",
                        "email": "test@example.com"
                    }
                }
            ]
        }
        
        mock_prs = {
            "value": [
                {
                    "pullRequestId": 123,
                    "title": "Test PR",
                    "status": "active"
                }
            ]
        }
        
        # Patch ADO client methods
        with patch.object(self.analyzer.azure_devops_client, '_get_repository_info') as mock_get_repo:
            mock_get_repo.return_value = mock_repo_info
            
            with patch.object(self.analyzer.azure_devops_client, '_get_repository_contents') as mock_get_contents:
                mock_get_contents.return_value = mock_contents
                
                with patch.object(self.analyzer.azure_devops_client, '_get_commits') as mock_get_commits:
                    mock_get_commits.return_value = mock_commits
                    
                    with patch.object(self.analyzer.azure_devops_client, '_get_pull_requests') as mock_get_prs:
                        mock_get_prs.return_value = mock_prs
                        
                        # Execute analysis
                        result = await self.analyzer.analyze_repository_with_mcp(
                            self.test_repo_url,
                            "azure_devops"
                        )
                        
                        # Verify results
                        self.assertIn("repository_info", result)
                        self.assertIn("contents", result)
                        self.assertIn("recent_commits", result)
                        self.assertIn("pull_requests", result)
                        
                        # Verify method calls
                        mock_get_repo.assert_called_once_with(self.test_project, self.test_repo)
                        mock_get_contents.assert_called_once_with(self.test_project, self.test_repo)
                        mock_get_commits.assert_called_once_with(self.test_project, self.test_repo, top=5)
                        mock_get_prs.assert_called_once_with(self.test_project, self.test_repo)
    
    async def test_ado_file_retrieval(self):
        """Test retrieving file contents from ADO repository"""
        if not self.analyzer.mcp_enabled or not self.analyzer.azure_devops_client:
            self.skipTest("ADO MCP client not available")
        
        # Mock file listing response
        mock_contents = {
            "value": [
                {
                    "path": "/main.py",
                    "isFolder": False,
                    "size": len(self.sample_files["main.py"])
                },
                {
                    "path": "/src/api.py", 
                    "isFolder": False,
                    "size": len(self.sample_files["src/api.py"])
                },
                {
                    "path": "/src/database.py",
                    "isFolder": False,
                    "size": len(self.sample_files["src/database.py"])
                }
            ]
        }
        
        # Mock file content responses
        def mock_get_file_content(project, repo, path):
            file_key = path.lstrip('/')
            if file_key in self.sample_files:
                return {"content": self.sample_files[file_key]}
            else:
                raise Exception(f"File not found: {path}")
        
        with patch.object(self.analyzer.azure_devops_client, '_get_repository_contents') as mock_get_contents:
            mock_get_contents.return_value = mock_contents
            
            with patch.object(self.analyzer.azure_devops_client, '_get_file_content') as mock_get_file:
                mock_get_file.side_effect = mock_get_file_content
                
                # Retrieve files
                files = await self.analyzer.get_mcp_repository_files(
                    self.test_repo_url,
                    "azure_devops",
                    max_files=10
                )
                
                # Verify file retrieval
                self.assertIn("main.py", files)
                self.assertIn("src/api.py", files)
                self.assertIn("src/database.py", files)
                
                # Verify content
                self.assertEqual(files["main.py"], self.sample_files["main.py"])
                self.assertEqual(files["src/api.py"], self.sample_files["src/api.py"])
    
    async def test_complete_analysis_flow(self):
        """Test the complete flow: ADO connection -> file retrieval -> LLM analysis"""
        if not self.analyzer.mcp_enabled or not self.analyzer.azure_devops_client:
            self.skipTest("ADO MCP client not available")
        
        # Mock file retrieval
        with patch.object(self.analyzer, 'get_mcp_repository_files') as mock_get_files:
            mock_get_files.return_value = self.sample_files
            
            # Mock LLM API responses
            mock_llm_responses = {
                "main.py": {
                    "summary": "Main application entry point that initializes database and starts FastAPI server",
                    "main_functionality": "Serves as the application bootstrap, setting up async database connections and starting the web server on port 8000",
                    "key_components": [
                        "main() function - application entry point",
                        "Database initialization call",
                        "FastAPI app creation and configuration",
                        "Server startup with host/port configuration"
                    ],
                    "dependencies": [
                        "asyncio - for async execution",
                        "logging - for application logging", 
                        "src.api - custom API module",
                        "src.database - custom database module"
                    ],
                    "complexity_assessment": "Simple - straightforward bootstrap pattern with clear separation of concerns",
                    "improvement_suggestions": [
                        "Add environment variable configuration for host/port",
                        "Add graceful shutdown handling",
                        "Include error handling for database initialization failures"
                    ],
                    "code_patterns": [
                        "Application Factory Pattern",
                        "Async/Await Pattern",
                        "Bootstrap Pattern"
                    ]
                },
                "src/api.py": {
                    "summary": "FastAPI application factory that creates and configures the web API with middleware and routing",
                    "main_functionality": "Creates FastAPI instance, adds CORS and authentication middleware, includes user and data routers",
                    "key_components": [
                        "create_app() factory function",
                        "CORS middleware configuration",
                        "Authentication middleware setup",
                        "Router inclusion for users and data endpoints"
                    ],
                    "dependencies": [
                        "fastapi - web framework",
                        "fastapi.middleware.cors - CORS support",
                        ".routes - custom route modules",
                        ".auth - custom authentication module"
                    ],
                    "complexity_assessment": "Moderate - well-structured API factory with proper middleware configuration",
                    "improvement_suggestions": [
                        "Add API versioning strategy",
                        "Include request/response validation",
                        "Add API documentation configuration"
                    ],
                    "code_patterns": [
                        "Factory Pattern",
                        "Middleware Pattern",
                        "Router Pattern"
                    ]
                }
            }
            
            # Mock LLM client calls
            async def mock_llm_call(prompt):
                # Extract file path from prompt for targeted response
                for file_path, response_data in mock_llm_responses.items():
                    if file_path in prompt:
                        return json.dumps(response_data)
                # Default response for unknown files
                return json.dumps({
                    "summary": "Code analysis completed",
                    "main_functionality": "General purpose code file",
                    "key_components": [],
                    "dependencies": [],
                    "complexity_assessment": "Unknown",
                    "improvement_suggestions": [],
                    "code_patterns": []
                })
            
            with patch.object(self.analyzer, '_call_llm_api') as mock_llm:
                mock_llm.side_effect = mock_llm_call
                
                # Execute complete analysis flow
                
                # Step 1: Get files from ADO
                files = await self.analyzer.get_mcp_repository_files(
                    self.test_repo_url,
                    "azure_devops",
                    max_files=10
                )
                
                # Step 2: Analyze files with LLM
                explanations = await self.analyzer.analyze_codebase(files)
                
                # Verify results
                self.assertGreater(len(explanations), 0)
                
                # Check specific file analysis
                if "main.py" in explanations:
                    main_explanation = explanations["main.py"]
                    self.assertIsInstance(main_explanation, CodeExplanation)
                    self.assertEqual(main_explanation.file_path, "main.py")
                    self.assertEqual(main_explanation.language, "Python")
                    self.assertIn("entry point", main_explanation.summary.lower())
                
                if "src/api.py" in explanations:
                    api_explanation = explanations["src/api.py"]
                    self.assertIsInstance(api_explanation, CodeExplanation)
                    self.assertIn("fastapi", api_explanation.summary.lower())
    
    async def test_error_handling_invalid_ado_url(self):
        """Test error handling for invalid ADO repository URLs"""
        if not self.analyzer.mcp_enabled:
            self.skipTest("MCP not available")
        
        # Test with invalid URL
        invalid_url = "https://invalid-ado-url.com/project/_git/repo"
        
        result = await self.analyzer.analyze_repository_with_mcp(
            invalid_url,
            "azure_devops"
        )
        
        self.assertIn("error", result)
        self.assertIn("Invalid Azure DevOps repository URL", result["error"])
    
    async def test_error_handling_ado_api_failure(self):
        """Test error handling when ADO API calls fail"""
        if not self.analyzer.mcp_enabled or not self.analyzer.azure_devops_client:
            self.skipTest("ADO MCP client not available")
        
        # Mock API failure
        with patch.object(self.analyzer.azure_devops_client, '_get_repository_info') as mock_get_repo:
            mock_get_repo.side_effect = Exception("ADO API Error: Repository not found")
            
            result = await self.analyzer.analyze_repository_with_mcp(
                self.test_repo_url,
                "azure_devops"
            )
            
            self.assertIn("error", result)
            self.assertIn("ADO API Error", result["error"])
    
    async def test_llm_analysis_with_focus_files(self):
        """Test LLM analysis with focus on specific files"""
        if not self.analyzer.client:
            self.skipTest("LLM client not available")
        
        # Mock LLM response
        with patch.object(self.analyzer, '_call_llm_api') as mock_llm:
            mock_llm.return_value = json.dumps({
                "summary": "Focused file analysis",
                "main_functionality": "Test functionality",
                "key_components": ["Component 1"],
                "dependencies": ["Dependency 1"],
                "complexity_assessment": "Simple",
                "improvement_suggestions": ["Suggestion 1"],
                "code_patterns": ["Pattern 1"]
            })
            
            # Analyze with focus files
            focus_files = ["main.py", "src/api.py"]
            explanations = await self.analyzer.analyze_codebase(
                self.sample_files,
                focus_files=focus_files
            )
            
            # Verify focus files were prioritized
            self.assertIn("main.py", explanations)
            self.assertIn("src/api.py", explanations)
    
    def test_code_insights_generation(self):
        """Test generation of code insights from explanations"""
        # Create sample explanations
        explanations = {
            "main.py": CodeExplanation(
                file_path="main.py",
                language="Python",
                summary="Application entry point",
                main_functionality="Bootstrap application",
                key_components=["main function", "database init"],
                dependencies=["asyncio", "fastapi"],
                complexity_assessment="Simple application structure",
                improvement_suggestions=["Add error handling", "Add configuration"],
                code_patterns=["Factory Pattern", "Bootstrap Pattern"]
            ),
            "src/api.py": CodeExplanation(
                file_path="src/api.py",
                language="Python", 
                summary="API factory",
                main_functionality="Create FastAPI app",
                key_components=["create_app function", "middleware setup"],
                dependencies=["fastapi", "cors"],
                complexity_assessment="Moderate API structure",
                improvement_suggestions=["Add validation", "Add documentation"],
                code_patterns=["Factory Pattern", "Middleware Pattern"]
            )
        }
        
        # Generate insights
        insights = self.analyzer.generate_code_insights_summary(explanations)
        
        # Verify insights structure
        self.assertEqual(insights["total_files_analyzed"], 2)
        self.assertIn("Simple", insights["complexity_distribution"])
        self.assertIn("Moderate", insights["complexity_distribution"])
        self.assertIn("Factory Pattern", insights["common_patterns"])
        self.assertIn("fastapi", insights["key_technologies"])
    
    async def test_mcp_client_cleanup(self):
        """Test proper cleanup of MCP clients"""
        if not self.analyzer.mcp_enabled or not self.analyzer.azure_devops_client:
            self.skipTest("ADO MCP client not available")
        
        # Mock close methods
        with patch.object(self.analyzer.azure_devops_client, 'close') as mock_close:
            await self.analyzer.close_mcp_clients()
            mock_close.assert_called_once()
    
    def test_file_selection_priority(self):
        """Test file selection logic prioritizes important files"""
        # Test with focus files
        selected = self.analyzer._select_files_for_analysis(
            self.sample_files, 
            focus_files=["main.py"]
        )
        
        # Focus files should be included
        self.assertIn("main.py", selected)
        
        # Test without focus files - should select based on importance
        selected_no_focus = self.analyzer._select_files_for_analysis(
            self.sample_files,
            focus_files=None
        )
        
        # Important files like main.py should be selected
        self.assertIn("main.py", selected_no_focus)


# Helper functions for running async tests
def run_async_test(coro):
    """Helper function to run async tests"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(coro)
    finally:
        # Don't close the loop if it's the main event loop
        if not loop.is_running():
            loop.close()


# Convert async test methods to sync for unittest compatibility
for method_name in dir(TestADOMCPAnalysisFlow):
    if method_name.startswith('test_') and asyncio.iscoroutinefunction(getattr(TestADOMCPAnalysisFlow, method_name)):
        method = getattr(TestADOMCPAnalysisFlow, method_name)
        setattr(TestADOMCPAnalysisFlow, method_name, lambda self, m=method: run_async_test(m(self)))


if __name__ == '__main__':
    # Configure logging for tests
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    unittest.main(verbosity=2)
