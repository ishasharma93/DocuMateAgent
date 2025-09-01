"""
Code Analyzer

Analyzes code structure, dependencies, and patterns across different programming languages.
"""

import os
import re
import json
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
import logging
from collections import defaultdict, Counter

def get_int_from_env(env_var: str, default: int) -> int:
    """Get integer value from environment variable, handling comments"""
    value_str = os.getenv(env_var, str(default)).split('#')[0].strip()
    return int(value_str)

logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """Analyzes code structure and patterns"""
    
    # File extensions and their corresponding languages
    LANGUAGE_EXTENSIONS = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.jsx': 'React',
        '.tsx': 'React/TypeScript',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.h': 'C/C++ Header',
        '.hpp': 'C++ Header',
        '.cs': 'C#',
        '.go': 'Go',
        '.rs': 'Rust',
        '.php': 'PHP',
        '.rb': 'Ruby',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.r': 'R',
        '.m': 'Objective-C',
        '.mm': 'Objective-C++',
        '.sh': 'Shell',
        '.bash': 'Bash',
        '.ps1': 'PowerShell',
        '.sql': 'SQL',
        '.html': 'HTML',
        '.css': 'CSS',
        '.scss': 'SCSS',
        '.sass': 'Sass',
        '.less': 'Less',
        '.xml': 'XML',
        '.json': 'JSON',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.toml': 'TOML',
        '.ini': 'INI',
        '.cfg': 'Config',
        '.conf': 'Config',
        '.dockerfile': 'Dockerfile',
        '.md': 'Markdown',
        '.rst': 'reStructuredText',
        '.tex': 'LaTeX'
    }
    
    # Configuration files and their purposes
    CONFIG_FILES = {
        'package.json': 'Node.js dependencies',
        'requirements.txt': 'Python dependencies',
        'Pipfile': 'Python dependencies (pipenv)',
        'poetry.lock': 'Python dependencies (poetry)',
        'Cargo.toml': 'Rust dependencies',
        'go.mod': 'Go modules',
        'pom.xml': 'Java Maven dependencies',
        'build.gradle': 'Java Gradle dependencies',
        'Gemfile': 'Ruby dependencies',
        'composer.json': 'PHP dependencies',
        'pubspec.yaml': 'Dart/Flutter dependencies',
        'Package.swift': 'Swift dependencies',
        'setup.py': 'Python package setup',
        'setup.cfg': 'Python package configuration',
        'pyproject.toml': 'Python project configuration',
        'Dockerfile': 'Container configuration',
        'docker-compose.yml': 'Multi-container setup',
        'docker-compose.yaml': 'Multi-container setup',
        '.gitignore': 'Git ignore rules',
        '.dockerignore': 'Docker ignore rules',
        'Makefile': 'Build automation',
        'CMakeLists.txt': 'CMake build configuration',
        'webpack.config.js': 'Webpack configuration',
        'rollup.config.js': 'Rollup configuration',
        'vite.config.js': 'Vite configuration',
        'next.config.js': 'Next.js configuration',
        'nuxt.config.js': 'Nuxt.js configuration',
        'angular.json': 'Angular configuration',
        'vue.config.js': 'Vue.js configuration',
        'svelte.config.js': 'Svelte configuration',
        'tsconfig.json': 'TypeScript configuration',
        'jsconfig.json': 'JavaScript configuration',
        '.eslintrc.json': 'ESLint configuration',
        '.prettierrc': 'Prettier configuration',
        'tox.ini': 'Python testing configuration',
        'pytest.ini': 'Pytest configuration',
        'jest.config.js': 'Jest testing configuration',
        'cypress.json': 'Cypress testing configuration',
        '.travis.yml': 'Travis CI configuration',
        '.github/workflows': 'GitHub Actions',
        'action.yml': 'GitHub Action definition',
        'action.yaml': 'GitHub Action definition'
    }
    
    def __init__(self):
        # Handle environment variables that might have comments
        self.max_file_size = get_int_from_env('MAX_FILE_SIZE', 1048576)  # Default 1MB
        self.supported_extensions = set(self.LANGUAGE_EXTENSIONS.keys())
    
    def analyze_repository_structure(self, contents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the overall structure of the repository
        
        Args:
            contents: List of file/directory information from GitHub API
            
        Returns:
            Analysis results including structure, languages, and patterns
        """
        analysis = {
            'total_files': 0,
            'total_size': 0,
            'languages': defaultdict(int),
            'file_types': defaultdict(int),
            'directory_structure': defaultdict(list),
            'config_files': [],
            'documentation_files': [],
            'test_files': [],
            'build_files': [],
            'source_files': [],
            'largest_files': [],
            'file_distribution': {},
            'depth_analysis': defaultdict(int)
        }
        
        files_by_size = []
        
        for item in contents:
            if item['type'] == 'file':
                analysis['total_files'] += 1
                analysis['total_size'] += item.get('size', 0)
                
                file_path = Path(item['path'])
                extension = file_path.suffix.lower()
                
                # Language detection
                if extension in self.LANGUAGE_EXTENSIONS:
                    language = self.LANGUAGE_EXTENSIONS[extension]
                    analysis['languages'][language] += 1
                
                # File type categorization
                analysis['file_types'][extension or 'no_extension'] += 1
                
                # Directory structure
                directory = str(file_path.parent) if file_path.parent != Path('.') else 'root'
                analysis['directory_structure'][directory].append(file_path.name)
                
                # Special file categorization
                self._categorize_special_files(file_path.name, item['path'], analysis)
                
                # Track files by size for largest files analysis
                files_by_size.append((item['path'], item.get('size', 0)))
                
                # Depth analysis
                depth = len(file_path.parts) - 1
                analysis['depth_analysis'][depth] += 1
        
        # Get largest files (top 10)
        files_by_size.sort(key=lambda x: x[1], reverse=True)
        analysis['largest_files'] = files_by_size[:10]
        
        # File distribution by directory
        analysis['file_distribution'] = {
            dir_name: len(files) for dir_name, files in analysis['directory_structure'].items()
        }
        
        return dict(analysis)
    
    def _categorize_special_files(self, filename: str, filepath: str, analysis: Dict[str, Any]):
        """Categorize special files like configs, docs, tests, etc."""
        filename_lower = filename.lower()
        filepath_lower = filepath.lower()
        
        # Configuration files
        if filename in self.CONFIG_FILES or any(config in filename_lower for config in [
            'config', 'conf', '.env', 'settings', 'properties'
        ]):
            analysis['config_files'].append(filepath)
        
        # Documentation files
        if any(doc in filename_lower for doc in [
            'readme', 'changelog', 'license', 'contributing', 'code_of_conduct',
            'authors', 'contributors', 'install', 'usage', 'api', 'docs'
        ]) or filename.endswith(('.md', '.rst', '.txt', '.adoc')):
            analysis['documentation_files'].append(filepath)
        
        # Test files
        if any(test in filepath_lower for test in [
            'test', 'spec', '__tests__', 'tests', 'testing'
        ]) or any(test in filename_lower for test in [
            'test_', '_test', '.test.', '.spec.'
        ]):
            analysis['test_files'].append(filepath)
        
        # Build files
        if any(build in filename_lower for build in [
            'makefile', 'cmake', 'build', 'grunt', 'gulp', 'webpack',
            'rollup', 'vite', 'parcel', 'babel', 'eslint', 'prettier'
        ]) or filename.endswith(('.xml', '.gradle', '.sbt')):
            analysis['build_files'].append(filepath)
        
        # Source files (excluding tests and configs)
        if (filename.endswith(tuple(self.LANGUAGE_EXTENSIONS.keys())) and 
            'test' not in filepath_lower and 
            'config' not in filename_lower and
            not filename.startswith('.')):
            analysis['source_files'].append(filepath)
    
    def analyze_dependencies(self, file_contents: Dict[str, str]) -> Dict[str, Any]:
        """
        Analyze project dependencies from various configuration files
        
        Args:
            file_contents: Dictionary mapping file paths to their contents
            
        Returns:
            Dependency analysis results
        """
        dependencies = {
            'package_managers': [],
            'dependencies': defaultdict(list),
            'dev_dependencies': defaultdict(list),
            'frameworks': [],
            'build_tools': [],
            'testing_frameworks': [],
            'total_dependencies': 0
        }
        
        for file_path, content in file_contents.items():
            filename = Path(file_path).name
            
            try:
                if filename == 'package.json':
                    self._analyze_package_json(content, dependencies)
                elif filename == 'requirements.txt':
                    self._analyze_requirements_txt(content, dependencies)
                elif filename == 'Pipfile':
                    self._analyze_pipfile(content, dependencies)
                elif filename == 'pyproject.toml':
                    self._analyze_pyproject_toml(content, dependencies)
                elif filename == 'Cargo.toml':
                    self._analyze_cargo_toml(content, dependencies)
                elif filename == 'go.mod':
                    self._analyze_go_mod(content, dependencies)
                elif filename == 'pom.xml':
                    self._analyze_pom_xml(content, dependencies)
                elif filename == 'Gemfile':
                    self._analyze_gemfile(content, dependencies)
                elif filename == 'composer.json':
                    self._analyze_composer_json(content, dependencies)
                    
            except Exception as e:
                logger.warning(f"Error analyzing dependencies in {file_path}: {e}")
        
        # Calculate total dependencies
        dependencies['total_dependencies'] = sum(
            len(deps) for deps in dependencies['dependencies'].values()
        ) + sum(
            len(deps) for deps in dependencies['dev_dependencies'].values()
        )
        
        return dict(dependencies)
    
    def _analyze_package_json(self, content: str, dependencies: Dict[str, Any]):
        """Analyze Node.js package.json file"""
        try:
            data = json.loads(content)
            dependencies['package_managers'].append('npm')
            
            if 'dependencies' in data:
                dependencies['dependencies']['npm'].extend(list(data['dependencies'].keys()))
            
            if 'devDependencies' in data:
                dependencies['dev_dependencies']['npm'].extend(list(data['devDependencies'].keys()))
            
            # Identify frameworks and tools
            all_deps = []
            if 'dependencies' in data:
                all_deps.extend(data['dependencies'].keys())
            if 'devDependencies' in data:
                all_deps.extend(data['devDependencies'].keys())
            
            self._identify_frameworks(all_deps, dependencies)
            
        except json.JSONDecodeError:
            logger.warning("Invalid package.json format")
    
    def _analyze_requirements_txt(self, content: str, dependencies: Dict[str, Any]):
        """Analyze Python requirements.txt file"""
        dependencies['package_managers'].append('pip')
        
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # Extract package name (before ==, >=, etc.)
                package = re.split(r'[><=!]', line)[0].strip()
                if package:
                    dependencies['dependencies']['pip'].append(package)
    
    def _analyze_pipfile(self, content: str, dependencies: Dict[str, Any]):
        """Analyze Python Pipfile"""
        dependencies['package_managers'].append('pipenv')
        
        # Simple parsing - could be enhanced with proper TOML parser
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('[packages]'):
                current_section = 'packages'
            elif line.startswith('[dev-packages]'):
                current_section = 'dev-packages'
            elif line.startswith('['):
                current_section = None
            elif '=' in line and current_section:
                package = line.split('=')[0].strip().strip('"')
                if current_section == 'packages':
                    dependencies['dependencies']['pipenv'].append(package)
                elif current_section == 'dev-packages':
                    dependencies['dev_dependencies']['pipenv'].append(package)
    
    def _analyze_pyproject_toml(self, content: str, dependencies: Dict[str, Any]):
        """Analyze Python pyproject.toml file"""
        dependencies['package_managers'].append('poetry')
        # This would need proper TOML parsing for full implementation
        # For now, extract basic dependency information using regex
        
        dep_pattern = r'(\w+)\s*='
        matches = re.findall(dep_pattern, content)
        dependencies['dependencies']['poetry'].extend(matches)
    
    def _analyze_cargo_toml(self, content: str, dependencies: Dict[str, Any]):
        """Analyze Rust Cargo.toml file"""
        dependencies['package_managers'].append('cargo')
        # Similar approach as pyproject.toml - would need proper TOML parsing
        pass
    
    def _analyze_go_mod(self, content: str, dependencies: Dict[str, Any]):
        """Analyze Go go.mod file"""
        dependencies['package_managers'].append('go modules')
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('require '):
                # Extract module name
                parts = line.split()
                if len(parts) >= 2:
                    module = parts[1]
                    dependencies['dependencies']['go'].append(module)
    
    def _analyze_pom_xml(self, content: str, dependencies: Dict[str, Any]):
        """Analyze Java Maven pom.xml file"""
        dependencies['package_managers'].append('maven')
        
        # Extract artifact IDs using regex (simplified)
        artifact_pattern = r'<artifactId>([^<]+)</artifactId>'
        matches = re.findall(artifact_pattern, content)
        dependencies['dependencies']['maven'].extend(matches)
    
    def _analyze_gemfile(self, content: str, dependencies: Dict[str, Any]):
        """Analyze Ruby Gemfile"""
        dependencies['package_managers'].append('bundler')
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('gem '):
                # Extract gem name
                match = re.search(r"gem\s+['\"]([^'\"]+)['\"]", line)
                if match:
                    dependencies['dependencies']['bundler'].append(match.group(1))
    
    def _analyze_composer_json(self, content: str, dependencies: Dict[str, Any]):
        """Analyze PHP composer.json file"""
        try:
            data = json.loads(content)
            dependencies['package_managers'].append('composer')
            
            if 'require' in data:
                dependencies['dependencies']['composer'].extend(list(data['require'].keys()))
            
            if 'require-dev' in data:
                dependencies['dev_dependencies']['composer'].extend(list(data['require-dev'].keys()))
                
        except json.JSONDecodeError:
            logger.warning("Invalid composer.json format")
    
    def _identify_frameworks(self, package_list: List[str], dependencies: Dict[str, Any]):
        """Identify frameworks and tools from package names"""
        framework_patterns = {
            'React': ['react', '@types/react'],
            'Vue.js': ['vue', '@vue/'],
            'Angular': ['@angular/', 'angular'],
            'Express.js': ['express'],
            'Next.js': ['next'],
            'Nuxt.js': ['nuxt'],
            'Svelte': ['svelte'],
            'Django': ['django'],
            'Flask': ['flask'],
            'FastAPI': ['fastapi'],
            'Spring': ['spring'],
            'Rails': ['rails'],
            'Laravel': ['laravel']
        }
        
        testing_patterns = {
            'Jest': ['jest'],
            'Mocha': ['mocha'],
            'Chai': ['chai'],
            'Cypress': ['cypress'],
            'Puppeteer': ['puppeteer'],
            'Playwright': ['playwright'],
            'pytest': ['pytest'],
            'unittest': ['unittest'],
            'JUnit': ['junit']
        }
        
        build_tool_patterns = {
            'Webpack': ['webpack'],
            'Rollup': ['rollup'],
            'Vite': ['vite'],
            'Parcel': ['parcel'],
            'Babel': ['@babel/', 'babel'],
            'ESLint': ['eslint'],
            'Prettier': ['prettier'],
            'TypeScript': ['typescript']
        }
        
        for package in package_list:
            package_lower = package.lower()
            
            # Check frameworks
            for framework, patterns in framework_patterns.items():
                if any(pattern.lower() in package_lower for pattern in patterns):
                    if framework not in dependencies['frameworks']:
                        dependencies['frameworks'].append(framework)
            
            # Check testing frameworks
            for tool, patterns in testing_patterns.items():
                if any(pattern.lower() in package_lower for pattern in patterns):
                    if tool not in dependencies['testing_frameworks']:
                        dependencies['testing_frameworks'].append(tool)
            
            # Check build tools
            for tool, patterns in build_tool_patterns.items():
                if any(pattern.lower() in package_lower for pattern in patterns):
                    if tool not in dependencies['build_tools']:
                        dependencies['build_tools'].append(tool)
    
    def analyze_code_metrics(self, file_contents: Dict[str, str]) -> Dict[str, Any]:
        """
        Analyze code metrics like lines of code, complexity, etc.
        
        Args:
            file_contents: Dictionary mapping file paths to their contents
            
        Returns:
            Code metrics analysis
        """
        metrics = {
            'total_lines': 0,
            'code_lines': 0,
            'comment_lines': 0,
            'blank_lines': 0,
            'files_analyzed': 0,
            'languages': defaultdict(lambda: {
                'files': 0,
                'lines': 0,
                'code_lines': 0,
                'comment_lines': 0
            }),
            'complexity_indicators': {
                'large_files': [],  # Files > 500 lines
                'deeply_nested': [],  # Files with high indentation
                'long_functions': []  # Functions/methods > 50 lines
            }
        }
        
        for file_path, content in file_contents.items():
            if not content:
                continue
                
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in self.LANGUAGE_EXTENSIONS:
                continue
            
            language = self.LANGUAGE_EXTENSIONS[file_ext]
            lines = content.split('\n')
            
            metrics['files_analyzed'] += 1
            metrics['languages'][language]['files'] += 1
            
            file_metrics = self._analyze_file_metrics(lines, language)
            
            # Update totals
            metrics['total_lines'] += len(lines)
            metrics['code_lines'] += file_metrics['code_lines']
            metrics['comment_lines'] += file_metrics['comment_lines']
            metrics['blank_lines'] += file_metrics['blank_lines']
            
            # Update language-specific metrics
            metrics['languages'][language]['lines'] += len(lines)
            metrics['languages'][language]['code_lines'] += file_metrics['code_lines']
            metrics['languages'][language]['comment_lines'] += file_metrics['comment_lines']
            
            # Check complexity indicators
            if len(lines) > 500:
                metrics['complexity_indicators']['large_files'].append({
                    'file': file_path,
                    'lines': len(lines)
                })
            
            if file_metrics['max_indentation'] > 6:
                metrics['complexity_indicators']['deeply_nested'].append({
                    'file': file_path,
                    'max_indentation': file_metrics['max_indentation']
                })
        
        return dict(metrics)
    
    def _analyze_file_metrics(self, lines: List[str], language: str) -> Dict[str, Any]:
        """Analyze metrics for a single file"""
        metrics = {
            'code_lines': 0,
            'comment_lines': 0,
            'blank_lines': 0,
            'max_indentation': 0
        }
        
        comment_patterns = {
            'Python': [r'^\s*#', r'^\s*"""', r"^\s*'''"],
            'JavaScript': [r'^\s*//', r'^\s*/\*', r'^\s*\*'],
            'TypeScript': [r'^\s*//', r'^\s*/\*', r'^\s*\*'],
            'Java': [r'^\s*//', r'^\s*/\*', r'^\s*\*'],
            'C++': [r'^\s*//', r'^\s*/\*', r'^\s*\*'],
            'C': [r'^\s*//', r'^\s*/\*', r'^\s*\*'],
            'Go': [r'^\s*//', r'^\s*/\*', r'^\s*\*'],
            'Rust': [r'^\s*//', r'^\s*/\*', r'^\s*\*'],
            'Ruby': [r'^\s*#'],
            'PHP': [r'^\s*//', r'^\s*/\*', r'^\s*\*', r'^\s*#'],
            'Shell': [r'^\s*#'],
            'Bash': [r'^\s*#'],
            'PowerShell': [r'^\s*#'],
            'HTML': [r'^\s*<!--'],
            'CSS': [r'^\s*/\*', r'^\s*\*']
        }
        
        patterns = comment_patterns.get(language, [r'^\s*#', r'^\s*//'])
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                metrics['blank_lines'] += 1
            elif any(re.match(pattern, line) for pattern in patterns):
                metrics['comment_lines'] += 1
            else:
                metrics['code_lines'] += 1
            
            # Calculate indentation level
            if stripped:
                indentation = len(line) - len(line.lstrip())
                if language == 'Python':
                    indentation_level = indentation // 4  # Assuming 4-space indentation
                else:
                    indentation_level = indentation // 2  # Assuming 2-space indentation
                
                metrics['max_indentation'] = max(metrics['max_indentation'], indentation_level)
        
        return metrics
    
    def detect_project_patterns(self, file_structure: List[str], file_contents: Dict[str, str]) -> Dict[str, Any]:
        """
        Detect common project patterns and architectures
        
        Args:
            file_structure: List of file paths in the repository
            file_contents: Dictionary mapping file paths to their contents
            
        Returns:
            Detected patterns and architecture information
        """
        patterns = {
            'project_type': 'Unknown',
            'architecture_patterns': [],
            'frameworks': [],
            'build_tools': [],
            'deployment_platforms': [],
            'testing_strategy': [],
            'code_organization': [],
            'api_type': None,
            'database_technologies': [],
            'frontend_technologies': [],
            'backend_technologies': [],
            'mobile_technologies': [],
            'cloud_services': []
        }
        
        # Analyze file structure for patterns
        file_paths = [Path(f) for f in file_structure]
        
        # Detect project type based on key files and structure
        patterns['project_type'] = self._detect_project_type(file_paths, file_contents)
        
        # Detect architecture patterns
        patterns['architecture_patterns'] = self._detect_architecture_patterns(file_paths, file_contents)
        
        # Detect API type
        patterns['api_type'] = self._detect_api_type(file_contents)
        
        # Detect technologies
        patterns.update(self._detect_technologies(file_contents))
        
        return patterns
    
    def _detect_project_type(self, file_paths: List[Path], file_contents: Dict[str, str]) -> str:
        """Detect the primary project type"""
        filenames = [p.name for p in file_paths]
        
        # Web application indicators
        if 'package.json' in filenames:
            package_json = file_contents.get('package.json', '')
            if any(framework in package_json.lower() for framework in ['react', 'vue', 'angular']):
                return 'Frontend Web Application'
            elif any(backend in package_json.lower() for backend in ['express', 'koa', 'fastify']):
                return 'Backend Web Application'
            else:
                return 'Node.js Application'
        
        # Python project indicators
        if any(f in filenames for f in ['requirements.txt', 'pyproject.toml', 'setup.py']):
            if any('django' in content.lower() for content in file_contents.values()):
                return 'Django Web Application'
            elif any('flask' in content.lower() for content in file_contents.values()):
                return 'Flask Web Application'
            elif any('fastapi' in content.lower() for content in file_contents.values()):
                return 'FastAPI Application'
            else:
                return 'Python Application'
        
        # Mobile app indicators
        if any(f in filenames for f in ['pubspec.yaml', 'android', 'ios']):
            return 'Mobile Application'
        
        # Java project indicators
        if any(f in filenames for f in ['pom.xml', 'build.gradle']):
            return 'Java Application'
        
        # Other indicators
        if 'Cargo.toml' in filenames:
            return 'Rust Application'
        if 'go.mod' in filenames:
            return 'Go Application'
        if 'Gemfile' in filenames:
            return 'Ruby Application'
        if 'composer.json' in filenames:
            return 'PHP Application'
        
        # Docker/Container project
        if any(f in filenames for f in ['Dockerfile', 'docker-compose.yml']):
            return 'Containerized Application'
        
        # Documentation/Static site
        if any(p.suffix in ['.md', '.rst'] for p in file_paths) and len([p for p in file_paths if p.suffix in ['.py', '.js', '.java']]) < 5:
            return 'Documentation/Static Site'
        
        return 'Unknown'
    
    def _detect_architecture_patterns(self, file_paths: List[Path], file_contents: Dict[str, str]) -> List[str]:
        """Detect architecture patterns"""
        patterns = []
        
        # Check for common directory patterns
        directories = set(p.parent.name for p in file_paths if p.parent.name != '.')
        
        # MVC pattern
        if any(d in directories for d in ['models', 'views', 'controllers']):
            patterns.append('MVC (Model-View-Controller)')
        
        # Microservices
        if any(d in directories for d in ['services', 'microservices']) or 'docker-compose.yml' in [p.name for p in file_paths]:
            patterns.append('Microservices')
        
        # Clean Architecture / Hexagonal
        if any(d in directories for d in ['domain', 'infrastructure', 'application', 'adapters']):
            patterns.append('Clean Architecture')
        
        # Component-based (React/Vue)
        if any(d in directories for d in ['components', 'containers']):
            patterns.append('Component-Based Architecture')
        
        # API-first
        if any(f in [p.name for p in file_paths] for f in ['openapi.yaml', 'swagger.yaml', 'api.yaml']):
            patterns.append('API-First Design')
        
        # Event-driven
        if any(content for content in file_contents.values() if any(keyword in content.lower() for keyword in ['event', 'queue', 'pubsub', 'kafka'])):
            patterns.append('Event-Driven Architecture')
        
        return patterns
    
    def _detect_api_type(self, file_contents: Dict[str, str]) -> Optional[str]:
        """Detect API type"""
        all_content = ' '.join(file_contents.values()).lower()
        
        if 'graphql' in all_content:
            return 'GraphQL'
        elif any(keyword in all_content for keyword in ['rest', 'api', 'endpoint', 'router']):
            return 'REST API'
        elif 'grpc' in all_content:
            return 'gRPC'
        elif 'websocket' in all_content:
            return 'WebSocket API'
        
        return None
    
    def _detect_technologies(self, file_contents: Dict[str, str]) -> Dict[str, List[str]]:
        """Detect various technologies used in the project"""
        all_content = ' '.join(file_contents.values()).lower()
        
        frontend_tech = []
        backend_tech = []
        database_tech = []
        cloud_services = []
        mobile_tech = []
        
        # Frontend technologies
        frontend_patterns = {
            'React': ['react', 'jsx'],
            'Vue.js': ['vue'],
            'Angular': ['angular', '@angular'],
            'Svelte': ['svelte'],
            'jQuery': ['jquery'],
            'Bootstrap': ['bootstrap'],
            'Tailwind CSS': ['tailwind'],
            'Material-UI': ['material-ui', '@mui'],
            'Styled Components': ['styled-components']
        }
        
        # Backend technologies
        backend_patterns = {
            'Express.js': ['express'],
            'Django': ['django'],
            'Flask': ['flask'],
            'FastAPI': ['fastapi'],
            'Spring Boot': ['spring-boot', 'springframework'],
            'Rails': ['rails'],
            'Laravel': ['laravel'],
            'ASP.NET': ['asp.net', 'aspnet']
        }
        
        # Database technologies
        database_patterns = {
            'PostgreSQL': ['postgresql', 'postgres', 'psycopg'],
            'MySQL': ['mysql'],
            'MongoDB': ['mongodb', 'mongoose'],
            'Redis': ['redis'],
            'SQLite': ['sqlite'],
            'Elasticsearch': ['elasticsearch'],
            'Cassandra': ['cassandra'],
            'DynamoDB': ['dynamodb']
        }
        
        # Cloud services
        cloud_patterns = {
            'AWS': ['aws', 'boto3', 'lambda', 's3', 'ec2'],
            'Google Cloud': ['gcp', 'google-cloud'],
            'Azure': ['azure', 'microsoft'],
            'Heroku': ['heroku'],
            'Vercel': ['vercel'],
            'Netlify': ['netlify'],
            'Docker': ['docker', 'dockerfile'],
            'Kubernetes': ['kubernetes', 'k8s']
        }
        
        # Mobile technologies
        mobile_patterns = {
            'React Native': ['react-native'],
            'Flutter': ['flutter', 'dart'],
            'Ionic': ['ionic'],
            'Xamarin': ['xamarin'],
            'Cordova': ['cordova'],
            'Swift': ['swift'],
            'Kotlin': ['kotlin']
        }
        
        # Check patterns
        for tech, patterns in frontend_patterns.items():
            if any(pattern in all_content for pattern in patterns):
                frontend_tech.append(tech)
        
        for tech, patterns in backend_patterns.items():
            if any(pattern in all_content for pattern in patterns):
                backend_tech.append(tech)
        
        for tech, patterns in database_patterns.items():
            if any(pattern in all_content for pattern in patterns):
                database_tech.append(tech)
        
        for tech, patterns in cloud_patterns.items():
            if any(pattern in all_content for pattern in patterns):
                cloud_services.append(tech)
        
        for tech, patterns in mobile_patterns.items():
            if any(pattern in all_content for pattern in patterns):
                mobile_tech.append(tech)
        
        return {
            'frontend_technologies': frontend_tech,
            'backend_technologies': backend_tech,
            'database_technologies': database_tech,
            'cloud_services': cloud_services,
            'mobile_technologies': mobile_tech
        }
