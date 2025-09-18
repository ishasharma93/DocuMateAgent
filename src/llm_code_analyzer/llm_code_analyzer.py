"""
LLM Code Analyzer

Uses Large Language Models to analyze and explain code functionality, 
providing human-readable explanations of what code does.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json
import asyncio
from dataclasses import dataclass



def get_int_from_env(env_var: str, default: int) -> int:
    """Get integer value from environment variable, handling comments"""
    value_str = os.getenv(env_var, str(default)).split('#')[0].strip()
    return int(value_str)


# Use the official OpenAI client (for non-Azure usage)
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

# Import MCP server-client components
try:
    from .mcp.azure_devops_client import AzureDevOpsClient
    from .mcp.github_client import GitHubMCPClient
    from .mcp.client import MCPClient
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    AzureDevOpsClient = None
    GitHubMCPClient = None
    MCPClient = None

logger = logging.getLogger(__name__)


@dataclass
class CodeExplanation:
    """Data class for code explanation results"""
    file_path: str
    language: str
    summary: str
    main_functionality: str
    key_components: List[str]
    dependencies: List[str]
    complexity_assessment: str
    improvement_suggestions: List[str]
    code_patterns: List[str]


class LLMCodeAnalyzer:
    """Analyzes code using Large Language Models to provide explanations"""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 model: str = "gpt-4",
                 api_base: Optional[str] = None,
                 use_azure: bool = None,
                 enable_mcp: bool = True,
                 azure_devops_org: Optional[str] = None,
                 azure_devops_pat: Optional[str] = None,
                 github_token: Optional[str] = None):
        """
        Initialize LLM Code Analyzer with MCP server-client support
        
        Args:
            api_key: OpenAI or Azure OpenAI API key
            model: Model to use (gpt-4, gpt-3.5-turbo, etc.)
            api_base: Custom API base URL (optional)
            use_azure: Force Azure OpenAI usage (auto-detected if None)
            enable_mcp: Enable MCP server-client functionality
            azure_devops_org: Azure DevOps organization name
            azure_devops_pat: Azure DevOps Personal Access Token
            github_token: GitHub Personal Access Token
        """
        # Auto-detect Azure usage if not specified

        if use_azure is None:
            use_azure = bool(os.getenv('AZURE_OPENAI_ENDPOINT'))
        self.use_azure = use_azure
        self.model = model

        if self.use_azure:
            # Azure OpenAI configuration using openai package
            self.api_key = api_key or os.getenv('AZURE_OPENAI_API_KEY')
            self.api_base = os.getenv('AZURE_OPENAI_ENDPOINT')
            self.api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-06-01')
            self.deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', model)

            if not OPENAI_AVAILABLE:
                logger.error("OpenAI package not available. Install with: pip install openai")
                self.client = None
            elif not self.api_key or not self.api_base:
                logger.warning("Azure OpenAI API key or endpoint not set. Code explanations will be disabled.")
                self.client = None
            else:
                try:
                    self.client = AsyncOpenAI(
                        api_key=self.api_key,
                        base_url=self.api_base,
                        api_version=self.api_version
                    )
                    logger.info(f"Azure OpenAI client initialized - Endpoint: {self.api_base}, Deployment: {self.deployment_name}")
                except Exception as e:
                    logger.error(f"Failed to initialize Azure OpenAI client: {e}")
                    self.client = None
        else:
            # Regular OpenAI configuration
            if not OPENAI_AVAILABLE:
                logger.error("OpenAI package not available. Install with: pip install openai")
                self.client = None
                return
            self.api_key = api_key or os.getenv('OPENAI_API_KEY')
            if not self.api_key:
                logger.warning("No OpenAI API key provided. Code explanations will be disabled.")
                self.client = None
            else:
                try:
                    self.client = AsyncOpenAI(
                        api_key=self.api_key,
                        base_url=api_base if api_base else None
                    )
                    logger.info(f"OpenAI client initialized with model: {self.model}")
                except Exception as e:
                    logger.error(f"Failed to initialize OpenAI client: {e}")
                    self.client = None
        
        # Configuration
        self.max_code_length = get_int_from_env('MAX_CODE_LENGTH_FOR_LLM', 8000)
        self.max_concurrent_requests = get_int_from_env('MAX_CONCURRENT_LLM_REQUESTS', 3)
        
        # Initialize MCP servers if enabled
        self.mcp_enabled = enable_mcp and MCP_AVAILABLE
        self.azure_devops_client = None
        self.github_mcp_client = None
        
        if self.mcp_enabled:
            try:
                # Initialize Azure DevOps MCP client
                if azure_devops_org or os.getenv('AZURE_DEVOPS_ORGANIZATION'):
                    self.azure_devops_client = AzureDevOpsClient(
                        organization=azure_devops_org,
                        personal_access_token=azure_devops_pat
                    )
                    logger.info("Azure DevOps MCP client initialized")
                
                # Initialize GitHub MCP client
                if github_token or os.getenv('GITHUB_TOKEN'):
                    self.github_mcp_client = GitHubMCPClient(
                        github_token=github_token
                    )
                    logger.info("GitHub MCP client initialized")
                    
            except Exception as e:
                logger.warning(f"Failed to initialize MCP clients: {e}")
                self.mcp_enabled = False
        
        # Supported file extensions for detailed analysis
        self.code_extensions = {
            '.py': 'Python',
            '.js': 'JavaScript', 
            '.ts': 'TypeScript',
            '.jsx': 'React JSX',
            '.tsx': 'React TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.go': 'Go',
            '.rs': 'Rust',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            '.sql': 'SQL',
            '.sh': 'Shell Script',
            '.bash': 'Bash Script',
            '.ps1': 'PowerShell'
        }
    
    def _clone_repo(self, repository_url: str):
        """Clone a repository to a temporary directory and return the cloned path (Path) and tmpdir."""
        import tempfile
        import subprocess
        import shutil
        from pathlib import Path

        tmpdir = tempfile.mkdtemp(prefix="repo_clone_")
        cloned_path = Path(tmpdir) / Path(repository_url.rstrip('/').split('/')[-1].replace('.git', ''))
        try:
            logger.info(f"Cloning {repository_url} -> {cloned_path}")
            subprocess.run(["git", "clone", repository_url, str(cloned_path)], check=True)
        except Exception as e:
            shutil.rmtree(tmpdir, ignore_errors=True)
            raise
        return tmpdir, cloned_path

    def _collect_code_files(self, cloned_path: 'Path') -> tuple:
        """Walk a cloned repo and collect relevant files and compute total size."""
        from pathlib import Path
        import os

        file_contents = {}
        total_size = 0
        for root, dirs, files in os.walk(cloned_path):
            for fname in files:
                fpath = Path(root) / fname
                rel_path = str(fpath.relative_to(cloned_path))
                _, ext = os.path.splitext(fname)
                include_ext = ext.lower() in self.code_extensions or fname.lower() in (
                    'package.json', 'requirements.txt', 'pyproject.toml', 'pom.xml', 'Dockerfile', 'Makefile', 'README.md')
                if include_ext:
                    try:
                        content = fpath.read_text(encoding='utf-8')
                    except Exception:
                        try:
                            content = fpath.read_text(encoding='latin-1')
                        except Exception:
                            logger.warning(f"Failed to read file {fpath}, skipping")
                            continue
                    file_contents[rel_path] = content
                    total_size += len(content)
        return file_contents, total_size

    async def _create_github_issues(self, owner: str, repo: str, code_insights: Dict[str, Any], llm_analysis: Dict[str, CodeExplanation], cloned_path) -> List[str]:
        """Create GitHub issues for technical debt candidates and return list of created issue URLs."""
        created_issues = []
        try:
            token = None
            if self.github_mcp_client and getattr(self.github_mcp_client, 'github_token', None):
                token = self.github_mcp_client.github_token
            elif os.getenv('GITHUB_TOKEN'):
                token = os.getenv('GITHUB_TOKEN')

            if not token:
                return created_issues

            import aiohttp

            candidates = []
            for theme in code_insights.get('improvement_themes', []):
                candidates.append(f"Investigate: {theme}")
            for explanation in llm_analysis.values():
                try:
                    if hasattr(explanation, 'improvement_suggestions') and explanation.improvement_suggestions:
                        for sugg in explanation.improvement_suggestions:
                            if isinstance(sugg, str) and sugg.strip():
                                candidates.append(sugg.strip())
                            elif isinstance(sugg, dict):
                                candidates.append(sugg.get('text') or sugg.get('description') or str(sugg))
                except Exception:
                    continue

            # Deduplicate
            unique = []
            seen = set()
            for c in candidates:
                k = c.strip().lower()[:200]
                if k and k not in seen:
                    seen.add(k)
                    unique.append(c.strip())

            issues_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json'}

            async with aiohttp.ClientSession(headers=headers) as session:
                # fetch open issues (first page)
                existing_titles = []
                try:
                    async with session.get(issues_url, params={'state': 'open', 'per_page': 100}) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            existing_titles = [it.get('title', '').lower() for it in data if isinstance(it, dict)]
                except Exception:
                    existing_titles = []

                for cand in unique:
                    title = cand if len(cand) <= 120 else cand[:117] + '...'
                    if title.lower() in existing_titles:
                        continue
                    body = f"Automated technical debt identified by DocuMateAgent LLM analysis:\n\n{cand}\n\nSee generated report at: {str(cloned_path / 'TechnicalDocument.md')}\n"
                    payload = {'title': title, 'body': body, 'labels': ['technical-debt', 'automated']}
                    try:
                        async with session.post(issues_url, json=payload) as post:
                            if post.status in (200, 201):
                                created = await post.json()
                                created_issues.append(created.get('html_url'))
                            else:
                                logger.warning(f"Failed to create issue for candidate: {cand[:80]} (status {post.status})")
                    except Exception as e:
                        logger.warning(f"Exception while creating issue: {e}")

        except Exception as e:
            logger.warning(f"Issue creation step failed: {e}")
        return created_issues

    async def _create_azure_workitems(self, org: str, project: str, code_insights: Dict[str, Any], llm_analysis: Dict[str, CodeExplanation], cloned_path) -> List[str]:
        """Create Azure DevOps work items for technical debt candidates and return list of created work item URLs."""
        created_items = []
        try:
            if not self.azure_devops_client or not getattr(self.azure_devops_client, 'personal_access_token', None):
                return created_items

            token_header = self.azure_devops_client.auth_header
            import aiohttp

            candidates = []
            for theme in code_insights.get('improvement_themes', []):
                candidates.append(f"Investigate: {theme}")
            for explanation in llm_analysis.values():
                try:
                    if hasattr(explanation, 'improvement_suggestions') and explanation.improvement_suggestions:
                        for sugg in explanation.improvement_suggestions:
                            if isinstance(sugg, str) and sugg.strip():
                                candidates.append(sugg.strip())
                            elif isinstance(sugg, dict):
                                candidates.append(sugg.get('text') or sugg.get('description') or str(sugg))
                except Exception:
                    continue

            # Deduplicate
            unique = []
            seen = set()
            for c in candidates:
                k = c.strip().lower()[:200]
                if k and k not in seen:
                    seen.add(k)
                    unique.append(c.strip())

            # Azure DevOps work item create endpoint
            base = self.azure_devops_client.base_url  # https://dev.azure.com/{org}
            api_ver = self.azure_devops_client.api_version
            async with aiohttp.ClientSession(headers={'Authorization': token_header, 'Content-Type': 'application/json-patch+json'}) as session:
                for cand in unique:
                    # construct patch body
                    title = cand if len(cand) <= 120 else cand[:117] + '...'
                    description = f"Automated technical debt identified by DocuMateAgent LLM analysis:\n\n{cand}\n\nSee generated report at: {str(cloned_path / 'TechnicalDocument.md')}\n"
                    patch = [
                        {"op": "add", "path": "/fields/System.Title", "value": title},
                        {"op": "add", "path": "/fields/System.Description", "value": description}
                    ]
                    url = f"{base}/{project}/_apis/wit/workitems/$Issue?api-version={api_ver}"
                    try:
                        async with session.post(url, json=patch) as resp:
                            if resp.status in (200, 201):
                                data = await resp.json()
                                created_items.append(data.get('url') or data.get('id'))
                            else:
                                logger.warning(f"Failed to create Azure work item for candidate: {cand[:80]} (status {resp.status})")
                    except Exception as e:
                        logger.warning(f"Exception while creating Azure work item: {e}")
        except Exception as e:
            logger.warning(f"Azure work item creation failed: {e}")
        return created_items

    async def _analyze_repository_local(self, repository_url: str, platform: str, identifiers: Dict[str, str], repo_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Shared flow: clone repo, collect files, run LLM analysis, generate docs, and create issues/work items."""
        from pathlib import Path
        import os

        results: Dict[str, Any] = {}

        # 1) Clone
        tmpdir, cloned_path = self._clone_repo(repository_url)

        # 2) Collect files
        file_contents, total_size = self._collect_code_files(cloned_path)
        results['collected_files'] = len(file_contents)

        # 3) Run LLM analysis (temporarily increase max)
        prev_max = os.environ.get('MAX_FILES_FOR_LLM_ANALYSIS')
        os.environ['MAX_FILES_FOR_LLM_ANALYSIS'] = str(len(file_contents) or 1)
        try:
            llm_analysis = await self.analyze_codebase(file_contents)
        finally:
            if prev_max is None:
                os.environ.pop('MAX_FILES_FOR_LLM_ANALYSIS', None)
            else:
                os.environ['MAX_FILES_FOR_LLM_ANALYSIS'] = prev_max

        results['llm_analysis_count'] = len(llm_analysis)

        # 4) Insights
        code_insights = self.generate_code_insights_summary(llm_analysis)
        results['code_insights'] = code_insights

        # 5) Minimal structure/dependency/code_metrics (same as previous logic)
        structure_analysis = {'total_files': len(file_contents), 'total_size': total_size, 'languages': {}, 'file_distribution': {}, 'source_files': [], 'test_files': [], 'config_files': [], 'documentation_files': [], 'build_files': [], 'largest_files': []}
        for path_str, content in file_contents.items():
            ext = Path(path_str).suffix.lower()
            lang = self.code_extensions.get(ext)
            if lang:
                structure_analysis['languages'][lang] = structure_analysis['languages'].get(lang, 0) + 1
                structure_analysis['source_files'].append(path_str)
            lower = path_str.lower()
            if 'test' in lower or lower.startswith('tests') or '/tests/' in lower:
                structure_analysis['test_files'].append(path_str)
            if any(cfg in lower for cfg in ['package.json', 'requirements.txt', 'pyproject.toml', 'pom.xml', 'setup.py']):
                structure_analysis['config_files'].append(path_str)
            if any(doc in lower for doc in ['readme', 'changelog', 'license', 'contributing']):
                structure_analysis['documentation_files'].append(path_str)
            if any(build in path_str for build in ['Dockerfile', 'Makefile']):
                structure_analysis['build_files'].append(path_str)
        largest = sorted([(p, len(c)) for p, c in file_contents.items()], key=lambda x: x[1], reverse=True)[:10]
        structure_analysis['largest_files'] = largest

        # basic dependency analysis
        dependency_analysis = {'dependencies': {}, 'dev_dependencies': {}, 'package_managers': [], 'frameworks': [], 'build_tools': [], 'testing_frameworks': []}
        if any(f for f in file_contents if f.lower().endswith('requirements.txt')):
            dependency_analysis['package_managers'].append('pip')
        if any(f for f in file_contents if f.lower().endswith('package.json')):
            dependency_analysis['package_managers'].append('npm')
        if any(f for f in file_contents if f.lower().endswith('pom.xml')):
            dependency_analysis['package_managers'].append('maven')

        # code metrics
        total_lines = code_lines = comment_lines = blank_lines = 0
        languages_metrics = {}
        for path_str, content in file_contents.items():
            lines = content.splitlines()
            total_lines += len(lines)
            for ln in lines:
                stripped = ln.strip()
                if not stripped:
                    blank_lines += 1
                elif stripped.startswith('#') or stripped.startswith('//'):
                    comment_lines += 1
                else:
                    code_lines += 1
            lang = self.code_extensions.get(Path(path_str).suffix.lower(), 'Unknown')
            lm = languages_metrics.setdefault(lang, {'files': 0, 'lines': 0, 'code_lines': 0, 'comment_lines': 0})
            lm['files'] += 1
            lm['lines'] += len(lines)
            lm['code_lines'] += max(0, len(lines) - 1)
            lm['comment_lines'] += comment_lines

        code_metrics = {'total_lines': total_lines, 'code_lines': code_lines, 'comment_lines': comment_lines, 'blank_lines': blank_lines, 'files_analyzed': len(file_contents), 'languages': languages_metrics, 'complexity_indicators': {'large_files': [{'file': p, 'lines': l} for p, l in largest], 'deeply_nested': []}}

        # 6) Generate markdown files
        from src.markdown_generator import MarkdownGenerator
        md = MarkdownGenerator()
        try:
            functional_md = md.generate_quick_summary(repo_info or {}, structure_analysis)
            functional_path = cloned_path / 'FunctionalDocument.md'
            functional_path.write_text(functional_md, encoding='utf-8')

            technical_md = md.generate_summary(repo_info or {}, structure_analysis, dependency_analysis, code_metrics, {}, file_contents, llm_analysis, code_insights)
            technical_path = cloned_path / 'TechnicalDocument.md'
            technical_path.write_text(technical_md, encoding='utf-8')

            build_md_lines = [f"# Build & Run Instructions for {identifiers.get('repo', '') or identifiers.get('repository', '')}\n"]
            if any('dockerfile' in f.lower() for f in file_contents):
                build_md_lines.append('## Docker\n')
                build_md_lines.append('```bash\n# Build the image\ndocker build -t myapp:latest .\n# Run the container\ndocker run -p 8080:8080 myapp:latest\n```\n')
            if any(f.lower().endswith('package.json') for f in file_contents):
                build_md_lines.append('## Node.js / npm\n')
                build_md_lines.append('```bash\n# Install\nnpm install\n# Run\nnpm start\n```\n')
            if any(f.lower().endswith('requirements.txt') for f in file_contents):
                build_md_lines.append('## Python\n')
                build_md_lines.append('```bash\n# Create venv\npython -m venv .venv\nsource .venv/bin/activate  # or .\\.venv\\Scripts\\activate on Windows\n# Install deps\npip install -r requirements.txt\n# Run main if exists\npython main.py\n```\n')
            if any(f.lower().endswith('makefile') or f == 'Makefile' for f in file_contents):
                build_md_lines.append('## Makefile\n')
                build_md_lines.append('```bash\n# Build\nmake build\n# Run\nmake run\n```\n')

            build_md = '\n'.join(build_md_lines)
            build_path = cloned_path / 'CodeBuild&Run.md'
            build_path.write_text(build_md, encoding='utf-8')

            results['generated_documents'] = {'functional': str(functional_path), 'technical': str(technical_path), 'build_and_run': str(build_path)}
        except Exception as e:
            logger.error(f"Failed to generate markdown documents: {e}")
            results['generated_documents_error'] = str(e)

        # 7) Create issues/work items based on platform
        if platform == 'github':
            owner = identifiers.get('owner')
            repo_name = identifiers.get('repo')
            created = await self._create_github_issues(owner, repo_name, code_insights, llm_analysis, cloned_path)
            if created:
                results['created_issues'] = created
        elif platform == 'azure_devops':
            org = identifiers.get('org')
            project = identifiers.get('project')
            created = await self._create_azure_workitems(org, project, code_insights, llm_analysis, cloned_path)
            if created:
                results['created_workitems'] = created

        # 8) return results
        results['cloned_path'] = str(cloned_path)
        results['files_analyzed'] = list(file_contents.keys())
        return results

    async def analyze_repository_with_mcp(self, 
                                         repository_url: str,
                                         repository_type: str = "github") -> Dict[str, Any]:
        """
        Analyze a repository using MCP server-client architecture

        Args:
            repository_url: Repository URL (GitHub or Azure DevOps)
            repository_type: Type of repository ("github" or "azure_devops")
            
        Returns:
            Repository analysis results with MCP integration
        """
        if not self.mcp_enabled:
            logger.warning("MCP not enabled, falling back to basic analysis")
            return {"error": "MCP not enabled"}

        try:
            if repository_type == "github":
                return await self._analyze_github_repository(repository_url)
            elif repository_type == "azure_devops":
                return await self._analyze_azure_devops_repository(repository_url)
            else:
                return {"error": f"Unsupported repository type: {repository_type}"}
        except Exception as e:
            logger.error(f"MCP repository analysis failed: {e}")
            return {"error": str(e)}
    
    async def _analyze_github_repository(self, repository_url: str) -> Dict[str, Any]:
        """Analyze GitHub repository using MCP client

        This implementation clones the repository locally, collects all code files,
        runs LLM analysis against all files, and generates three markdown documents:
        - FunctionalDocument.md (high-level / functional overview)
        - TechnicalDocument.md (detailed technical summary)
        - CodeBuild&Run.md (build & run instructions)
        """
        if not self.github_mcp_client:
            raise Exception("GitHub MCP client not initialized")

        import re
        from src.markdown_generator import MarkdownGenerator

        match = re.match(r'https://github\.com/([^/]+)/([^/]+)/?', repository_url)
        if not match:
            return {"error": "Invalid GitHub repository URL"}

        owner, repo = match.groups()
        repo = repo.rstrip('.git')

        logger.info(f"Analyzing GitHub repository (clone): {owner}/{repo}")

        results: Dict[str, Any] = {}

        # Shared analysis flow: clone, collect files, analyze, generate docs, create issues
        identifiers = {'owner': owner, 'repo': repo, 'repository': repo}
        try:
            return await self._analyze_repository_local(repository_url, "github", identifiers)
        except Exception as e:
            logger.error(f"GitHub repository analysis failed: {e}")
            results['error'] = str(e)
            return results
    
    async def _analyze_azure_devops_repository(self, repository_url: str) -> Dict[str, Any]:
        """Analyze Azure DevOps repository using MCP client"""
        if not self.azure_devops_client:
            raise Exception("Azure DevOps MCP client not initialized")
        
        # Parse Azure DevOps URL to extract organization, project, and repository
        import re
        match = re.match(r'https://dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/]+)/?', repository_url)
        if not match:
            # Try alternative format
            match = re.match(r'https://([^.]+)\.visualstudio\.com/([^/]+)/_git/([^/]+)/?', repository_url)
            if not match:
                return {"error": "Invalid Azure DevOps repository URL"}
        
        org, project, repo = match.groups()
        
        logger.info(f"Analyzing Azure DevOps repository: {org}/{project}/{repo}")
        
        # Gather repository information using MCP tools
        results = {}
        
        # Shared analysis flow: clone, collect files, analyze, generate docs, create issues
        identifiers = {'org': org, 'project': project, 'repo': repo}
        try:
            return await self._analyze_repository_local(repository_url, "azure_devops", identifiers)
        except Exception as e:
            logger.error(f"Azure DevOps repository analysis failed: {e}")
            results['error'] = str(e)
            return results
    
    async def get_mcp_repository_files(self, 
                                      repository_url: str,
                                      repository_type: str = "github",
                                      max_files: int = 50) -> Dict[str, str]:
        """
        Get repository files content using MCP clients
        
        Args:
            repository_url: Repository URL
            repository_type: Type of repository ("github" or "azure_devops")
            max_files: Maximum number of files to retrieve
            
        Returns:
            Dictionary mapping file paths to their contents
        """
        if not self.mcp_enabled:
            logger.warning("MCP not enabled, returning empty file list")
            return {}
        
        try:
            if repository_type == "github":
                return await self._get_github_files(repository_url, max_files)
            elif repository_type == "azure_devops":
                return await self._get_azure_devops_files(repository_url, max_files)
            else:
                raise ValueError(f"Unsupported repository type: {repository_type}")
        except Exception as e:
            logger.error(f"Failed to get MCP repository files: {e}")
            return {}
    
    async def _get_github_files(self, repository_url: str, max_files: int) -> Dict[str, str]:
        """Get GitHub repository files using MCP"""
        if not self.github_mcp_client:
            return {}
        
        # Parse repository URL
        import re
        match = re.match(r'https://github\.com/([^/]+)/([^/]+)/?', repository_url)
        if not match:
            return {}
        
        owner, repo = match.groups()
        repo = repo.rstrip('.git')
        
        file_contents = {}
        files_processed = 0
        
        async def process_directory(path: str = ""):
            nonlocal files_processed
            if files_processed >= max_files:
                return
            
            try:
                contents = await self.github_mcp_client._get_repository_contents(owner, repo, path)
                
                if isinstance(contents, list):
                    for item in contents:
                        if files_processed >= max_files:
                            break
                        
                        if item['type'] == 'file':
                            # Check if it's a code file
                            file_path = item['path']
                            _, ext = os.path.splitext(file_path)
                            
                            if ext.lower() in self.code_extensions and item['size'] < self.max_code_length:
                                try:
                                    file_content = await self.github_mcp_client._get_file_content(owner, repo, file_path)
                                    if 'decoded_content' in file_content:
                                        file_contents[file_path] = file_content['decoded_content']
                                        files_processed += 1
                                        logger.debug(f"Retrieved file: {file_path}")
                                except Exception as e:
                                    logger.warning(f"Failed to get file {file_path}: {e}")
                        
                        elif item['type'] == 'dir' and files_processed < max_files:
                            # Recursively process subdirectories (limited depth)
                            if len(item['path'].split('/')) < 3:  # Limit recursion depth
                                await process_directory(item['path'])
            
            except Exception as e:
                logger.warning(f"Failed to process directory {path}: {e}")
        
        await process_directory()
        return file_contents
    
    async def _get_azure_devops_files(self, repository_url: str, max_files: int) -> Dict[str, str]:
        """Get Azure DevOps repository files using MCP"""
        if not self.azure_devops_client:
            return {}
        
        # Parse Azure DevOps URL
        import re
        match = re.match(r'https://dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/]+)/?', repository_url)
        if not match:
            match = re.match(r'https://([^.]+)\.visualstudio\.com/([^/]+)/_git/([^/]+)/?', repository_url)
            if not match:
                return {}
        
        org, project, repo = match.groups()
        
        file_contents = {}
        files_processed = 0
        
        try:
            # Get repository contents with full recursion
            contents = await self.azure_devops_client._get_repository_contents(
                project, repo, recursionLevel="Full"
            )
            
            for item in contents.get('value', []):
                if files_processed >= max_files:
                    break
                
                if not item.get('isFolder', True):  # It's a file
                    file_path = item.get('path', '').lstrip('/')
                    _, ext = os.path.splitext(file_path)
                    
                    if ext.lower() in self.code_extensions and item.get('size', 0) < self.max_code_length:
                        try:
                            file_content = await self.azure_devops_client._get_file_content(project, repo, file_path)
                            if 'content' in file_content:
                                file_contents[file_path] = file_content['content']
                                files_processed += 1
                                logger.debug(f"Retrieved file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to get file {file_path}: {e}")
        
        except Exception as e:
            logger.warning(f"Failed to get Azure DevOps files: {e}")
        
        return file_contents
    
    async def close_mcp_clients(self):
        """Close MCP client connections"""
        if self.azure_devops_client:
            await self.azure_devops_client.close()
        if self.github_mcp_client:
            await self.github_mcp_client.close()
    
    async def analyze_codebase(self, 
                              file_contents: Dict[str, str],
                              focus_files: Optional[List[str]] = None) -> Dict[str, CodeExplanation]:
        """
        Analyze multiple files concurrently using LLM
        
        Args:
            file_contents: Dictionary mapping file paths to their contents
            focus_files: Optional list of files to prioritize for analysis
            
        Returns:
            Dictionary mapping file paths to their explanations
        """

        # For Azure, credential is handled by DefaultAzureCredential
        if not self.client:
            logger.warning("OpenAI client not available, skipping LLM analysis")
            return {}
        
        logger.info(f"Starting LLM analysis of {len(file_contents)} files")
        
        # Filter files for analysis
        files_to_analyze = self._select_files_for_analysis(file_contents, focus_files)
        logger.info(f"Selected {len(files_to_analyze)} files for detailed LLM analysis")
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        # Analyze files concurrently
        tasks = []
        for file_path, content in files_to_analyze.items():
            task = self._analyze_single_file(semaphore, file_path, content)
            tasks.append(task)
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        explanations = {}
        for result in results:
            if isinstance(result, CodeExplanation):
                explanations[result.file_path] = result
            elif isinstance(result, Exception):
                logger.error(f"Error in LLM analysis: {result}")
        
        logger.info(f"Completed LLM analysis for {len(explanations)} files")
        return explanations
    
    def _select_files_for_analysis(self, 
                                  file_contents: Dict[str, str],
                                  focus_files: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Select most important files for LLM analysis
        
        Args:
            file_contents: All available file contents
            focus_files: Files to prioritize
            
        Returns:
            Filtered dictionary of files to analyze
        """
        selected = {}
        
        # Priority scoring for files
        def priority_score(file_path: str) -> int:
            path = Path(file_path)
            name = path.name.lower()
            ext = path.suffix.lower()
            content = file_contents.get(file_path, "")
            
            score = 0
            
            # High priority files
            if focus_files and file_path in focus_files:
                score += 1000
            
            # Main entry points
            if name in ['main.py', 'index.js', 'app.py', 'server.js', 'main.go', 'main.java']:
                score += 500
            
            # Core application files
            if any(core in name for core in ['app', 'application', 'core', 'engine', 'service']):
                score += 300
            
            # Configuration files with code
            if name in ['settings.py', 'config.js', 'webpack.config.js', 'babel.config.js']:
                score += 200
            
            # Important utilities
            if 'util' in name or 'helper' in name:
                score += 150
            
            # API/Route files
            if any(api in name for api in ['api', 'route', 'endpoint', 'controller']):
                score += 250
            
            # Model/Schema files
            if any(model in name for model in ['model', 'schema', 'entity']):
                score += 200
            
            # Test files (lower priority but still valuable)
            if 'test' in name or 'spec' in name:
                score += 100
            
            # Language-specific scoring
            if ext in self.code_extensions:
                score += 100
            
            # File size consideration (prefer medium-sized files)
            lines = len(content.split('\n'))
            if 20 <= lines <= 200:
                score += 50
            elif 200 < lines <= 500:
                score += 25
            elif lines > 500:
                score -= 25  # Very large files are harder to analyze
            
            # Complexity indicators (more complex = more valuable to explain)
            if any(keyword in content.lower() for keyword in [
                'class ', 'function ', 'def ', 'async ', 'await',
                'interface', 'abstract', 'extends', 'implements'
            ]):
                score += 75
            
            # Root level files get higher priority
            if len(path.parts) == 1:
                score += 100
            
            return score
        
        # Score and sort all files
        file_scores = []
        for file_path, content in file_contents.items():
            ext = Path(file_path).suffix.lower()
            
            # Skip non-code files
            if ext not in self.code_extensions:
                continue
            
            # Skip very large files
            if len(content) > self.max_code_length:
                logger.debug(f"Skipping large file for LLM analysis: {file_path}")
                continue
            
            score = priority_score(file_path)
            file_scores.append((file_path, content, score))
        
        # Sort by score and take top files
        file_scores.sort(key=lambda x: x[2], reverse=True)
        
        # Limit to reasonable number of files for LLM analysis
        max_files = get_int_from_env('MAX_FILES_FOR_LLM_ANALYSIS', 15)
        
        for file_path, content, score in file_scores[:max_files]:
            selected[file_path] = content
            logger.debug(f"Selected for LLM analysis: {file_path} (score: {score})")
        
        return selected
    
    async def _analyze_single_file(self, 
                                  semaphore: asyncio.Semaphore,
                                  file_path: str, 
                                  content: str) -> CodeExplanation:
        """
        Analyze a single file using LLM
        
        Args:
            semaphore: Concurrency control
            file_path: Path to the file
            content: File content
            
        Returns:
            Code explanation
        """
        async with semaphore:
            try:
                path = Path(file_path)
                language = self.code_extensions.get(path.suffix.lower(), 'Unknown')
                
                logger.debug(f"Analyzing {file_path} with LLM")
                
                # Create prompt for code analysis
                prompt = self._create_analysis_prompt(file_path, content, language)
                
                # Call LLM API
                response = await self._call_llm_api(prompt)
                
                # Parse response
                explanation = self._parse_llm_response(file_path, language, response)
                
                logger.debug(f"Completed LLM analysis for {file_path}")
                return explanation
                
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")
                # Return basic explanation on error
                return CodeExplanation(
                    file_path=file_path,
                    language=language,
                    summary="Analysis failed due to an error",
                    main_functionality="Could not determine",
                    key_components=[],
                    dependencies=[],
                    complexity_assessment="Unknown",
                    improvement_suggestions=[],
                    code_patterns=[]
                )
    
    def _create_analysis_prompt(self, file_path: str, content: str, language: str) -> str:
        """
        Create a detailed prompt for code analysis
        
        Args:
            file_path: Path to the file
            content: File content
            language: Programming language
            
        Returns:
            Formatted prompt for LLM
        """
        prompt = f"""
As an expert software engineer, analyze the following {language} code from the file `{file_path}` and provide a comprehensive explanation that would help a developer understand this code for the first time.

```{language.lower()}
{content}
```

Please provide your analysis in the following JSON format:

{{
    "summary": "Brief 2-3 sentence overview of what this file does",
    "main_functionality": "Detailed explanation of the primary purpose and functionality",
    "key_components": [
        "List of main classes, functions, or components and their purposes"
    ],
    "dependencies": [
        "External libraries, modules, or services this code depends on"
    ],
    "complexity_assessment": "Assessment of code complexity (Simple/Moderate/Complex/Very Complex) with brief reasoning",
    "improvement_suggestions": [
        "Specific suggestions for code improvement, best practices, or potential issues"
    ],
    "code_patterns": [
        "Design patterns, architectural patterns, or coding patterns used"
    ]
}}

Focus on:
1. What the code actually DOES (not just what it is)
2. How it fits into a larger application
3. Key algorithms or business logic
4. Important implementation details
5. Potential issues or areas for improvement
6. Architecture and design decisions

Be specific and technical, but explain in a way that helps understanding rather than just describing syntax.
"""
        return prompt
    
    async def _call_llm_api(self, prompt: str) -> str:
        """
        Call the OpenAI or Azure OpenAI API with the analysis prompt
        
        Args:
            prompt: The analysis prompt
            
        Returns:
            LLM response text
            
        Raises:
            Exception: If API call fails
        """

        if not self.client:
            raise Exception("OpenAI client not available. Check configuration.")
        

        try:
            # Use deployment_name for Azure, model for OpenAI
            model_to_use = self.deployment_name if self.use_azure else self.model
            response = await self.client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": "You are an expert software engineer who provides clear, detailed code analysis and explanations. Always respond with valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.1,
                timeout=60.0,
                tools=[]
            )
            return response.choices[0].message.content
        except Exception as e:
            provider = "Azure OpenAI" if self.use_azure else "OpenAI"
            logger.error(f"{provider} API call failed: {e}")
            raise Exception(f"LLM API error: {e}")
    
    def _parse_llm_response(self, 
                           file_path: str, 
                           language: str, 
                           response: str) -> CodeExplanation:
        """
        Parse LLM response into structured format
        
        Args:
            file_path: Path to the analyzed file
            language: Programming language
            response: LLM response text
            
        Returns:
            Structured code explanation
        """
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = response[json_start:json_end]
                parsed = json.loads(json_text)
                
                return CodeExplanation(
                    file_path=file_path,
                    language=language,
                    summary=parsed.get('summary', 'No summary provided'),
                    main_functionality=parsed.get('main_functionality', 'No functionality description provided'),
                    key_components=parsed.get('key_components', []),
                    dependencies=parsed.get('dependencies', []),
                    complexity_assessment=parsed.get('complexity_assessment', 'Unknown'),
                    improvement_suggestions=parsed.get('improvement_suggestions', []),
                    code_patterns=parsed.get('code_patterns', [])
                )
            else:
                # Fallback parsing if JSON is not found
                return self._fallback_parse(file_path, language, response)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON for {file_path}: {e}")
            return self._fallback_parse(file_path, language, response)
    
    def _fallback_parse(self, file_path: str, language: str, response: str) -> CodeExplanation:
        """
        Fallback parsing when JSON parsing fails
        
        Args:
            file_path: Path to the analyzed file
            language: Programming language  
            response: LLM response text
            
        Returns:
            Basic code explanation
        """
        # Extract what we can from free-form text
        lines = response.split('\n')
        summary = next((line.strip() for line in lines if line.strip() and not line.startswith('{')), "Analysis provided")
        
        return CodeExplanation(
            file_path=file_path,
            language=language,
            summary=summary[:200] + "..." if len(summary) > 200 else summary,
            main_functionality=response[:500] + "..." if len(response) > 500 else response,
            key_components=[],
            dependencies=[],
            complexity_assessment="Unknown",
            improvement_suggestions=[],
            code_patterns=[]
        )
    
    def generate_code_insights_summary(self, explanations: Dict[str, CodeExplanation]) -> Dict[str, Any]:
        """
        Generate high-level insights from all code explanations
        
        Args:
            explanations: Dictionary of file explanations
            
        Returns:
            Summary insights
        """
        try:
            if not explanations:
                return {
                    'total_files_analyzed': 0,
                    'complexity_distribution': {},
                    'common_patterns': [],
                    'key_technologies': [],
                    'improvement_themes': [],
                    'architecture_insights': []
                }
            
            logger.debug(f"Generating insights for {len(explanations)} explanations")
            
            # Analyze complexity distribution
            complexity_counts = {}
            for file_path, explanation in explanations.items():
                try:
                    if hasattr(explanation, 'complexity_assessment') and explanation.complexity_assessment:
                        complexity = explanation.complexity_assessment.split(' ')[0]  # Get first word
                        complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
                except Exception as e:
                    logger.warning(f"Error processing complexity for {file_path}: {e}")
                    continue
            
            # Find common patterns
            all_patterns = []
            for file_path, explanation in explanations.items():
                try:
                    if hasattr(explanation, 'code_patterns') and explanation.code_patterns:
                        # Ensure patterns are strings, not dictionaries
                        for pattern in explanation.code_patterns:
                            if isinstance(pattern, str):
                                all_patterns.append(pattern)
                            else:
                                logger.warning(f"Non-string pattern found in {file_path}: {type(pattern)}")
                except Exception as e:
                    logger.warning(f"Error processing patterns for {file_path}: {e}")
                    continue
            
            pattern_counts = {}
            for pattern in all_patterns:
                if isinstance(pattern, str):
                    pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            
            common_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Analyze dependencies/technologies
            all_dependencies = []
            for file_path, explanation in explanations.items():
                try:
                    if hasattr(explanation, 'dependencies') and explanation.dependencies:
                        # Ensure dependencies are strings, not dictionaries
                        for dep in explanation.dependencies:
                            if isinstance(dep, str):
                                all_dependencies.append(dep)
                            else:
                                logger.warning(f"Non-string dependency found in {file_path}: {type(dep)}")
                except Exception as e:
                    logger.warning(f"Error processing dependencies for {file_path}: {e}")
                    continue
            
            dependency_counts = {}
            for dep in all_dependencies:
                if isinstance(dep, str):
                    dependency_counts[dep] = dependency_counts.get(dep, 0) + 1
            
            key_technologies = sorted(dependency_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Common improvement themes
            all_improvements = []
            for file_path, explanation in explanations.items():
                try:
                    if hasattr(explanation, 'improvement_suggestions') and explanation.improvement_suggestions:
                        # Ensure improvements are strings, not dictionaries
                        for improvement in explanation.improvement_suggestions:
                            if isinstance(improvement, str):
                                all_improvements.append(improvement)
                            else:
                                logger.warning(f"Non-string improvement found in {file_path}: {type(improvement)}")
                except Exception as e:
                    logger.warning(f"Error processing improvements for {file_path}: {e}")
                    continue
            
            improvement_counts = {}
            for improvement in all_improvements:
                if isinstance(improvement, str):
                    # Simple keyword extraction for themes
                    if 'test' in improvement.lower():
                        improvement_counts['Testing'] = improvement_counts.get('Testing', 0) + 1
                    if 'error' in improvement.lower() or 'exception' in improvement.lower():
                        improvement_counts['Error Handling'] = improvement_counts.get('Error Handling', 0) + 1
                    if 'performance' in improvement.lower():
                        improvement_counts['Performance'] = improvement_counts.get('Performance', 0) + 1
                    if 'documentation' in improvement.lower() or 'comment' in improvement.lower():
                        improvement_counts['Documentation'] = improvement_counts.get('Documentation', 0) + 1
            
            result = {
                'total_files_analyzed': len(explanations),
                'complexity_distribution': complexity_counts,
                'common_patterns': [pattern for pattern, count in common_patterns],
                'key_technologies': [tech for tech, count in key_technologies],
                'improvement_themes': list(improvement_counts.keys()),
                'architecture_insights': []  # Could be enhanced with more analysis
            }
            
            logger.debug(f"Generated insights: {len(result['common_patterns'])} patterns, {len(result['key_technologies'])} technologies")
            return result
            
        except Exception as e:
            logger.error(f"Error generating code insights summary: {e}")
            return {
                'total_files_analyzed': 0,
                'complexity_distribution': {},
                'common_patterns': [],
                'key_technologies': [],
                'improvement_themes': [],
                'architecture_insights': [],
                'error': str(e)
            }


# Async wrapper for synchronous usage
def analyze_codebase_sync(llm_analyzer: LLMCodeAnalyzer, 
                         file_contents: Dict[str, str],
                         focus_files: Optional[List[str]] = None) -> Dict[str, CodeExplanation]:
    """
    Synchronous wrapper for async code analysis
    
    Args:
        llm_analyzer: LLM analyzer instance
        file_contents: Dictionary mapping file paths to contents
        focus_files: Optional list of files to prioritize
        
    Returns:
        Dictionary mapping file paths to explanations
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        llm_analyzer.analyze_codebase(file_contents, focus_files)
    )