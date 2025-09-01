"""
GitHub Repository Summarization Agent

Main class that orchestrates the analysis and summarization of GitHub repositories.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_int_from_env(env_var: str, default: int) -> int:
    """Get integer value from environment variable, handling comments"""
    value_str = os.getenv(env_var, str(default)).split('#')[0].strip()
    return int(value_str)

from .github_client import GitHubClient
from .code_analyzer import CodeAnalyzer
from .markdown_generator import MarkdownGenerator
from .llm_code_analyzer import LLMCodeAnalyzer, analyze_codebase_sync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GitHubRepoSummarizer:
    """
    Main class for analyzing GitHub repositories and generating markdown summaries
    """
    
    def __init__(self, github_token: Optional[str] = None, 
                 max_file_size: int = 1024*1024,
                 llm_api_key: Optional[str] = None,
                 llm_model: str = "gpt-4",
                 enable_llm_analysis: bool = True,
                 use_azure: bool = None,
                 azure_endpoint: Optional[str] = None,
                 azure_deployment: Optional[str] = None):
        """
        Initialize the repository summarizer
        
        Args:
            github_token: GitHub personal access token for API access
            max_file_size: Maximum file size to analyze in bytes (default: 1MB)
            llm_api_key: OpenAI or Azure OpenAI API key for code analysis
            llm_model: LLM model to use (gpt-4, gpt-3.5-turbo, etc.)
            enable_llm_analysis: Whether to perform LLM-powered code analysis
            use_azure: Whether to use Azure OpenAI (auto-detected if None)
            azure_endpoint: Azure OpenAI endpoint URL
            azure_deployment: Azure OpenAI deployment name
        """
        self.github_client = GitHubClient(github_token)
        self.code_analyzer = CodeAnalyzer()
        self.markdown_generator = MarkdownGenerator()
        self.max_file_size = max_file_size
        
        # Set Azure environment variables if provided via parameters
        if azure_endpoint:
            os.environ['AZURE_OPENAI_ENDPOINT'] = azure_endpoint
        if azure_deployment:
            os.environ['AZURE_OPENAI_DEPLOYMENT_NAME'] = azure_deployment
        if llm_api_key and use_azure:
            os.environ['AZURE_OPENAI_API_KEY'] = llm_api_key
        
        # LLM Analysis setup
        self.enable_llm_analysis = enable_llm_analysis
        if enable_llm_analysis:
            self.llm_analyzer = LLMCodeAnalyzer(
                api_key=llm_api_key,
                model=llm_model,
                use_azure=use_azure
            )
        else:
            self.llm_analyzer = None
        
        # Configuration
        self.max_files_to_analyze = get_int_from_env('MAX_FILES_TO_ANALYZE', 500)
        self.excluded_dirs = {
            '.git', 'node_modules', '__pycache__', '.pytest_cache', 
            'venv', 'env', '.env', 'dist', 'build', 'target',
            '.next', '.nuxt', 'coverage', '.coverage', 'htmlcov'
        }
        self.excluded_extensions = {
            '.pyc', '.pyo', '.pyd', '.class', '.o', '.so', '.dll',
            '.exe', '.bin', '.jar', '.war', '.ear', '.zip', '.tar',
            '.gz', '.rar', '.7z', '.pdf', '.doc', '.docx', '.xls',
            '.xlsx', '.ppt', '.pptx', '.jpg', '.jpeg', '.png', '.gif',
            '.bmp', '.svg', '.ico', '.mp3', '.mp4', '.avi', '.mov',
            '.wmv', '.flv', '.webm', '.ogg', '.wav', '.flac'
        }
    
    def analyze_repository(self, repo_url: str, 
                          include_file_contents: bool = True,
                          quick_analysis: bool = False) -> Dict[str, Any]:
        """
        Analyze a GitHub repository and return comprehensive analysis data
        
        Args:
            repo_url: GitHub repository URL or owner/repo format
            include_file_contents: Whether to download and analyze file contents
            quick_analysis: If True, perform faster analysis with limited scope
            
        Returns:
            Dictionary containing all analysis results
            
        Raises:
            Exception: If repository cannot be accessed or analyzed
        """
        logger.info(f"Starting analysis of repository: {repo_url}")
        
        try:
            # Get repository object
            repo = self.github_client.get_repository(repo_url)
            logger.info(f"Successfully connected to repository: {repo.full_name}")
            
            # Get basic repository information
            repo_info = self.github_client.get_repository_info(repo)
            logger.info("Retrieved repository metadata")
            
            # Get repository contents
            logger.info("Fetching repository contents...")
            contents = self.github_client.get_repository_contents(repo)
            logger.info(f"Found {len(contents)} files and directories")
            
            # Filter contents
            filtered_contents = self._filter_contents(contents)
            logger.info(f"Analyzing {len(filtered_contents)} relevant files")
            
            # Analyze repository structure
            logger.info("Analyzing repository structure...")
            structure_analysis = self.code_analyzer.analyze_repository_structure(filtered_contents)
            
            # Initialize analysis results
            analysis_results = {
                'repository_info': repo_info,
                'structure_analysis': structure_analysis,
                'file_contents': {},
                'dependency_analysis': {},
                'code_metrics': {},
                'pattern_analysis': {},
                'llm_analysis': {},
                'code_insights': {},
                'analysis_metadata': {
                    'quick_analysis': quick_analysis,
                    'files_analyzed': len(filtered_contents),
                    'total_files_found': len(contents),
                    'include_file_contents': include_file_contents,
                    'llm_analysis_enabled': self.enable_llm_analysis and include_file_contents
                }
            }
            
            # If quick analysis, return basic results
            if quick_analysis:
                logger.info("Quick analysis completed")
                return analysis_results
            
            # Get file contents for detailed analysis
            if include_file_contents:
                logger.info("Downloading file contents for analysis...")
                file_contents = self._get_file_contents(repo, filtered_contents)
                analysis_results['file_contents'] = file_contents
                logger.info(f"Downloaded {len(file_contents)} files")
                
                # Analyze dependencies
                logger.info("Analyzing dependencies...")
                dependency_analysis = self.code_analyzer.analyze_dependencies(file_contents)
                analysis_results['dependency_analysis'] = dependency_analysis
                
                # Analyze code metrics
                logger.info("Analyzing code metrics...")
                code_metrics = self.code_analyzer.analyze_code_metrics(file_contents)
                analysis_results['code_metrics'] = code_metrics
                
                # Detect patterns and architecture
                logger.info("Detecting patterns and architecture...")
                file_paths = [item['path'] for item in filtered_contents]
                pattern_analysis = self.code_analyzer.detect_project_patterns(file_paths, file_contents)
                analysis_results['pattern_analysis'] = pattern_analysis
                
                # LLM-powered code analysis
                if self.enable_llm_analysis and self.llm_analyzer:
                    logger.info("Starting LLM-powered code analysis...")
                    try:
                        # Identify key files for LLM analysis
                        key_files = self._identify_key_files(filtered_contents, file_contents)
                        
                        # Perform LLM analysis
                        llm_explanations = analyze_codebase_sync(
                            self.llm_analyzer, 
                            file_contents, 
                            focus_files=key_files
                        )
                        analysis_results['llm_analysis'] = llm_explanations
                        
                        # Generate code insights
                        if llm_explanations:
                            code_insights = self.llm_analyzer.generate_code_insights_summary(llm_explanations)
                            analysis_results['code_insights'] = code_insights
                            logger.info(f"LLM analysis completed for {len(llm_explanations)} files")
                        
                    except Exception as e:
                        logger.warning(f"LLM analysis failed: {e}")
                        analysis_results['llm_analysis'] = {}
                        analysis_results['code_insights'] = {}
                else:
                    logger.info("LLM analysis disabled or not configured")
                    analysis_results['llm_analysis'] = {}
                    analysis_results['code_insights'] = {}
            
            logger.info("Repository analysis completed successfully")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error analyzing repository: {e}")
            raise
    
    def generate_markdown_summary(self, analysis_results: Dict[str, Any], 
                                 output_type: str = 'full') -> str:
        """
        Generate a markdown summary from analysis results
        
        Args:
            analysis_results: Results from analyze_repository()
            output_type: Type of summary ('full', 'quick', 'custom')
            
        Returns:
            Markdown summary document
        """
        logger.info(f"Generating {output_type} markdown summary...")
        
        try:
            if output_type == 'quick':
                return self.markdown_generator.generate_quick_summary(
                    analysis_results['repository_info'],
                    analysis_results['structure_analysis']
                )
            
            elif output_type == 'full':
                return self.markdown_generator.generate_summary(
                    analysis_results['repository_info'],
                    analysis_results['structure_analysis'],
                    analysis_results.get('dependency_analysis', {}),
                    analysis_results.get('code_metrics', {}),
                    analysis_results.get('pattern_analysis', {}),
                    analysis_results.get('file_contents', {}),
                    analysis_results.get('llm_analysis', {}),
                    analysis_results.get('code_insights', {})
                )
            
            else:
                raise ValueError(f"Unsupported output type: {output_type}")
                
        except Exception as e:
            logger.error(f"Error generating markdown summary: {e}")
            raise
    
    def analyze_and_summarize(self, repo_url: str, 
                            output_file: Optional[str] = None,
                            output_type: str = 'full',
                            quick_analysis: bool = False) -> str:
        """
        Complete workflow: analyze repository and generate summary
        
        Args:
            repo_url: GitHub repository URL
            output_file: Optional file path to save the summary
            output_type: Type of summary ('full', 'quick')
            quick_analysis: Whether to perform quick analysis
            
        Returns:
            Generated markdown summary
        """
        logger.info(f"Starting complete analysis and summarization for: {repo_url}")
        
        try:
            # Analyze repository
            analysis_results = self.analyze_repository(
                repo_url, 
                include_file_contents=(output_type == 'full' and not quick_analysis),
                quick_analysis=quick_analysis
            )
            
            # Generate summary
            markdown_summary = self.generate_markdown_summary(analysis_results, output_type)
            
            # Save to file if specified
            if output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_summary)
                
                logger.info(f"Summary saved to: {output_path}")
            
            logger.info("Analysis and summarization completed successfully")
            return markdown_summary
            
        except Exception as e:
            logger.error(f"Error in complete workflow: {e}")
            raise
    
    def _filter_contents(self, contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter repository contents to exclude irrelevant files and directories
        
        Args:
            contents: List of file/directory information
            
        Returns:
            Filtered list of relevant files
        """
        filtered = []
        
        for item in contents:
            if item['type'] != 'file':
                continue
            
            file_path = Path(item['path'])
            
            # Skip files in excluded directories
            if any(excluded_dir in file_path.parts for excluded_dir in self.excluded_dirs):
                continue
            
            # Skip files with excluded extensions
            if file_path.suffix.lower() in self.excluded_extensions:
                continue
            
            # Skip very large files
            file_size = item.get('size', 0)
            if file_size > self.max_file_size:
                logger.debug(f"Skipping large file: {item['path']} ({file_size} bytes)")
                continue
            
            # Skip hidden files (except important ones)
            if (file_path.name.startswith('.') and 
                file_path.name not in {'.gitignore', '.env.example', '.dockerignore', 
                                     '.eslintrc.json', '.prettierrc', '.travis.yml'}):
                continue
            
            filtered.append(item)
        
        # Limit total files to analyze
        if len(filtered) > self.max_files_to_analyze:
            logger.warning(f"Too many files ({len(filtered)}), limiting to {self.max_files_to_analyze}")
            # Prioritize important files
            filtered = self._prioritize_files(filtered)[:self.max_files_to_analyze]
        
        return filtered
    
    def _prioritize_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prioritize files for analysis based on importance
        
        Args:
            files: List of file information
            
        Returns:
            Prioritized list of files
        """
        def priority_score(file_info: Dict[str, Any]) -> int:
            path = Path(file_info['path'])
            filename = path.name.lower()
            extension = path.suffix.lower()
            
            score = 0
            
            # High priority files
            if filename in {'readme.md', 'package.json', 'requirements.txt', 'dockerfile', 'makefile'}:
                score += 100
            
            # Configuration files
            if any(config in filename for config in ['config', '.env', 'settings']):
                score += 50
            
            # Source code files
            if extension in {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php'}:
                score += 30
            
            # Test files
            if 'test' in filename or 'spec' in filename:
                score += 20
            
            # Documentation
            if extension in {'.md', '.rst', '.txt'}:
                score += 15
            
            # Root level files get higher priority
            if len(path.parts) == 1:
                score += 25
            
            return score
        
        return sorted(files, key=priority_score, reverse=True)
    
    def _get_file_contents(self, repo, files: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Download file contents from GitHub repository
        
        Args:
            repo: GitHub repository object
            files: List of file information
            
        Returns:
            Dictionary mapping file paths to their contents
        """
        file_contents = {}
        
        for file_info in files:
            try:
                file_path = file_info['path']
                content = self.github_client.get_file_content(repo, file_path)
                
                if content is not None:
                    file_contents[file_path] = content
                else:
                    logger.debug(f"Could not read file: {file_path}")
                    
            except Exception as e:
                logger.warning(f"Error reading file {file_info['path']}: {e}")
                continue
        
        return file_contents
    
    def _identify_key_files(self, 
                           filtered_contents: List[Dict[str, Any]], 
                           file_contents: Dict[str, str]) -> List[str]:
        """
        Identify the most important files for LLM analysis
        
        Args:
            filtered_contents: List of filtered file information
            file_contents: Dictionary of file contents
            
        Returns:
            List of key file paths for prioritized LLM analysis
        """
        key_files = []
        
        # Priority categories
        main_files = []
        config_files = []
        core_files = []
        api_files = []
        
        for item in filtered_contents:
            file_path = item['path']
            file_name = Path(file_path).name.lower()
            
            # Main entry points
            if file_name in ['main.py', 'app.py', 'index.js', 'server.js', 'main.go', 'main.java']:
                main_files.append(file_path)
            
            # Configuration files with significant logic
            elif file_name in ['settings.py', 'config.js', 'webpack.config.js', 'next.config.js']:
                config_files.append(file_path)
            
            # Core application files
            elif any(core in file_name for core in ['app', 'core', 'engine', 'service', 'manager']):
                core_files.append(file_path)
            
            # API/Route files
            elif any(api in file_name for api in ['api', 'route', 'controller', 'handler']):
                api_files.append(file_path)
        
        # Add files in priority order
        key_files.extend(main_files[:2])  # Top 2 main files
        key_files.extend(config_files[:2])  # Top 2 config files
        key_files.extend(core_files[:3])  # Top 3 core files
        key_files.extend(api_files[:3])  # Top 3 API files
        
        # Add some additional files based on size and complexity
        remaining_files = [item['path'] for item in filtered_contents 
                          if item['path'] not in key_files and 
                          Path(item['path']).suffix.lower() in ['.py', '.js', '.ts', '.java', '.go']]
        
        # Sort by file size (prefer medium-sized files)
        remaining_files.sort(key=lambda f: abs(len(file_contents.get(f, '').split('\n')) - 100))
        
        # Add up to 5 more files
        key_files.extend(remaining_files[:5])
        
        # Remove duplicates and files not in file_contents
        key_files = list(dict.fromkeys(key_files))  # Remove duplicates, preserve order
        key_files = [f for f in key_files if f in file_contents]
        
        logger.info(f"Identified {len(key_files)} key files for LLM analysis: {key_files}")
        return key_files
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current GitHub API rate limit status
        
        Returns:
            Rate limit information
        """
        return self.github_client.get_rate_limit()
    
    def set_configuration(self, **kwargs):
        """
        Update configuration settings
        
        Args:
            **kwargs: Configuration parameters to update
        """
        if 'max_file_size' in kwargs:
            self.max_file_size = kwargs['max_file_size']
            
        if 'max_files_to_analyze' in kwargs:
            self.max_files_to_analyze = kwargs['max_files_to_analyze']
            
        if 'excluded_dirs' in kwargs:
            self.excluded_dirs.update(kwargs['excluded_dirs'])
            
        if 'excluded_extensions' in kwargs:
            self.excluded_extensions.update(kwargs['excluded_extensions'])
        
        logger.info("Configuration updated")


# Convenience functions for common use cases
def quick_summary(repo_url: str, github_token: Optional[str] = None) -> str:
    """
    Generate a quick summary of a repository
    
    Args:
        repo_url: GitHub repository URL
        github_token: GitHub API token
        
    Returns:
        Quick markdown summary
    """
    summarizer = GitHubRepoSummarizer(github_token)
    return summarizer.analyze_and_summarize(
        repo_url, 
        output_type='quick', 
        quick_analysis=True
    )


def full_analysis(repo_url: str, 
                 output_file: Optional[str] = None,
                 github_token: Optional[str] = None) -> str:
    """
    Generate a comprehensive analysis of a repository
    
    Args:
        repo_url: GitHub repository URL
        output_file: Optional file to save the summary
        github_token: GitHub API token
        
    Returns:
        Complete markdown summary
    """
    summarizer = GitHubRepoSummarizer(github_token)
    return summarizer.analyze_and_summarize(
        repo_url,
        output_file=output_file,
        output_type='full',
        quick_analysis=False
    )
