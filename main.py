#!/usr/bin/env python3
"""
GitHub Repository Summarization Agent - Command Line Interface

Usage:
    python main.py --repo-url https://github.com/owner/repo
    python main.py --repo owner/repo --output summary.md
    python main.py --repo-url https://github.com/owner/repo --quick
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.repo_summarizer import GitHubRepoSummarizer, quick_summary, full_analysis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_argparser() -> argparse.ArgumentParser:
    """Setup command line argument parser"""
    parser = argparse.ArgumentParser(
        description='Analyze GitHub repositories and generate comprehensive markdown summaries',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --repo-url https://github.com/facebook/react
  %(prog)s --repo microsoft/vscode --output vscode_analysis.md
  %(prog)s --repo-url https://github.com/django/django --quick
  %(prog)s --repo owner/repo --token ghp_xxxxxxxxxxxx
  %(prog)s --repo-url https://github.com/rust-lang/rust --output rust_summary.md --verbose

Environment Variables:
  GITHUB_TOKEN    GitHub personal access token for API access
  MAX_FILE_SIZE   Maximum file size to analyze in bytes (default: 1MB)
        """
    )
    
    # Required arguments
    repo_group = parser.add_mutually_exclusive_group(required=True)
    repo_group.add_argument(
        '--repo-url', 
        type=str,
        help='Full GitHub repository URL (e.g., https://github.com/owner/repo)'
    )
    repo_group.add_argument(
        '--repo', 
        type=str,
        help='Repository in owner/repo format (e.g., facebook/react)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path for the markdown summary (default: prints to stdout)'
    )
    
    parser.add_argument(
        '--token', '-t',
        type=str,
        help='GitHub personal access token (overrides GITHUB_TOKEN env var)'
    )
    
    parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='Perform quick analysis without detailed code inspection'
    )
    
    parser.add_argument(
        '--type',
        choices=['full', 'quick'],
        default='full',
        help='Type of summary to generate (default: full)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--max-file-size',
        type=int,
        default=1024*1024,
        help='Maximum file size to analyze in bytes (default: 1MB)'
    )
    
    parser.add_argument(
        '--max-files',
        type=int,
        default=500,
        help='Maximum number of files to analyze (default: 500)'
    )
    
    parser.add_argument(
        '--llm-api-key',
        type=str,
        help='OpenAI API key for LLM-powered code analysis (overrides OPENAI_API_KEY env var)'
    )
    
    parser.add_argument(
        '--llm-model',
        type=str,
        default='gpt-4',
        choices=['gpt-4', 'gpt-3.5-turbo', 'gpt-4-turbo'],
        help='LLM model to use for code analysis (default: gpt-4)'
    )
    
    parser.add_argument(
        '--disable-llm',
        action='store_true',
        help='Disable LLM-powered code analysis'
    )
    
    # Azure OpenAI specific arguments
    parser.add_argument(
        '--azure-openai-key',
        type=str,
        help='Azure OpenAI API key (overrides AZURE_OPENAI_API_KEY env var)'
    )
    
    parser.add_argument(
        '--azure-openai-endpoint',
        type=str,
        help='Azure OpenAI endpoint URL (overrides AZURE_OPENAI_ENDPOINT env var)'
    )
    
    parser.add_argument(
        '--azure-openai-deployment',
        type=str,
        help='Azure OpenAI deployment name (overrides AZURE_OPENAI_DEPLOYMENT_NAME env var)'
    )
    
    parser.add_argument(
        '--use-azure',
        action='store_true',
        help='Force use of Azure OpenAI instead of regular OpenAI'
    )
    
    return parser


def validate_arguments(args) -> str:
    """Validate and normalize arguments"""
    # Determine repository URL
    if args.repo_url:
        repo_url = args.repo_url
    elif args.repo:
        repo_url = f"https://github.com/{args.repo}"
    else:
        raise ValueError("Repository URL or owner/repo must be specified")
    
    # Validate URL format
    if not (repo_url.startswith('https://github.com/') or '/' in repo_url):
        raise ValueError("Invalid repository URL or format")
    
    return repo_url


def setup_logging(verbose: bool):
    """Setup logging configuration"""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        # Enable debug logging for our modules
        logging.getLogger('src').setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)
        # Suppress third-party debug logs
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('github').setLevel(logging.WARNING)


def get_github_token(args) -> Optional[str]:
    """Get GitHub token from arguments or environment"""
    token = args.token or os.getenv('GITHUB_TOKEN')
    
    if not token:
        logger.warning("""
No GitHub token provided. API rate limits will be lower.
Set GITHUB_TOKEN environment variable or use --token argument.
Get a token at: https://github.com/settings/tokens
        """.strip())
    
    return token


def get_llm_api_key(args) -> Optional[str]:
    """Get LLM API key from arguments or environment"""
    if args.disable_llm:
        return None
        
    api_key = args.llm_api_key or os.getenv('OPENAI_API_KEY')
    
    if not api_key and not args.disable_llm:
        logger.warning("""
No LLM API key provided. Code analysis will be limited to static analysis.
For detailed code explanations, set OPENAI_API_KEY environment variable or use --llm-api-key argument.
Get an OpenAI API key at: https://platform.openai.com/api-keys
        """.strip())
    
    return api_key


def get_debug_args():
    """Get arguments from environment variables for debug mode"""
    class DebugArgs:
        def __init__(self):
            # Repository settings
            self.repo = os.getenv('DEBUG_REPO_URL', 'facebook/react')
            self.repo_url = None
            self.output = os.getenv('DEBUG_OUTPUT_FILE', 'debug_analysis.md')
            
            # Debug settings
            self.verbose = True  # Always verbose in debug mode
            self.quick = os.getenv('DEBUG_QUICK_ANALYSIS', 'true').lower() == 'true'
            self.type = 'quick' if self.quick else 'full'
            
            # Token settings
            self.token = None  # Will use environment variable
            
            # LLM settings
            self.llm_api_key = None  # Will use environment variable
            self.llm_model = os.getenv('DEBUG_LLM_MODEL', 'gpt-4')
            self.disable_llm = os.getenv('DEBUG_DISABLE_LLM', 'false').lower() == 'true'
            
            # Azure OpenAI settings
            self.azure_openai_key = None  # Will use environment variable
            self.azure_openai_endpoint = None  # Will use environment variable
            self.azure_openai_deployment = None  # Will use environment variable
            self.use_azure = os.getenv('DEBUG_USE_AZURE', 'true').lower() == 'true'
            
            # Analysis settings - handle comments in env vars
            max_file_size_str = os.getenv('MAX_FILE_SIZE', '1048576').split('#')[0].strip()
            max_files_str = os.getenv('MAX_FILES_TO_ANALYZE', '500').split('#')[0].strip()
            
            self.max_file_size = int(max_file_size_str)
            self.max_files = int(max_files_str)
            
    return DebugArgs()


def is_debug_mode():
    """Check if we're running in debug mode"""
    # Check if DEBUG_MODE is set in environment
    debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    
    # Also check if no command line arguments are provided (common in VS Code debugging)
    no_args = len(sys.argv) == 1
    
    return debug_mode or no_args


def main():
    """Main CLI entry point"""
    try:
        # Check if we're in debug mode
        if is_debug_mode():
            print("🔍 Debug Mode Activated")
            print("=" * 30)
            print(f"📁 Repository: {os.getenv('DEBUG_REPO_URL', 'facebook/react')}")
            print(f"📄 Output: {os.getenv('DEBUG_OUTPUT_FILE', 'debug_analysis.md')}")
            print(f"⚡ Quick Analysis: {os.getenv('DEBUG_QUICK_ANALYSIS', 'true')}")
            print(f"🤖 Use Azure: {os.getenv('DEBUG_USE_AZURE', 'true')}")
            print("=" * 30)
            
            # Use debug arguments from environment
            args = get_debug_args()
        else:
            # Parse command line arguments normally
            parser = setup_argparser()
            args = parser.parse_args()
        
        # Setup logging
        setup_logging(args.verbose)
        
        # Validate arguments
        repo_url = validate_arguments(args)
        
        # Get GitHub token
        github_token = get_github_token(args)
        
        # Get LLM API key (Azure or regular OpenAI)
        llm_api_key = get_llm_api_key(args)
        
        # Handle Azure OpenAI specific parameters
        azure_endpoint = args.azure_openai_endpoint or os.getenv('AZURE_OPENAI_ENDPOINT')
        azure_deployment = args.azure_openai_deployment or os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')
        azure_api_key = args.azure_openai_key or os.getenv('AZURE_OPENAI_API_KEY')
        
        # Use Azure if explicitly requested or if Azure credentials are available
        use_azure = args.use_azure or bool(azure_api_key and azure_endpoint)
        
        # Use Azure API key if available and using Azure
        if use_azure and azure_api_key:
            llm_api_key = azure_api_key
        
        # Determine analysis type
        if args.quick or args.type == 'quick':
            analysis_type = 'quick'
            quick_analysis = True
        else:
            analysis_type = 'full'
            quick_analysis = False
        
        logger.info(f"Starting {analysis_type} analysis of: {repo_url}")
        
        # Create summarizer with configuration
        summarizer = GitHubRepoSummarizer(
            github_token=github_token,
            max_file_size=args.max_file_size,
            llm_api_key=llm_api_key,
            llm_model=args.llm_model,
            enable_llm_analysis=not args.disable_llm,
            use_azure=use_azure,
            azure_endpoint=azure_endpoint,
            azure_deployment=azure_deployment
        )
        
        # Set additional configuration
        summarizer.set_configuration(
            max_files_to_analyze=args.max_files
        )
        
        # Check rate limit status
        rate_limit = summarizer.get_rate_limit_status()
        if rate_limit and 'core' in rate_limit:
            remaining = rate_limit['core'].get('remaining', 'unknown')
            logger.info(f"GitHub API rate limit remaining: {remaining}")
        
        # Perform analysis and generate summary
        summary = summarizer.analyze_and_summarize(
            repo_url=repo_url,
            output_file=args.output,
            output_type=analysis_type,
            quick_analysis=quick_analysis
        )
        
        # Output results
        if args.output:
            logger.info(f"Summary saved to: {args.output}")
            print(f"✅ Analysis complete! Summary saved to: {args.output}")
        else:
            print(summary)
        
        logger.info("Analysis completed successfully")
        
    except KeyboardInterrupt:
        logger.error("Analysis interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        if args.verbose if 'args' in locals() else False:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def demo_usage():
    """Demonstrate usage with popular repositories"""
    print("🚀 GitHub Repository Summarization Agent Demo")
    print("=" * 50)
    
    # Demo repositories
    demo_repos = [
        "facebook/react",
        "microsoft/vscode", 
        "django/django",
        "rust-lang/rust"
    ]
    
    print("\nTry analyzing these popular repositories:")
    for repo in demo_repos:
        print(f"  python main.py --repo {repo} --quick")
    
    print("\nFor detailed analysis:")
    print("  python main.py --repo facebook/react --output react_analysis.md")
    
    print("\nWith GitHub token:")
    print("  python main.py --repo microsoft/vscode --token ghp_your_token_here")
    
    print("\nSet up your GitHub token:")
    print("  1. Go to https://github.com/settings/tokens")
    print("  2. Generate a new token")
    print("  3. Set GITHUB_TOKEN environment variable")
    print("  4. Or use --token argument")


if __name__ == '__main__':
    # if len(sys.argv) == 1:
    #     # Show demo if no arguments provided
    #     demo_usage()
    #     sys.exit(0)
    
    main()
