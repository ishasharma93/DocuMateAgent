"""
Markdown Generator

Generates comprehensive markdown summary documents from repository analysis data.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MarkdownGenerator:
    """Generates markdown summary reports from analysis data"""
    
    def __init__(self):
        self.template_sections = [
            'header',
            'overview',
            'project_structure',
            'technology_stack',
            'dependencies',
            'code_metrics',
            'architecture',
            'documentation',
            'development_workflow',
            'recommendations',
            'footer'
        ]
    
    def generate_summary(self, 
                        repo_info: Dict[str, Any],
                        structure_analysis: Dict[str, Any],
                        dependency_analysis: Dict[str, Any],
                        code_metrics: Dict[str, Any],
                        pattern_analysis: Dict[str, Any],
                        file_contents: Dict[str, str],
                        llm_analysis: Dict[str, Any] = None,
                        code_insights: Dict[str, Any] = None) -> str:
        """
        Generate a comprehensive markdown summary
        
        Args:
            repo_info: Repository metadata from GitHub API
            structure_analysis: Repository structure analysis
            dependency_analysis: Dependency analysis results
            code_metrics: Code metrics and statistics
            pattern_analysis: Architecture and pattern detection
            file_contents: Sample file contents for context
            llm_analysis: LLM-powered code explanations
            code_insights: High-level insights from LLM analysis
            
        Returns:
            Complete markdown summary document
        """
        sections = []
        
        # Generate each section
        sections.append(self._generate_header(repo_info))
        sections.append(self._generate_overview(repo_info, pattern_analysis))
        sections.append(self._generate_project_structure(structure_analysis))
        sections.append(self._generate_technology_stack(pattern_analysis, dependency_analysis))
        sections.append(self._generate_dependencies(dependency_analysis))
        sections.append(self._generate_code_metrics(code_metrics))
        sections.append(self._generate_architecture(pattern_analysis))
        
        # Add LLM-powered code analysis section
        if llm_analysis and any(llm_analysis.values()):
            sections.append(self._generate_code_analysis_section(llm_analysis, code_insights))
        
        sections.append(self._generate_documentation_quality(structure_analysis))
        sections.append(self._generate_development_workflow(structure_analysis, repo_info))
        sections.append(self._generate_recommendations(structure_analysis, code_metrics, pattern_analysis, llm_analysis))
        sections.append(self._generate_footer())
        
        return '\n\n'.join(sections)
    
    def _generate_header(self, repo_info: Dict[str, Any]) -> str:
        """Generate document header with repository information"""
        title = repo_info.get('name', 'Unknown Repository')
        description = repo_info.get('description', 'No description available')
        url = repo_info.get('url', '')
        
        header = f"""# 📊 Repository Analysis: {title}

> {description}

**Repository URL:** {url}  
**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Primary Language:** {repo_info.get('language', 'Not specified')}  

---

## 📋 Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Dependencies](#dependencies)
- [Code Metrics](#code-metrics)
- [Architecture & Patterns](#architecture--patterns)
- [Code Analysis & Explanations](#code-analysis--explanations)
- [Documentation Quality](#documentation-quality)
- [Development Workflow](#development-workflow)
- [Recommendations](#recommendations)

---"""
        
        return header
    
    def _generate_overview(self, repo_info: Dict[str, Any], pattern_analysis: Dict[str, Any]) -> str:
        """Generate repository overview section"""
        stars = repo_info.get('stars', 0)
        forks = repo_info.get('forks', 0)
        size = repo_info.get('size', 0)
        created = repo_info.get('created_at', 'Unknown')
        updated = repo_info.get('updated_at', 'Unknown')
        project_type = pattern_analysis.get('project_type', 'Unknown')
        
        # Format dates
        if created != 'Unknown':
            created = created.strftime('%Y-%m-%d') if hasattr(created, 'strftime') else str(created)
        if updated != 'Unknown':
            updated = updated.strftime('%Y-%m-%d') if hasattr(updated, 'strftime') else str(updated)
        
        overview = f"""## 🌟 Overview

### Repository Statistics
- **⭐ Stars:** {stars:,}
- **🍴 Forks:** {forks:,}
- **📦 Size:** {size:,} KB
- **📅 Created:** {created}
- **🔄 Last Updated:** {updated}
- **🏷️ Project Type:** {project_type}

### Quick Summary
This repository appears to be a **{project_type.lower()}** with the following characteristics:

"""
        
        # Add key characteristics
        languages = repo_info.get('languages', {})
        if languages:
            overview += "**Primary Languages:**\n"
            for lang, bytes_count in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]:
                percentage = (bytes_count / sum(languages.values())) * 100
                overview += f"- {lang}: {percentage:.1f}%\n"
            overview += "\n"
        
        # Add topics if available
        topics = repo_info.get('topics', [])
        if topics:
            overview += f"**Topics:** {', '.join(topics)}\n\n"
        
        # Add license information
        license_name = repo_info.get('license')
        if license_name:
            overview += f"**License:** {license_name}\n\n"
        
        return overview
    
    def _generate_project_structure(self, structure_analysis: Dict[str, Any]) -> str:
        """Generate project structure section"""
        total_files = structure_analysis.get('total_files', 0)
        total_size = structure_analysis.get('total_size', 0)
        languages = structure_analysis.get('languages', {})
        
        structure = f"""## 📁 Project Structure

### File Statistics
- **Total Files:** {total_files:,}
- **Total Size:** {self._format_size(total_size)}
- **Language Distribution:**

"""
        
        # Language distribution
        if languages:
            total_lang_files = sum(languages.values())
            for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_lang_files) * 100
                bar = self._create_progress_bar(percentage)
                structure += f"  - **{lang}:** {count} files ({percentage:.1f}%) {bar}\n"
        
        structure += "\n### Directory Structure\n\n"
        
        # Directory breakdown
        file_distribution = structure_analysis.get('file_distribution', {})
        if file_distribution:
            structure += "| Directory | File Count |\n|-----------|------------|\n"
            for directory, count in sorted(file_distribution.items(), key=lambda x: x[1], reverse=True)[:10]:
                dir_name = directory if directory != 'root' else '📁 Root'
                structure += f"| {dir_name} | {count} |\n"
        
        # Special files breakdown
        structure += "\n### File Categories\n\n"
        
        categories = [
            ('📄 Source Files', structure_analysis.get('source_files', [])),
            ('🧪 Test Files', structure_analysis.get('test_files', [])),
            ('⚙️ Configuration Files', structure_analysis.get('config_files', [])),
            ('📚 Documentation Files', structure_analysis.get('documentation_files', [])),
            ('🔨 Build Files', structure_analysis.get('build_files', []))
        ]
        
        for category_name, files in categories:
            count = len(files)
            if count > 0:
                structure += f"- **{category_name}:** {count} files\n"
        
        # Largest files
        largest_files = structure_analysis.get('largest_files', [])
        if largest_files:
            structure += "\n### Largest Files\n\n"
            structure += "| File | Size |\n|------|------|\n"
            for file_path, size in largest_files[:5]:
                structure += f"| `{file_path}` | {self._format_size(size)} |\n"
        
        return structure
    
    def _generate_technology_stack(self, pattern_analysis: Dict[str, Any], dependency_analysis: Dict[str, Any]) -> str:
        """Generate technology stack section"""
        tech_stack = """## 🛠️ Technology Stack

"""
        
        # Project type and architecture
        project_type = pattern_analysis.get('project_type', 'Unknown')
        tech_stack += f"**Project Type:** {project_type}\n\n"
        
        # Technologies by category
        categories = [
            ('🎨 Frontend Technologies', pattern_analysis.get('frontend_technologies', [])),
            ('⚙️ Backend Technologies', pattern_analysis.get('backend_technologies', [])),
            ('🗄️ Database Technologies', pattern_analysis.get('database_technologies', [])),
            ('📱 Mobile Technologies', pattern_analysis.get('mobile_technologies', [])),
            ('☁️ Cloud Services', pattern_analysis.get('cloud_services', []))
        ]
        
        for category_name, technologies in categories:
            if technologies:
                tech_stack += f"### {category_name}\n\n"
                for tech in technologies:
                    tech_stack += f"- {tech}\n"
                tech_stack += "\n"
        
        # Package managers
        package_managers = dependency_analysis.get('package_managers', [])
        if package_managers:
            tech_stack += "### 📦 Package Managers\n\n"
            for pm in package_managers:
                tech_stack += f"- {pm}\n"
            tech_stack += "\n"
        
        # Build tools and frameworks
        frameworks = dependency_analysis.get('frameworks', [])
        build_tools = dependency_analysis.get('build_tools', [])
        testing_frameworks = dependency_analysis.get('testing_frameworks', [])
        
        if frameworks or build_tools or testing_frameworks:
            tech_stack += "### 🔧 Development Tools\n\n"
            
            if frameworks:
                tech_stack += "**Frameworks:**\n"
                for framework in frameworks:
                    tech_stack += f"- {framework}\n"
                tech_stack += "\n"
            
            if build_tools:
                tech_stack += "**Build Tools:**\n"
                for tool in build_tools:
                    tech_stack += f"- {tool}\n"
                tech_stack += "\n"
            
            if testing_frameworks:
                tech_stack += "**Testing Frameworks:**\n"
                for framework in testing_frameworks:
                    tech_stack += f"- {framework}\n"
                tech_stack += "\n"
        
        return tech_stack
    
    def _generate_dependencies(self, dependency_analysis: Dict[str, Any]) -> str:
        """Generate dependencies section"""
        total_deps = dependency_analysis.get('total_dependencies', 0)
        
        deps_section = f"""## 📦 Dependencies

**Total Dependencies:** {total_deps}

"""
        
        # Dependencies by package manager
        dependencies = dependency_analysis.get('dependencies', {})
        dev_dependencies = dependency_analysis.get('dev_dependencies', {})
        
        if dependencies or dev_dependencies:
            deps_section += "### Production Dependencies\n\n"
            
            for package_manager, deps in dependencies.items():
                if deps:
                    deps_section += f"**{package_manager.title()}** ({len(deps)} packages):\n"
                    # Show top dependencies
                    for dep in deps[:10]:  # Limit to top 10
                        deps_section += f"- `{dep}`\n"
                    if len(deps) > 10:
                        deps_section += f"- ... and {len(deps) - 10} more\n"
                    deps_section += "\n"
            
            if dev_dependencies:
                deps_section += "### Development Dependencies\n\n"
                
                for package_manager, deps in dev_dependencies.items():
                    if deps:
                        deps_section += f"**{package_manager.title()}** ({len(deps)} packages):\n"
                        for dep in deps[:5]:  # Show fewer dev deps
                            deps_section += f"- `{dep}`\n"
                        if len(deps) > 5:
                            deps_section += f"- ... and {len(deps) - 5} more\n"
                        deps_section += "\n"
        
        return deps_section
    
    def _generate_code_metrics(self, code_metrics: Dict[str, Any]) -> str:
        """Generate code metrics section"""
        total_lines = code_metrics.get('total_lines', 0)
        code_lines = code_metrics.get('code_lines', 0)
        comment_lines = code_metrics.get('comment_lines', 0)
        blank_lines = code_metrics.get('blank_lines', 0)
        files_analyzed = code_metrics.get('files_analyzed', 0)
        
        metrics = f"""## 📊 Code Metrics

### Lines of Code Analysis
- **Total Lines:** {total_lines:,}
- **Code Lines:** {code_lines:,} ({self._percentage(code_lines, total_lines):.1f}%)
- **Comment Lines:** {comment_lines:,} ({self._percentage(comment_lines, total_lines):.1f}%)
- **Blank Lines:** {blank_lines:,} ({self._percentage(blank_lines, total_lines):.1f}%)
- **Files Analyzed:** {files_analyzed:,}

### Code Distribution by Language

"""
        
        # Language-specific metrics
        languages = code_metrics.get('languages', {})
        if languages:
            metrics += "| Language | Files | Lines | Code | Comments |\n"
            metrics += "|----------|-------|-------|------|----------|\n"
            
            for lang, lang_metrics in sorted(languages.items(), key=lambda x: x[1]['lines'], reverse=True):
                files = lang_metrics.get('files', 0)
                lines = lang_metrics.get('lines', 0)
                code = lang_metrics.get('code_lines', 0)
                comments = lang_metrics.get('comment_lines', 0)
                
                metrics += f"| {lang} | {files} | {lines:,} | {code:,} | {comments:,} |\n"
        
        # Complexity indicators
        complexity = code_metrics.get('complexity_indicators', {})
        if any(complexity.values()):
            metrics += "\n### Complexity Indicators\n\n"
            
            large_files = complexity.get('large_files', [])
            if large_files:
                metrics += f"**Large Files (>500 lines):** {len(large_files)}\n"
                for file_info in large_files[:3]:  # Show top 3
                    metrics += f"- `{file_info['file']}` ({file_info['lines']} lines)\n"
                if len(large_files) > 3:
                    metrics += f"- ... and {len(large_files) - 3} more\n"
                metrics += "\n"
            
            deeply_nested = complexity.get('deeply_nested', [])
            if deeply_nested:
                metrics += f"**Deeply Nested Files (>6 levels):** {len(deeply_nested)}\n"
                for file_info in deeply_nested[:3]:
                    metrics += f"- `{file_info['file']}` (max depth: {file_info['max_indentation']})\n"
                if len(deeply_nested) > 3:
                    metrics += f"- ... and {len(deeply_nested) - 3} more\n"
                metrics += "\n"
        
        return metrics
    
    def _generate_architecture(self, pattern_analysis: Dict[str, Any]) -> str:
        """Generate architecture and patterns section"""
        architecture = """## 🏗️ Architecture & Patterns

"""
        
        # Architecture patterns
        arch_patterns = pattern_analysis.get('architecture_patterns', [])
        if arch_patterns:
            architecture += "### Detected Architecture Patterns\n\n"
            for pattern in arch_patterns:
                architecture += f"- **{pattern}**\n"
            architecture += "\n"
        
        # API type
        api_type = pattern_analysis.get('api_type')
        if api_type:
            architecture += f"### API Architecture\n\n**Type:** {api_type}\n\n"
        
        # Design patterns or recommendations
        if not arch_patterns and not api_type:
            architecture += "### Architecture Analysis\n\n"
            architecture += "No specific architecture patterns were automatically detected. "
            architecture += "This could indicate:\n"
            architecture += "- A simple or straightforward project structure\n"
            architecture += "- Custom architecture not matching common patterns\n"
            architecture += "- Early stage of development\n\n"
        
        return architecture
    
    def _generate_code_analysis_section(self, 
                                      llm_analysis: Dict[str, Any], 
                                      code_insights: Dict[str, Any]) -> str:
        """Generate detailed code analysis section from LLM results"""
        section = """## 🔍 Code Analysis & Explanations

*This section provides AI-powered analysis of the most important code files, explaining their functionality and purpose.*

"""
        
        if not llm_analysis:
            section += "No detailed code analysis available.\n"
            return section
        
        # Overview insights
        if code_insights:
            section += "### 📊 Code Analysis Overview\n\n"
            
            total_analyzed = code_insights.get('total_files_analyzed', 0)
            section += f"**Files Analyzed:** {total_analyzed}\n\n"
            
            # Complexity distribution
            complexity_dist = code_insights.get('complexity_distribution', {})
            if complexity_dist:
                section += "**Complexity Distribution:**\n"
                for complexity, count in complexity_dist.items():
                    section += f"- {complexity}: {count} files\n"
                section += "\n"
            
            # Common patterns
            common_patterns = code_insights.get('common_patterns', [])
            if common_patterns:
                section += "**Common Design Patterns:**\n"
                for pattern in common_patterns[:5]:
                    section += f"- {pattern}\n"
                section += "\n"
            
            # Key technologies identified by LLM
            key_technologies = code_insights.get('key_technologies', [])
            if key_technologies:
                section += "**Key Technologies (AI-Identified):**\n"
                for tech in key_technologies[:8]:
                    section += f"- {tech}\n"
                section += "\n"
        
        # Individual file analyses
        section += "### 📁 Detailed File Analysis\n\n"
        
        # Sort files by importance (main files first)
        sorted_files = sorted(llm_analysis.items(), key=lambda x: self._file_importance_score(x[0]))
        
        for file_path, explanation in sorted_files:
            section += f"#### `{file_path}`\n\n"
            section += f"**Language:** {explanation.language}  \n"
            section += f"**Complexity:** {explanation.complexity_assessment}\n\n"
            
            # Summary
            section += f"**Summary:** {explanation.summary}\n\n"
            
            # Main functionality
            if explanation.main_functionality:
                section += "**Functionality:**\n"
                section += f"{explanation.main_functionality}\n\n"
            
            # Key components
            if explanation.key_components:
                section += "**Key Components:**\n"
                for component in explanation.key_components:
                    section += f"- {component}\n"
                section += "\n"
            
            # Dependencies
            if explanation.dependencies:
                section += "**Dependencies:**\n"
                for dep in explanation.dependencies:
                    section += f"- `{dep}`\n"
                section += "\n"
            
            # Code patterns
            if explanation.code_patterns:
                section += "**Design Patterns:**\n"
                for pattern in explanation.code_patterns:
                    section += f"- {pattern}\n"
                section += "\n"
            
            # Improvement suggestions
            if explanation.improvement_suggestions:
                section += "**Improvement Suggestions:**\n"
                for suggestion in explanation.improvement_suggestions:
                    section += f"- {suggestion}\n"
                section += "\n"
            
            section += "---\n\n"
        
        # Code insights summary
        if code_insights and code_insights.get('improvement_themes'):
            section += "### 💡 Key Improvement Themes\n\n"
            section += "Based on AI analysis of the codebase, the following improvement areas were identified:\n\n"
            
            for theme in code_insights['improvement_themes']:
                section += f"- **{theme}**\n"
            section += "\n"
        
        return section
    
    def _file_importance_score(self, file_path: str) -> int:
        """Calculate importance score for file ordering"""
        from pathlib import Path
        
        path = Path(file_path)
        name = path.name.lower()
        score = 0
        
        # Main files get highest priority
        if name in ['main.py', 'app.py', 'index.js', 'server.js']:
            score = 1
        # Config files
        elif name in ['settings.py', 'config.js', 'webpack.config.js']:
            score = 2
        # Core files
        elif any(core in name for core in ['app', 'core', 'engine']):
            score = 3
        # API files
        elif any(api in name for api in ['api', 'route', 'controller']):
            score = 4
        # Other files
        else:
            score = 5
        
        return score
    
    def _generate_documentation_quality(self, structure_analysis: Dict[str, Any]) -> str:
        """Generate documentation quality assessment"""
        doc_files = structure_analysis.get('documentation_files', [])
        total_files = structure_analysis.get('total_files', 1)
        
        doc_section = f"""## 📚 Documentation Quality

### Documentation Coverage
- **Documentation Files:** {len(doc_files)}
- **Documentation Ratio:** {self._percentage(len(doc_files), total_files):.1f}% of total files

"""
        
        if doc_files:
            doc_section += "### Available Documentation\n\n"
            
            # Categorize documentation files
            readme_files = [f for f in doc_files if 'readme' in f.lower()]
            api_docs = [f for f in doc_files if any(term in f.lower() for term in ['api', 'reference'])]
            changelog_files = [f for f in doc_files if 'changelog' in f.lower()]
            license_files = [f for f in doc_files if 'license' in f.lower()]
            contrib_files = [f for f in doc_files if any(term in f.lower() for term in ['contributing', 'contribute'])]
            
            categories = [
                ('📖 README Files', readme_files),
                ('📋 API Documentation', api_docs),
                ('📝 Changelog', changelog_files),
                ('⚖️ License', license_files),
                ('🤝 Contributing Guidelines', contrib_files)
            ]
            
            for category_name, files in categories:
                if files:
                    doc_section += f"**{category_name}:**\n"
                    for file in files:
                        doc_section += f"- `{file}`\n"
                    doc_section += "\n"
            
            # Other documentation files
            other_docs = [f for f in doc_files if not any(f in cat_files for _, cat_files in categories for cat_files in [cat_files])]
            if other_docs:
                doc_section += "**Other Documentation:**\n"
                for file in other_docs[:5]:  # Limit to 5
                    doc_section += f"- `{file}`\n"
                if len(other_docs) > 5:
                    doc_section += f"- ... and {len(other_docs) - 5} more\n"
                doc_section += "\n"
        
        # Documentation quality assessment
        doc_section += "### Quality Assessment\n\n"
        
        if len(doc_files) == 0:
            doc_section += "❌ **Poor:** No documentation files found\n"
        elif len(doc_files) < 3:
            doc_section += "⚠️ **Basic:** Minimal documentation present\n"
        elif len(doc_files) < 8:
            doc_section += "✅ **Good:** Adequate documentation coverage\n"
        else:
            doc_section += "🌟 **Excellent:** Comprehensive documentation\n"
        
        return doc_section
    
    def _generate_development_workflow(self, structure_analysis: Dict[str, Any], repo_info: Dict[str, Any]) -> str:
        """Generate development workflow section"""
        config_files = structure_analysis.get('config_files', [])
        build_files = structure_analysis.get('build_files', [])
        test_files = structure_analysis.get('test_files', [])
        
        workflow = """## 🔄 Development Workflow

"""
        
        # CI/CD detection
        ci_files = [f for f in config_files if any(ci in f.lower() for ci in [
            '.github/workflows', 'travis', 'circle', 'jenkins', 'azure-pipelines'
        ])]
        
        if ci_files:
            workflow += "### Continuous Integration\n\n"
            workflow += "**CI/CD Configuration Files:**\n"
            for file in ci_files:
                workflow += f"- `{file}`\n"
            workflow += "\n"
        
        # Testing setup
        if test_files:
            workflow += "### Testing Strategy\n\n"
            workflow += f"**Test Files:** {len(test_files)}\n"
            workflow += f"**Testing Coverage:** {self._percentage(len(test_files), structure_analysis.get('total_files', 1)):.1f}% of codebase\n\n"
        
        # Build and development tools
        if build_files:
            workflow += "### Build & Development Tools\n\n"
            workflow += "**Configuration Files:**\n"
            for file in build_files[:5]:  # Show top 5
                workflow += f"- `{file}`\n"
            if len(build_files) > 5:
                workflow += f"- ... and {len(build_files) - 5} more\n"
            workflow += "\n"
        
        # Repository settings
        has_issues = repo_info.get('has_issues', False)
        has_projects = repo_info.get('has_projects', False)
        has_wiki = repo_info.get('has_wiki', False)
        
        workflow += "### Repository Features\n\n"
        workflow += f"- **Issues:** {'✅ Enabled' if has_issues else '❌ Disabled'}\n"
        workflow += f"- **Projects:** {'✅ Enabled' if has_projects else '❌ Disabled'}\n"
        workflow += f"- **Wiki:** {'✅ Enabled' if has_wiki else '❌ Disabled'}\n"
        
        return workflow
    
    def _generate_recommendations(self, structure_analysis: Dict[str, Any], 
                                code_metrics: Dict[str, Any], 
                                pattern_analysis: Dict[str, Any],
                                llm_analysis: Dict[str, Any] = None) -> str:
        """Generate recommendations section"""
        recommendations = """## 💡 Recommendations

Based on the analysis, here are some suggestions for improvement:

"""
        
        recs = []
        
        # Documentation recommendations
        doc_files = structure_analysis.get('documentation_files', [])
        if len(doc_files) < 3:
            recs.append("📚 **Improve Documentation:** Consider adding more documentation files such as API documentation, contributing guidelines, and detailed README sections.")
        
        # Testing recommendations
        test_files = structure_analysis.get('test_files', [])
        total_files = structure_analysis.get('total_files', 1)
        test_ratio = len(test_files) / total_files
        
        if test_ratio < 0.1:
            recs.append("🧪 **Increase Test Coverage:** The project has minimal test files. Consider implementing comprehensive unit and integration tests.")
        
        # Code complexity recommendations
        complexity = code_metrics.get('complexity_indicators', {})
        large_files = complexity.get('large_files', [])
        deeply_nested = complexity.get('deeply_nested', [])
        
        if large_files:
            recs.append(f"🔧 **Refactor Large Files:** {len(large_files)} files are over 500 lines. Consider breaking them into smaller, more manageable modules.")
        
        if deeply_nested:
            recs.append(f"🎯 **Reduce Complexity:** {len(deeply_nested)} files have deep nesting. Consider refactoring to improve readability and maintainability.")
        
        # Architecture recommendations
        arch_patterns = pattern_analysis.get('architecture_patterns', [])
        if not arch_patterns:
            recs.append("🏗️ **Define Architecture:** Consider implementing clear architectural patterns to improve code organization and maintainability.")
        
        # CI/CD recommendations
        config_files = structure_analysis.get('config_files', [])
        ci_files = [f for f in config_files if '.github/workflows' in f or 'travis' in f.lower()]
        if not ci_files:
            recs.append("⚙️ **Setup CI/CD:** Implement continuous integration and deployment pipelines to automate testing and deployment.")
        
        # Dependency management
        dep_files = [f for f in config_files if any(dep in f.lower() for dep in [
            'package.json', 'requirements.txt', 'pom.xml', 'cargo.toml'
        ])]
        if not dep_files:
            recs.append("📦 **Dependency Management:** Add proper dependency management files to ensure reproducible builds.")
        
        # LLM-based recommendations
        if llm_analysis:
            llm_suggestions = []
            for explanation in llm_analysis.values():
                if hasattr(explanation, 'improvement_suggestions') and explanation.improvement_suggestions:
                    # Ensure we only add string suggestions
                    for suggestion in explanation.improvement_suggestions:
                        if isinstance(suggestion, str):
                            llm_suggestions.append(suggestion)
                        elif isinstance(suggestion, dict):
                            # If it's a dict, try to extract a meaningful string
                            if 'text' in suggestion:
                                llm_suggestions.append(suggestion['text'])
                            elif 'description' in suggestion:
                                llm_suggestions.append(suggestion['description'])
                            else:
                                # Convert dict to string as fallback
                                llm_suggestions.append(str(suggestion))
            
            # Group similar suggestions
            if llm_suggestions:
                # Extract common themes - now we know all items are strings
                testing_suggestions = [s for s in llm_suggestions if isinstance(s, str) and 'test' in s.lower()]
                error_suggestions = [s for s in llm_suggestions if isinstance(s, str) and any(word in s.lower() for word in ['error', 'exception', 'handling'])]
                performance_suggestions = [s for s in llm_suggestions if isinstance(s, str) and 'performance' in s.lower()]
                
                if testing_suggestions:
                    recs.append("🧪 **AI-Identified Testing Improvements:** " + testing_suggestions[0])
                
                if error_suggestions:
                    recs.append("⚠️ **AI-Identified Error Handling:** " + error_suggestions[0])
                
                if performance_suggestions:
                    recs.append("🚀 **AI-Identified Performance Optimizations:** " + performance_suggestions[0])
        
        # Add recommendations to section
        if recs:
            for i, rec in enumerate(recs, 1):
                recommendations += f"{i}. {rec}\n\n"
        else:
            recommendations += "✨ **Great Job!** The repository appears to be well-structured and follows good practices.\n\n"
        
        # General best practices
        recommendations += """### 🌟 General Best Practices

- Keep dependencies up to date and regularly audit for security vulnerabilities
- Maintain comprehensive documentation and keep it current
- Implement proper error handling and logging
- Use consistent code formatting and style guidelines
- Regular code reviews and collaborative development practices
- Monitor code quality metrics and technical debt

"""
        
        return recommendations
    
    def _generate_footer(self) -> str:
        """Generate document footer"""
        footer = f"""---

## 🤖 Analysis Information

This analysis was generated automatically by the GitHub Repository Summarization Agent.

**Generated on:** {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}  
**Analysis Version:** 1.0.0  

### Methodology

This analysis includes:
- Repository structure and file organization
- Programming language detection and distribution
- Dependency analysis from package management files
- Code metrics including lines of code and complexity indicators
- Architecture pattern detection
- Documentation quality assessment
- Development workflow analysis

### Limitations

- Analysis is based on static code examination
- Some patterns may not be detected due to custom implementations
- File content analysis is limited to prevent performance issues
- Private or restricted files may not be accessible

For questions or feedback about this analysis, please refer to the tool documentation.

---

*Generated by DocuMate Repository Analyzer*"""
        
        return footer
    
    # Helper methods
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def _percentage(self, part: int, total: int) -> float:
        """Calculate percentage safely"""
        return (part / total * 100) if total > 0 else 0
    
    def _create_progress_bar(self, percentage: float, width: int = 20) -> str:
        """Create a simple text progress bar"""
        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"`{bar}`"
    
    def generate_quick_summary(self, repo_info: Dict[str, Any], 
                              structure_analysis: Dict[str, Any]) -> str:
        """
        Generate a quick, condensed summary for rapid understanding
        
        Args:
            repo_info: Repository metadata
            structure_analysis: Basic structure analysis
            
        Returns:
            Short markdown summary
        """
        name = repo_info.get('name', 'Repository')
        description = repo_info.get('description', 'No description')
        language = repo_info.get('language', 'Mixed')
        total_files = structure_analysis.get('total_files', 0)
        languages = structure_analysis.get('languages', {})
        
        summary = f"""# 🚀 Quick Summary: {name}

**Description:** {description}  
**Primary Language:** {language}  
**Total Files:** {total_files:,}  

## 📊 Language Breakdown
"""
        
        if languages:
            for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:3]:
                summary += f"- **{lang}:** {count} files\n"
        
        summary += f"""
## 🏷️ Key Stats
- **Repository Size:** {self._format_size(structure_analysis.get('total_size', 0))}
- **Documentation Files:** {len(structure_analysis.get('documentation_files', []))}
- **Test Files:** {len(structure_analysis.get('test_files', []))}
- **Configuration Files:** {len(structure_analysis.get('config_files', []))}

*This is a quick overview. For detailed analysis, generate the full summary.*
"""
        
        return summary
