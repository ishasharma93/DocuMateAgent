# Runner for LLMCodeAnalyzer — main-llm.py
# Loads configuration from .env (or Key Vault), instantiates the analyzer, and runs repository analysis.

import os
import sys
import json
import argparse
import asyncio
import logging
from pathlib import Path

# Ensure src package is importable when running from repo root
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Local imports
try:
    from src.llm_code_analyzer.llm_code_analyzer import LLMCodeAnalyzer
except Exception as e:
    print(f"Failed to import LLMCodeAnalyzer: {e}")
    raise

# Optional KeyVault helper (only used if AZURE_KEYVAULT_URL is set)
KEYVAULT_HELPER = None
if os.getenv('AZURE_KEYVAULT_URL'):
    try:
        from src.llm_code_analyzer.mcp.keyvault_helper import KeyVaultHelper
        KEYVAULT_HELPER = KeyVaultHelper(os.getenv('AZURE_KEYVAULT_URL'))
    except Exception as e:
        # If KeyVaultHelper cannot be imported/initialized, fall back to env vars
        print(f"Warning: KeyVaultHelper unavailable: {e}")
        KEYVAULT_HELPER = None


def get_secret_or_env(secret_name: str, env_name: str) -> str:
    """Try Key Vault first (if available) then fallback to environment variable."""
    if KEYVAULT_HELPER:
        try:
            val = KEYVAULT_HELPER.get_secret(secret_name)
            if val:
                return val
        except Exception:
            pass
    return os.getenv(env_name)


async def run_analysis(repo_url: str, repo_type: str, model: str, use_azure: bool, output: str | None):
    # Determine credentials and tokens
    # LLM API key (Azure or OpenAI)
    api_key = None
    api_base = None

    if use_azure:
        api_key = get_secret_or_env('AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_API_KEY')
        api_base = os.getenv('AZURE_OPENAI_ENDPOINT') or os.getenv('AZURE_OPENAI_API_BASE')
    else:
        api_key = get_secret_or_env('OPENAI_API_KEY', 'OPENAI_API_KEY')

    # MCP tokens
    github_token = get_secret_or_env('GITHUB_MCP_API_KEY', 'GITHUB_TOKEN') or get_secret_or_env('GITHUB_MCP_API_KEY', 'GITHUB_MCP_API_KEY')
    azure_devops_pat = get_secret_or_env('AZURE_DEVOPS_MCP_API_KEY', 'AZURE_DEVOPS_PAT') or get_secret_or_env('AZURE_DEVOPS_MCP_API_KEY', 'AZURE_DEVOPS_MCP_API_KEY')

    analyzer = LLMCodeAnalyzer(
        api_key=api_key,
        model=model,
        api_base=api_base,
        use_azure=use_azure,
        enable_mcp=True,
        azure_devops_pat=azure_devops_pat,
        github_token=github_token
    )

    try:
        result = await analyzer.analyze_repository_with_mcp(repo_url, repository_type=repo_type)
    finally:
        # Attempt to close MCP clients if analyzer provides method
        try:
            await analyzer.close_mcp_clients()
        except Exception:
            pass

    # Serialize dataclasses if present
    def default_serializer(obj):
        try:
            return obj.__dict__
        except Exception:
            return str(obj)

    out_text = json.dumps(result, default=default_serializer, indent=2)

    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(out_text)
        print(f"Analysis written to: {output}")
    else:
        print(out_text)


def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='Run LLMCodeAnalyzer against a repository (MCP)')
    # repository may be provided as a positional argument or via REPOSITORY env var in .env
    parser.add_argument('repository', nargs='?', default=os.getenv('REPOSITORY'),
                        help='Repository URL to analyze (e.g. https://github.com/owner/repo). If not provided, will use REPOSITORY env var')
    # repository type can be provided via REPOSITORY_TYPE env var
    parser.add_argument('--type', choices=['github', 'azure_devops'], default=os.getenv('REPOSITORY_TYPE', 'github'), help='Repository type (or set REPOSITORY_TYPE in .env)')
    parser.add_argument('--model', default=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o'), help='LLM model or deployment name (or set LLM_MODEL in .env)')
    parser.add_argument('--azure', action='store_true', help='Use Azure OpenAI settings (AZURE_OPENAI_* env vars)')
    # output path can come from ANALYSIS_OUTPUT env var
    parser.add_argument('--output', '-o', default=os.getenv('ANALYSIS_OUTPUT'), help='Write JSON output to a file instead of stdout (or set ANALYSIS_OUTPUT in .env)')
    args = parser.parse_args()

    # If repository not provided via CLI, check env and fail fast with helpful message
    if not args.repository:
        print("Error: repository URL not provided. Pass it as an argument or set the REPOSITORY env variable in your .env file.")
        parser.print_help()
        sys.exit(2)

    # If user did not pass --azure, auto-detect from env
    use_azure = args.azure or bool(os.getenv('AZURE_OPENAI_ENDPOINT') or os.getenv('AZURE_OPENAI_API_KEY'))

    try:
        asyncio.run(run_analysis(args.repository, args.type, args.model, use_azure, args.output))
    except KeyboardInterrupt:
        print('\nCancelled by user')
    except Exception as e:
        print(f"Analysis failed: {e}")
        raise


if __name__ == '__main__':
    main()
