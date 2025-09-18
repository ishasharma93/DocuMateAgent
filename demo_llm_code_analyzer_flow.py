#!/usr/bin/env python3
"""
Demo script for LLM Code Analyzer with MCP Integration

This script demonstrates the complete flow of:
1. Connecting to Azure DevOps via MCP client
2. Analyzing repository structure and contents
3. Retrieving code files
4. Performing LLM-based code analysis
5. Generating insights and summaries

Usage:
    python demo_llm_code_analyzer_flow.py --repo-url <azure_devops_repo_url>
    
Example:
    python demo_llm_code_analyzer_flow.py --repo-url "https://dev.azure.com/myorg/myproject/_git/myrepo"
"""

import asyncio
import logging
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.llm_code_analyzer.llm_code_analyzer import LLMCodeAnalyzer, CodeExplanation


class LLMCodeAnalyzerDemo:
    """Demo class for showcasing LLM Code Analyzer functionality"""
    
    def __init__(self, 
                 repo_url: str,
                 enable_llm: bool = True,
                 max_files: int = 20,
                 focus_files: Optional[List[str]] = None):
        """
        Initialize the demo
        
        Args:
            repo_url: Azure DevOps repository URL
            enable_llm: Whether to enable LLM analysis (requires API keys)
            max_files: Maximum number of files to analyze
            focus_files: Specific files to focus on for analysis
        """
        self.repo_url = repo_url
        self.enable_llm = enable_llm
        self.max_files = max_files
        self.focus_files = focus_files or []
        
        # Demo options (can be set after initialization)
        self.demo_individual = False
        self.demo_patterns = False
        self.save_prompts = False
        
        # Setup logging
        self._setup_logging()
        
        # Initialize analyzer
        self.analyzer = self._initialize_analyzer()
        
        # Demo results storage
        self.demo_results = {
            'timestamp': datetime.now().isoformat(),
            'repository_url': repo_url,
            'repository_analysis': {},
            'files_retrieved': {},
            'llm_explanations': {},
            'insights_summary': {},
            'errors': []
        }
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(f'demo_llm_analyzer_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _initialize_analyzer(self) -> LLMCodeAnalyzer:
        """Initialize the LLM Code Analyzer with proper configuration"""
        self.logger.info("Initializing LLM Code Analyzer...")
        
        # Check for required environment variables
        required_env_vars = {
            'AZURE_DEVOPS_ORGANIZATION': os.getenv('AZURE_DEVOPS_ORGANIZATION'),
            'AZURE_DEVOPS_PAT': os.getenv('AZURE_DEVOPS_PAT')
        }
        
        missing_vars = [var for var, value in required_env_vars.items() if not value]
        if missing_vars:
            self.logger.warning(f"Missing environment variables: {missing_vars}")
            self.logger.info("You can set these in a .env file or as environment variables")
        
        # LLM configuration (optional)
        llm_config = {
            'api_key': None,
            'model': 'gpt-4',
            'use_azure': False
        }
        
        if self.enable_llm:
            # Check for OpenAI configuration
            if os.getenv('OPENAI_API_KEY'):
                llm_config['api_key'] = os.getenv('OPENAI_API_KEY')
                self.logger.info("Using OpenAI API for LLM analysis")
            elif os.getenv('AZURE_OPENAI_API_KEY') and os.getenv('AZURE_OPENAI_ENDPOINT'):
                llm_config['api_key'] = os.getenv('AZURE_OPENAI_API_KEY')
                llm_config['use_azure'] = True
                llm_config['model'] = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4')
                self.logger.info("Using Azure OpenAI for LLM analysis")
            else:
                self.logger.warning("No LLM API keys found. LLM analysis will be disabled.")
                self.enable_llm = False
        
        try:
            analyzer = LLMCodeAnalyzer(
                api_key=llm_config['api_key'],
                model=llm_config['model'],
                use_azure=llm_config['use_azure'],
                enable_mcp=True,
                azure_devops_org=os.getenv('AZURE_DEVOPS_ORGANIZATION'),
                azure_devops_pat=os.getenv('AZURE_DEVOPS_PAT')
            )
            
            self.logger.info("LLM Code Analyzer initialized successfully")
            
            # Log configuration status
            if analyzer.mcp_enabled and analyzer.azure_devops_client:
                self.logger.info("✅ Azure DevOps MCP client ready")
            else:
                self.logger.warning("❌ Azure DevOps MCP client not available")
            
            if self.enable_llm and analyzer.client:
                self.logger.info("✅ LLM client ready")
            else:
                self.logger.warning("❌ LLM client not available")
            
            return analyzer
            
        except Exception as e:
            self.logger.error(f"Failed to initialize analyzer: {e}")
            raise
    
    async def run_demo(self) -> Dict[str, Any]:
        """
        Run the complete demo flow
        
        Returns:
            Dictionary containing all demo results
        """
        self.logger.info("=" * 80)
        self.logger.info("🚀 Starting LLM Code Analyzer Demo")
        self.logger.info("=" * 80)
        
        try:
            # Step 1: Analyze repository with MCP
            await self._demo_repository_analysis()
            
            # Step 2: Retrieve repository files
            await self._demo_file_retrieval()
            
            # Step 3: Perform LLM analysis (if enabled)
            if self.enable_llm:
                await self._demo_llm_analysis()
            else:
                self.logger.info("🔥 Skipping LLM analysis (disabled)")
            
            # Step 4: Generate insights summary
            self._demo_insights_generation()
            
            # Step 5: Demonstrate individual analysis methods (if enabled)
            if self.demo_individual:
                await self._demo_individual_analysis_methods()
            else:
                self.logger.info("🔥 Skipping individual analysis demo (use --demo-individual to enable)")
            
            # Step 6: Display results
            self._display_demo_results()
            
            self.logger.info("✅ Demo completed successfully!")
            
        except Exception as e:
            error_msg = f"Demo failed: {e}"
            self.logger.error(error_msg)
            self.demo_results['errors'].append(error_msg)
            raise
        
        finally:
            # Cleanup
            await self._cleanup()
        
        return self.demo_results
    
    async def _demo_repository_analysis(self):
        """Demo Step 1: Analyze repository structure using MCP"""
        self.logger.info("📋 Step 1: Analyzing repository with Azure DevOps MCP client...")
        
        if not self.analyzer.mcp_enabled or not self.analyzer.azure_devops_client:
            error_msg = "Azure DevOps MCP client not available. Check credentials."
            self.logger.error(error_msg)
            self.demo_results['errors'].append(error_msg)
            return
        
        try:
            # Analyze repository
            analysis_result = await self.analyzer.analyze_repository_with_mcp(
                self.repo_url,
                "azure_devops"
            )
            
            if 'error' in analysis_result:
                error_msg = f"Repository analysis failed: {analysis_result['error']}"
                self.logger.error(error_msg)
                self.demo_results['errors'].append(error_msg)
                return
            
            self.demo_results['repository_analysis'] = analysis_result
            
            # Log key findings
            if 'repository_info' in analysis_result:
                repo_info = analysis_result['repository_info']
                self.logger.info(f"📁 Repository: {repo_info.get('name', 'Unknown')}")
                if 'project' in repo_info:
                    self.logger.info(f"🏗️  Project: {repo_info['project'].get('name', 'Unknown')}")
                self.logger.info(f"📏 Size: {repo_info.get('size', 0)} bytes")
                self.logger.info(f"🌿 Default branch: {repo_info.get('defaultBranch', 'Unknown')}")
            
            if 'contents' in analysis_result:
                contents = analysis_result['contents']
                file_count = len([item for item in contents.get('value', []) if not item.get('isFolder', True)])
                folder_count = len([item for item in contents.get('value', []) if item.get('isFolder', False)])
                self.logger.info(f"📄 Files found: {file_count}")
                self.logger.info(f"📁 Folders found: {folder_count}")
            
            if 'recent_commits' in analysis_result:
                commits = analysis_result['recent_commits']
                commit_count = len(commits.get('value', []))
                self.logger.info(f"📝 Recent commits: {commit_count}")
            
            if 'pull_requests' in analysis_result:
                prs = analysis_result['pull_requests']
                pr_count = len(prs.get('value', []))
                self.logger.info(f"🔄 Active pull requests: {pr_count}")
            
            self.logger.info("✅ Repository analysis completed")
            
        except Exception as e:
            error_msg = f"Repository analysis error: {e}"
            self.logger.error(error_msg)
            self.demo_results['errors'].append(error_msg)
    
    async def _demo_file_retrieval(self):
        """Demo Step 2: Retrieve code files from repository"""
        self.logger.info("📥 Step 2: Retrieving code files from repository...")
        
        if not self.analyzer.mcp_enabled:
            error_msg = "MCP not enabled for file retrieval"
            self.logger.error(error_msg)
            self.demo_results['errors'].append(error_msg)
            return
        
        try:
            # Retrieve files
            files = await self.analyzer.get_mcp_repository_files(
                self.repo_url,
                "azure_devops",
                max_files=self.max_files
            )
            
            self.demo_results['files_retrieved'] = files
            
            if not files:
                self.logger.warning("⚠️  No code files retrieved")
                return
            
            # Log file retrieval results
            self.logger.info(f"📄 Retrieved {len(files)} code files:")
            
            # Group files by type
            file_types = {}
            total_size = 0
            
            for file_path, content in files.items():
                ext = Path(file_path).suffix.lower()
                if ext not in file_types:
                    file_types[ext] = []
                file_types[ext].append(file_path)
                total_size += len(content)
                
                self.logger.info(f"   📝 {file_path} ({len(content)} chars)")
            
            # Summary by file type
            self.logger.info("📊 Files by type:")
            for ext, file_list in file_types.items():
                lang = self.analyzer.code_extensions.get(ext, 'Unknown')
                self.logger.info(f"   {ext} ({lang}): {len(file_list)} files")
            
            self.logger.info(f"💾 Total content size: {total_size:,} characters")
            self.logger.info("✅ File retrieval completed")
            
        except Exception as e:
            error_msg = f"File retrieval error: {e}"
            self.logger.error(error_msg)
            self.demo_results['errors'].append(error_msg)
    
    async def _demo_llm_analysis(self):
        """Demo Step 3: Perform LLM-based code analysis"""
        self.logger.info("🧠 Step 3: Performing LLM code analysis...")
        
        if not self.analyzer.client:
            error_msg = "LLM client not available. Check API configuration."
            self.logger.error(error_msg)
            self.demo_results['errors'].append(error_msg)
            return
        
        files = self.demo_results.get('files_retrieved', {})
        if not files:
            error_msg = "No files available for LLM analysis"
            self.logger.error(error_msg)
            self.demo_results['errors'].append(error_msg)
            return
        
        try:
            # Step 3a: Demonstrate file selection process
            await self._demo_file_selection(files)
            
            # Step 3b: Perform comprehensive LLM analysis
            explanations = await self.analyzer.analyze_codebase(
                files,
                focus_files=self.focus_files if self.focus_files else None
            )
            
            # Step 3c: Store and demonstrate detailed analysis results
            await self._demo_detailed_analysis_results(explanations)
            
            # Step 3d: Demonstrate analysis patterns and insights extraction
            await self._demo_analysis_patterns(explanations)
            
            self.logger.info("✅ LLM analysis completed")
            
        except Exception as e:
            error_msg = f"LLM analysis error: {e}"
            self.logger.error(error_msg)
            self.demo_results['errors'].append(error_msg)
    
    async def _demo_file_selection(self, files: Dict[str, str]):
        """Demonstrate the file selection process for LLM analysis"""
        self.logger.info("🎯 Step 3a: Demonstrating file selection for LLM analysis...")
        
        # Show all available files
        self.logger.info(f"📋 Available files for analysis: {len(files)}")
        for file_path in sorted(files.keys()):
            file_size = len(files[file_path])
            ext = Path(file_path).suffix.lower()
            language = self.analyzer.code_extensions.get(ext, 'Unknown')
            self.logger.info(f"   📄 {file_path} ({language}, {file_size:,} chars)")
        
        # Demonstrate the selection logic
        selected_files = self.analyzer._select_files_for_analysis(files, self.focus_files)
        
        self.logger.info(f"\n🎯 Selected {len(selected_files)} files for detailed LLM analysis:")
        
        # Show scoring breakdown for educational purposes
        file_scores = []
        for file_path, content in files.items():
            path = Path(file_path)
            name = path.name.lower()
            ext = path.suffix.lower()
            
            # Calculate priority score (simplified version of the actual logic)
            score = 0
            
            # Focus files get highest priority
            if self.focus_files and file_path in self.focus_files:
                score += 1000
                
            # Main entry points
            if name in ['main.py', 'index.js', 'app.py', 'server.js', 'main.go', 'main.java']:
                score += 500
                
            # Core application files
            if any(core in name for core in ['app', 'application', 'core', 'engine', 'service']):
                score += 300
                
            # API/Route files
            if any(api in name for api in ['api', 'route', 'endpoint', 'controller']):
                score += 250
                
            # Language support
            if ext in self.analyzer.code_extensions:
                score += 100
                
            # Root level files
            if len(path.parts) == 1:
                score += 100
            
            file_scores.append((file_path, score, file_path in selected_files))
        
        # Sort by score and show top candidates
        file_scores.sort(key=lambda x: x[1], reverse=True)
        
        self.logger.info("📊 File priority scores:")
        for file_path, score, selected in file_scores[:10]:  # Show top 10
            status = "✅ SELECTED" if selected else "❌ skipped"
            self.logger.info(f"   {score:4d} points: {file_path} {status}")
        
        if len(file_scores) > 10:
            self.logger.info(f"   ... and {len(file_scores) - 10} more files")
        
        # Store selection info
        self.demo_results['file_selection'] = {
            'total_files': len(files),
            'selected_files': len(selected_files),
            'focus_files': self.focus_files,
            'selection_criteria': {
                'max_files_for_llm': int(os.getenv('MAX_FILES_FOR_LLM_ANALYSIS', '15')),
                'max_code_length': self.analyzer.max_code_length,
                'supported_extensions': list(self.analyzer.code_extensions.keys())
            }
        }
    
    async def _demo_detailed_analysis_results(self, explanations: Dict[str, Any]):
        """Demonstrate detailed analysis results for each file"""
        self.logger.info("📊 Step 3b: Demonstrating detailed file-by-file analysis...")
        
        if not explanations:
            self.logger.warning("⚠️  No LLM explanations generated")
            return
        
        # Store structured results
        self.demo_results['llm_explanations'] = {
            path: {
                'file_path': exp.file_path,
                'language': exp.language,
                'summary': exp.summary,
                'main_functionality': exp.main_functionality,
                'key_components': exp.key_components,
                'dependencies': exp.dependencies,
                'complexity_assessment': exp.complexity_assessment,
                'improvement_suggestions': exp.improvement_suggestions,
                'code_patterns': exp.code_patterns
            }
            for path, exp in explanations.items()
        }
        
        # Detailed logging for each file
        self.logger.info(f"🔍 Analyzed {len(explanations)} files with LLM:\n")
        
        for i, (file_path, explanation) in enumerate(explanations.items(), 1):
            self.logger.info("=" * 80)
            self.logger.info(f"📄 File {i}/{len(explanations)}: {file_path}")
            self.logger.info("=" * 80)
            
            # Basic info
            self.logger.info(f"🔤 Language: {explanation.language}")
            self.logger.info(f"📝 Summary: {explanation.summary}")
            self.logger.info(f"📊 Complexity: {explanation.complexity_assessment}")
            
            # Main functionality (truncated for readability)
            functionality = explanation.main_functionality
            if len(functionality) > 200:
                functionality = functionality[:197] + "..."
            self.logger.info(f"🔧 Main Functionality: {functionality}")
            
            # Key components
            if explanation.key_components:
                self.logger.info(f"🧩 Key Components ({len(explanation.key_components)}):")
                for j, component in enumerate(explanation.key_components[:5], 1):
                    self.logger.info(f"   {j}. {component}")
                if len(explanation.key_components) > 5:
                    self.logger.info(f"   ... and {len(explanation.key_components) - 5} more")
            
            # Dependencies
            if explanation.dependencies:
                self.logger.info(f"📦 Dependencies ({len(explanation.dependencies)}):")
                for dep in explanation.dependencies[:5]:
                    self.logger.info(f"   • {dep}")
                if len(explanation.dependencies) > 5:
                    self.logger.info(f"   ... and {len(explanation.dependencies) - 5} more")
            
            # Code patterns
            if explanation.code_patterns:
                self.logger.info(f"🎨 Code Patterns ({len(explanation.code_patterns)}):")
                for pattern in explanation.code_patterns[:3]:
                    self.logger.info(f"   • {pattern}")
                if len(explanation.code_patterns) > 3:
                    self.logger.info(f"   ... and {len(explanation.code_patterns) - 3} more")
            
            # Improvement suggestions
            if explanation.improvement_suggestions:
                self.logger.info(f"💡 Improvement Suggestions ({len(explanation.improvement_suggestions)}):")
                for j, suggestion in enumerate(explanation.improvement_suggestions[:3], 1):
                    self.logger.info(f"   {j}. {suggestion}")
                if len(explanation.improvement_suggestions) > 3:
                    self.logger.info(f"   ... and {len(explanation.improvement_suggestions) - 3} more")
            
            self.logger.info("")  # Empty line for readability
    
    async def _demo_analysis_patterns(self, explanations: Dict[str, Any]):
        """Demonstrate pattern analysis and cross-file insights"""
        self.logger.info("🔍 Step 3c: Demonstrating cross-file analysis patterns...")
        
        if not explanations:
            return
        
        # Analyze patterns across files
        all_languages = set()
        all_patterns = []
        all_dependencies = []
        complexity_distribution = {}
        file_size_analysis = {}
        
        for file_path, explanation in explanations.items():
            # Language distribution
            all_languages.add(explanation.language)
            
            # Pattern collection
            if explanation.code_patterns:
                all_patterns.extend(explanation.code_patterns)
            
            # Dependency collection
            if explanation.dependencies:
                all_dependencies.extend(explanation.dependencies)
            
            # Complexity distribution
            complexity = explanation.complexity_assessment.split(' ')[0] if explanation.complexity_assessment else 'Unknown'
            complexity_distribution[complexity] = complexity_distribution.get(complexity, 0) + 1
            
            # File size vs complexity analysis
            file_content = self.demo_results.get('files_retrieved', {}).get(file_path, '')
            file_size = len(file_content.split('\n'))
            file_size_analysis[file_path] = {
                'lines': file_size,
                'complexity': complexity,
                'patterns_count': len(explanation.code_patterns) if explanation.code_patterns else 0
            }
        
        # Pattern frequency analysis
        pattern_counts = {}
        for pattern in all_patterns:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        # Dependency frequency analysis
        dependency_counts = {}
        for dep in all_dependencies:
            dependency_counts[dep] = dependency_counts.get(dep, 0) + 1
        
        # Log insights
        self.logger.info("🎯 Cross-File Analysis Insights:")
        self.logger.info(f"   📊 Languages used: {', '.join(sorted(all_languages))}")
        self.logger.info(f"   📈 Complexity distribution: {dict(complexity_distribution)}")
        
        # Most common patterns
        if pattern_counts:
            top_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            self.logger.info("   🎨 Most common patterns:")
            for pattern, count in top_patterns:
                self.logger.info(f"      • {pattern} (used in {count} files)")
        
        # Most common dependencies
        if dependency_counts:
            top_deps = sorted(dependency_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            self.logger.info("   📦 Most common dependencies:")
            for dep, count in top_deps:
                self.logger.info(f"      • {dep} (used in {count} files)")
        
        # File size vs complexity correlation
        self.logger.info("   📏 File size vs complexity correlation:")
        size_complexity = {}
        for file_info in file_size_analysis.values():
            complexity = file_info['complexity']
            lines = file_info['lines']
            if complexity not in size_complexity:
                size_complexity[complexity] = []
            size_complexity[complexity].append(lines)
        
        for complexity, line_counts in size_complexity.items():
            avg_lines = sum(line_counts) / len(line_counts)
            self.logger.info(f"      {complexity}: avg {avg_lines:.1f} lines ({len(line_counts)} files)")
        
        # Store pattern analysis results
        self.demo_results['pattern_analysis'] = {
            'languages_used': list(all_languages),
            'complexity_distribution': complexity_distribution,
            'top_patterns': dict(top_patterns[:10]) if pattern_counts else {},
            'top_dependencies': dict(top_deps[:10]) if dependency_counts else {},
            'file_size_analysis': file_size_analysis,
            'total_patterns_found': len(set(all_patterns)),
            'total_dependencies_found': len(set(all_dependencies))
        }
    
    def _demo_insights_generation(self):
        """Demo Step 4: Generate high-level insights"""
        self.logger.info("💡 Step 4: Generating code insights...")
        
        if not self.demo_results.get('llm_explanations'):
            self.logger.warning("⚠️  No LLM explanations available for insights generation")
            return
        
        try:
            # Convert back to CodeExplanation objects for insights generation
            explanations = {}
            for path, exp_data in self.demo_results['llm_explanations'].items():
                explanations[path] = CodeExplanation(
                    file_path=exp_data['file_path'],
                    language=exp_data['language'],
                    summary=exp_data['summary'],
                    main_functionality=exp_data['main_functionality'],
                    key_components=exp_data['key_components'],
                    dependencies=exp_data['dependencies'],
                    complexity_assessment=exp_data['complexity_assessment'],
                    improvement_suggestions=exp_data['improvement_suggestions'],
                    code_patterns=exp_data['code_patterns']
                )
            
            # Generate insights
            insights = self.analyzer.generate_code_insights_summary(explanations)
            self.demo_results['insights_summary'] = insights
            
            # Demonstrate specific insight generation methods
            self._demo_complexity_analysis(explanations)
            self._demo_dependency_analysis(explanations)
            self._demo_pattern_analysis(explanations)
            self._demo_improvement_analysis(explanations)
            
            # Log insights
            self.logger.info("📊 Code Insights Summary:")
            self.logger.info(f"   📁 Total files analyzed: {insights['total_files_analyzed']}")
            
            if insights['complexity_distribution']:
                self.logger.info("   📈 Complexity distribution:")
                for complexity, count in insights['complexity_distribution'].items():
                    self.logger.info(f"      {complexity}: {count} files")
            
            if insights['common_patterns']:
                self.logger.info(f"   🎨 Common patterns: {', '.join(insights['common_patterns'][:5])}")
            
            if insights['key_technologies']:
                tech_list = insights['key_technologies'][:5]
                self.logger.info(f"   🔧 Key technologies: {', '.join(tech_list)}")
            
            if insights['improvement_themes']:
                self.logger.info(f"   💡 Improvement themes: {', '.join(insights['improvement_themes'])}")
            
            self.logger.info("✅ Insights generation completed")
            
        except Exception as e:
            error_msg = f"Insights generation error: {e}"
            self.logger.error(error_msg)
            self.demo_results['errors'].append(error_msg)
    
    def _demo_complexity_analysis(self, explanations: Dict[str, CodeExplanation]):
        """Demonstrate complexity analysis capabilities"""
        self.logger.info("\n🔍 Demonstrating Complexity Analysis:")
        
        complexity_files = {}
        for file_path, explanation in explanations.items():
            complexity = explanation.complexity_assessment
            if complexity not in complexity_files:
                complexity_files[complexity] = []
            complexity_files[complexity].append({
                'file': file_path,
                'language': explanation.language,
                'summary': explanation.summary[:100] + "..." if len(explanation.summary) > 100 else explanation.summary
            })
        
        for complexity, files in complexity_files.items():
            self.logger.info(f"   📊 {complexity}:")
            for file_info in files:
                self.logger.info(f"      • {file_info['file']} ({file_info['language']})")
                self.logger.info(f"        {file_info['summary']}")
    
    def _demo_dependency_analysis(self, explanations: Dict[str, CodeExplanation]):
        """Demonstrate dependency analysis capabilities"""
        self.logger.info("\n📦 Demonstrating Dependency Analysis:")
        
        # Collect all dependencies
        all_deps = {}
        for file_path, explanation in explanations.items():
            for dep in explanation.dependencies:
                if dep not in all_deps:
                    all_deps[dep] = []
                all_deps[dep].append(file_path)
        
        # Show most used dependencies
        sorted_deps = sorted(all_deps.items(), key=lambda x: len(x[1]), reverse=True)
        
        self.logger.info(f"   Found {len(all_deps)} unique dependencies across {len(explanations)} files")
        self.logger.info("   Top dependencies by usage:")
        
        for dep, files in sorted_deps[:10]:
            self.logger.info(f"      📦 {dep} (used in {len(files)} files)")
            for file_path in files[:3]:  # Show first 3 files
                self.logger.info(f"         - {file_path}")
            if len(files) > 3:
                self.logger.info(f"         ... and {len(files) - 3} more files")
    
    def _demo_pattern_analysis(self, explanations: Dict[str, CodeExplanation]):
        """Demonstrate code pattern analysis capabilities"""
        self.logger.info("\n🎨 Demonstrating Pattern Analysis:")
        
        # Collect all patterns
        all_patterns = {}
        for file_path, explanation in explanations.items():
            for pattern in explanation.code_patterns:
                if pattern not in all_patterns:
                    all_patterns[pattern] = []
                all_patterns[pattern].append({
                    'file': file_path,
                    'language': explanation.language
                })
        
        # Show most used patterns
        sorted_patterns = sorted(all_patterns.items(), key=lambda x: len(x[1]), reverse=True)
        
        self.logger.info(f"   Found {len(all_patterns)} unique patterns across {len(explanations)} files")
        self.logger.info("   Top patterns by usage:")
        
        for pattern, usages in sorted_patterns[:8]:
            languages = set(usage['language'] for usage in usages)
            self.logger.info(f"      🎨 {pattern}")
            self.logger.info(f"         Used in {len(usages)} files across {len(languages)} languages: {', '.join(languages)}")
            
            # Show files using this pattern
            for usage in usages[:3]:
                self.logger.info(f"         - {usage['file']} ({usage['language']})")
            if len(usages) > 3:
                self.logger.info(f"         ... and {len(usages) - 3} more files")
    
    def _demo_improvement_analysis(self, explanations: Dict[str, CodeExplanation]):
        """Demonstrate improvement suggestion analysis"""
        self.logger.info("\n💡 Demonstrating Improvement Analysis:")
        
        # Categorize improvement suggestions
        improvement_categories = {
            'Testing': [],
            'Error Handling': [],
            'Performance': [],
            'Documentation': [],
            'Security': [],
            'Code Quality': [],
            'Architecture': [],
            'Other': []
        }
        
        for file_path, explanation in explanations.items():
            for suggestion in explanation.improvement_suggestions:
                suggestion_lower = suggestion.lower()
                categorized = False
                
                if any(keyword in suggestion_lower for keyword in ['test', 'testing', 'unit test', 'integration test']):
                    improvement_categories['Testing'].append({'file': file_path, 'suggestion': suggestion})
                    categorized = True
                elif any(keyword in suggestion_lower for keyword in ['error', 'exception', 'try', 'catch', 'handling']):
                    improvement_categories['Error Handling'].append({'file': file_path, 'suggestion': suggestion})
                    categorized = True
                elif any(keyword in suggestion_lower for keyword in ['performance', 'optimize', 'speed', 'memory', 'cache']):
                    improvement_categories['Performance'].append({'file': file_path, 'suggestion': suggestion})
                    categorized = True
                elif any(keyword in suggestion_lower for keyword in ['document', 'comment', 'docstring', 'readme']):
                    improvement_categories['Documentation'].append({'file': file_path, 'suggestion': suggestion})
                    categorized = True
                elif any(keyword in suggestion_lower for keyword in ['security', 'secure', 'authentication', 'authorization', 'validation']):
                    improvement_categories['Security'].append({'file': file_path, 'suggestion': suggestion})
                    categorized = True
                elif any(keyword in suggestion_lower for keyword in ['refactor', 'clean', 'maintainability', 'readability']):
                    improvement_categories['Code Quality'].append({'file': file_path, 'suggestion': suggestion})
                    categorized = True
                elif any(keyword in suggestion_lower for keyword in ['architecture', 'design', 'pattern', 'structure']):
                    improvement_categories['Architecture'].append({'file': file_path, 'suggestion': suggestion})
                    categorized = True
                
                if not categorized:
                    improvement_categories['Other'].append({'file': file_path, 'suggestion': suggestion})
        
        # Display categorized suggestions
        total_suggestions = sum(len(suggestions) for suggestions in improvement_categories.values())
        self.logger.info(f"   Found {total_suggestions} improvement suggestions across {len(explanations)} files")
        
        for category, suggestions in improvement_categories.items():
            if suggestions:
                self.logger.info(f"\n   💡 {category} ({len(suggestions)} suggestions):")
                for suggestion_info in suggestions[:3]:  # Show first 3 per category
                    file_name = Path(suggestion_info['file']).name
                    suggestion_text = suggestion_info['suggestion']
                    if len(suggestion_text) > 100:
                        suggestion_text = suggestion_text[:97] + "..."
                    self.logger.info(f"      📁 {file_name}: {suggestion_text}")
                
                if len(suggestions) > 3:
                    self.logger.info(f"      ... and {len(suggestions) - 3} more suggestions in this category")
        
        # Store improvement analysis
        self.demo_results['improvement_analysis'] = {
            category: [{'file': s['file'], 'suggestion': s['suggestion']} for s in suggestions]
            for category, suggestions in improvement_categories.items()
            if suggestions
        }
    
    async def _demo_individual_analysis_methods(self):
        """Demo Step 5: Demonstrate individual LLM analysis methods"""
        self.logger.info("\n🔬 Step 5: Demonstrating individual LLM analysis methods...")
        
        files = self.demo_results.get('files_retrieved', {})
        if not files or not self.analyzer.client:
            self.logger.warning("⚠️  Skipping individual analysis demo - no files or LLM client available")
            return
        
        # Select a sample file for detailed analysis demonstration
        sample_files = list(files.items())[:3]  # Take first 3 files
        
        for i, (file_path, content) in enumerate(sample_files, 1):
            self.logger.info(f"\n🔍 Individual Analysis Demo {i}/{len(sample_files)}: {file_path}")
            self.logger.info("-" * 60)
            
            try:
                # Demonstrate the analysis prompt creation
                await self._demo_prompt_creation(file_path, content)
                
                # Demonstrate single file analysis
                await self._demo_single_file_analysis(file_path, content)
                
                # Demonstrate response parsing
                await self._demo_response_parsing(file_path, content)
                
            except Exception as e:
                self.logger.warning(f"Demo analysis failed for {file_path}: {e}")
    
    async def _demo_prompt_creation(self, file_path: str, content: str):
        """Demonstrate the LLM prompt creation process"""
        self.logger.info("📝 Demonstrating prompt creation...")
        
        language = self.analyzer.code_extensions.get(Path(file_path).suffix.lower(), 'Unknown')
        
        # Show the prompt creation process
        prompt = self.analyzer._create_analysis_prompt(file_path, content, language)
        
        # Log prompt details (truncated for readability)
        self.logger.info(f"   🔤 Language detected: {language}")
        self.logger.info(f"   📏 Content length: {len(content):,} characters")
        self.logger.info(f"   📝 Prompt length: {len(prompt):,} characters")
        
        # Show a snippet of the prompt structure
        prompt_lines = prompt.split('\n')
        self.logger.info("   📋 Prompt structure preview:")
        for i, line in enumerate(prompt_lines[:5]):
            if line.strip():
                preview = line.strip()[:80] + "..." if len(line.strip()) > 80 else line.strip()
                self.logger.info(f"      {i+1}. {preview}")
        
        if len(prompt_lines) > 5:
            self.logger.info(f"      ... and {len(prompt_lines) - 5} more lines")
        
        # Store prompt info
        if 'prompt_analysis' not in self.demo_results:
            self.demo_results['prompt_analysis'] = {}
        
        self.demo_results['prompt_analysis'][file_path] = {
            'language': language,
            'content_length': len(content),
            'prompt_length': len(prompt),
            'prompt_lines': len(prompt_lines)
        }
        
        # Save prompt to file if requested
        if self.save_prompts:
            prompt_filename = f"prompt_{Path(file_path).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            try:
                with open(prompt_filename, 'w', encoding='utf-8') as f:
                    f.write(f"# LLM Analysis Prompt for {file_path}\n")
                    f.write(f"# Generated at: {datetime.now().isoformat()}\n\n")
                    f.write(prompt)
                self.logger.info(f"   💾 Prompt saved to: {prompt_filename}")
            except Exception as e:
                self.logger.warning(f"   ⚠️  Failed to save prompt: {e}")
    
    async def _demo_single_file_analysis(self, file_path: str, content: str):
        """Demonstrate single file analysis process"""
        self.logger.info("⚙️  Demonstrating single file analysis...")
        
        # Create a semaphore for demo purposes
        semaphore = asyncio.Semaphore(1)
        
        try:
            # Show the analysis process
            self.logger.info(f"   🔄 Starting analysis for {file_path}...")
            
            # Call the actual analysis method
            explanation = await self.analyzer._analyze_single_file(semaphore, file_path, content)
            
            self.logger.info("   ✅ Analysis completed successfully")
            self.logger.info(f"   📊 Generated explanation with {len(explanation.key_components)} components")
            self.logger.info(f"   📦 Found {len(explanation.dependencies)} dependencies")
            self.logger.info(f"   🎨 Identified {len(explanation.code_patterns)} patterns")
            self.logger.info(f"   💡 Provided {len(explanation.improvement_suggestions)} suggestions")
            
            # Store individual analysis result
            if 'individual_analysis' not in self.demo_results:
                self.demo_results['individual_analysis'] = {}
            
            self.demo_results['individual_analysis'][file_path] = {
                'success': True,
                'components_count': len(explanation.key_components),
                'dependencies_count': len(explanation.dependencies),
                'patterns_count': len(explanation.code_patterns),
                'suggestions_count': len(explanation.improvement_suggestions),
                'complexity': explanation.complexity_assessment
            }
            
        except Exception as e:
            self.logger.error(f"   ❌ Analysis failed: {e}")
            if 'individual_analysis' not in self.demo_results:
                self.demo_results['individual_analysis'] = {}
            
            self.demo_results['individual_analysis'][file_path] = {
                'success': False,
                'error': str(e)
            }
    
    async def _demo_response_parsing(self, file_path: str, content: str):
        """Demonstrate LLM response parsing process"""
        self.logger.info("🔍 Demonstrating response parsing...")
        
        # Show the parsing capabilities with a mock response
        language = self.analyzer.code_extensions.get(Path(file_path).suffix.lower(), 'Unknown')
        
        # Create a sample LLM response to demonstrate parsing
        sample_response = '''{
    "summary": "Sample analysis for demonstration purposes",
    "main_functionality": "Demonstrates the parsing capabilities of the LLM analyzer",
    "key_components": [
        "Response parser",
        "JSON extraction logic",
        "Fallback parsing mechanism"
    ],
    "dependencies": [
        "json - for JSON parsing",
        "logging - for error handling"
    ],
    "complexity_assessment": "Simple - demonstration code with clear structure",
    "improvement_suggestions": [
        "Add more robust error handling",
        "Include input validation"
    ],
    "code_patterns": [
        "Parser Pattern",
        "Fallback Pattern"
    ]
}'''
        
        try:
            # Demonstrate the parsing process
            self.logger.info("   📥 Parsing sample LLM response...")
            
            parsed_explanation = self.analyzer._parse_llm_response(file_path, language, sample_response)
            
            self.logger.info("   ✅ Response parsed successfully")
            self.logger.info(f"   📝 Summary: {parsed_explanation.summary}")
            self.logger.info(f"   🎯 Language: {parsed_explanation.language}")
            self.logger.info(f"   📊 Components parsed: {len(parsed_explanation.key_components)}")
            
            # Show JSON extraction process
            json_start = sample_response.find('{')
            json_end = sample_response.rfind('}') + 1
            self.logger.info(f"   🔍 JSON extraction: characters {json_start} to {json_end}")
            
            # Demonstrate fallback parsing
            self.logger.info("   🛡️  Testing fallback parsing with malformed response...")
            malformed_response = "This is not valid JSON but should still be parsed"
            fallback_explanation = self.analyzer._parse_llm_response(file_path, language, malformed_response)
            self.logger.info(f"   ✅ Fallback parsing successful: {fallback_explanation.summary[:50]}...")
            
        except Exception as e:
            self.logger.error(f"   ❌ Parsing demonstration failed: {e}")
    
    def _display_demo_results(self):
        """Display comprehensive demo results"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("📋 DEMO RESULTS SUMMARY")
        self.logger.info("=" * 80)
        
        # Repository info
        if self.demo_results['repository_analysis']:
            self.logger.info("🏗️  REPOSITORY ANALYSIS:")
            repo_info = self.demo_results['repository_analysis'].get('repository_info', {})
            if repo_info:
                self.logger.info(f"   Repository: {repo_info.get('name', 'Unknown')}")
                if 'project' in repo_info:
                    self.logger.info(f"   Project: {repo_info['project'].get('name', 'Unknown')}")
                self.logger.info(f"   Size: {repo_info.get('size', 0):,} bytes")
        
        # Files retrieved
        files_count = len(self.demo_results.get('files_retrieved', {}))
        self.logger.info(f"\n📄 FILES RETRIEVED: {files_count}")
        
        # File selection analysis
        if 'file_selection' in self.demo_results:
            selection_info = self.demo_results['file_selection']
            self.logger.info(f"   Total files: {selection_info['total_files']}")
            self.logger.info(f"   Selected for LLM: {selection_info['selected_files']}")
            self.logger.info(f"   Focus files: {len(selection_info.get('focus_files', []))}")
            self.logger.info(f"   Max LLM files: {selection_info['selection_criteria']['max_files_for_llm']}")
        
        # LLM analysis
        llm_count = len(self.demo_results.get('llm_explanations', {}))
        self.logger.info(f"\n🧠 LLM ANALYSIS: {llm_count} files analyzed")
        
        # Pattern analysis
        if 'pattern_analysis' in self.demo_results:
            pattern_info = self.demo_results['pattern_analysis']
            self.logger.info(f"   Languages used: {len(pattern_info['languages_used'])}")
            self.logger.info(f"   Unique patterns: {pattern_info['total_patterns_found']}")
            self.logger.info(f"   Unique dependencies: {pattern_info['total_dependencies_found']}")
        
        # Individual analysis
        if 'individual_analysis' in self.demo_results:
            individual_info = self.demo_results['individual_analysis']
            successful = sum(1 for result in individual_info.values() if result.get('success', False))
            self.logger.info(f"\n🔬 INDIVIDUAL ANALYSIS: {successful}/{len(individual_info)} successful")
            
            for file_path, result in individual_info.items():
                if result.get('success', False):
                    self.logger.info(f"   ✅ {Path(file_path).name}: {result['components_count']} components, {result['dependencies_count']} deps")
                else:
                    self.logger.info(f"   ❌ {Path(file_path).name}: {result.get('error', 'Unknown error')}")
        
        # Prompt analysis
        if 'prompt_analysis' in self.demo_results:
            prompt_info = self.demo_results['prompt_analysis']
            avg_prompt_length = sum(info['prompt_length'] for info in prompt_info.values()) / len(prompt_info)
            self.logger.info(f"\n📝 PROMPT ANALYSIS: {len(prompt_info)} prompts generated")
            self.logger.info(f"   Average prompt length: {avg_prompt_length:,.0f} characters")
        
        # Insights
        insights = self.demo_results.get('insights_summary', {})
        if insights:
            self.logger.info("\n💡 INSIGHTS:")
            self.logger.info(f"   Complexity distribution: {insights.get('complexity_distribution', {})}")
            self.logger.info(f"   Common patterns: {len(insights.get('common_patterns', []))}")
            self.logger.info(f"   Key technologies: {len(insights.get('key_technologies', []))}")
        
        # Improvement analysis
        if 'improvement_analysis' in self.demo_results:
            improvement_info = self.demo_results['improvement_analysis']
            total_improvements = sum(len(suggestions) for suggestions in improvement_info.values())
            self.logger.info(f"\n💡 IMPROVEMENT ANALYSIS: {total_improvements} suggestions across {len(improvement_info)} categories")
            
            for category, suggestions in improvement_info.items():
                self.logger.info(f"   {category}: {len(suggestions)} suggestions")
        
        # Errors
        if self.demo_results['errors']:
            self.logger.info(f"\n❌ ERRORS: {len(self.demo_results['errors'])}")
            for error in self.demo_results['errors']:
                self.logger.info(f"   • {error}")
        
        # Performance metrics
        self._display_performance_metrics()
        
        # Save results to file
        results_file = f"demo_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.demo_results, f, indent=2, ensure_ascii=False)
            self.logger.info(f"\n💾 Full results saved to: {results_file}")
        except Exception as e:
            self.logger.warning(f"Failed to save results to file: {e}")
    
    def _display_performance_metrics(self):
        """Display performance metrics for the demo"""
        self.logger.info("\n⚡ PERFORMANCE METRICS:")
        
        files_retrieved = len(self.demo_results.get('files_retrieved', {}))
        files_analyzed = len(self.demo_results.get('llm_explanations', {}))
        
        if files_retrieved > 0:
            analysis_ratio = (files_analyzed / files_retrieved) * 100
            self.logger.info(f"   Analysis coverage: {analysis_ratio:.1f}% ({files_analyzed}/{files_retrieved} files)")
        
        # Calculate total content processed
        total_chars = sum(len(content) for content in self.demo_results.get('files_retrieved', {}).values())
        if total_chars > 0:
            self.logger.info(f"   Total content processed: {total_chars:,} characters")
            
            if files_analyzed > 0:
                avg_chars_per_file = total_chars / files_analyzed
                self.logger.info(f"   Average file size analyzed: {avg_chars_per_file:,.0f} characters")
        
        # Show configuration used
        if hasattr(self.analyzer, 'max_concurrent_requests'):
            self.logger.info(f"   Max concurrent LLM requests: {self.analyzer.max_concurrent_requests}")
        
        if hasattr(self.analyzer, 'max_code_length'):
            self.logger.info(f"   Max code length for LLM: {self.analyzer.max_code_length:,} characters")
    
    async def _cleanup(self):
        """Cleanup resources"""
        self.logger.info("🧹 Cleaning up resources...")
        try:
            if self.analyzer:
                await self.analyzer.close_mcp_clients()
            self.logger.info("✅ Cleanup completed")
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")


async def main():
    """Main demo entry point"""
    parser = argparse.ArgumentParser(
        description="Demo LLM Code Analyzer with MCP Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo_llm_code_analyzer_flow.py --repo-url "https://dev.azure.com/myorg/myproject/_git/myrepo"
  python demo_llm_code_analyzer_flow.py --repo-url "https://dev.azure.com/myorg/myproject/_git/myrepo" --max-files 10 --disable-llm
  python demo_llm_code_analyzer_flow.py --repo-url "https://dev.azure.com/myorg/myproject/_git/myrepo" --focus-files main.py app.py

Environment Variables:
  AZURE_DEVOPS_ORGANIZATION - Azure DevOps organization name
  AZURE_DEVOPS_PAT - Azure DevOps Personal Access Token
  OPENAI_API_KEY - OpenAI API key (for LLM analysis)
  AZURE_OPENAI_API_KEY - Azure OpenAI API key (alternative)
  AZURE_OPENAI_ENDPOINT - Azure OpenAI endpoint
  AZURE_OPENAI_DEPLOYMENT_NAME - Azure OpenAI deployment name
        """
    )
    
    parser.add_argument(
        '--repo-url',
        required=True,
        help='Azure DevOps repository URL (e.g., https://dev.azure.com/org/project/_git/repo)'
    )
    
    parser.add_argument(
        '--max-files',
        type=int,
        default=20,
        help='Maximum number of files to analyze (default: 20)'
    )
    
    parser.add_argument(
        '--focus-files',
        nargs='*',
        help='Specific files to focus on for analysis (e.g., main.py app.py)'
    )
    
    parser.add_argument(
        '--disable-llm',
        action='store_true',
        help='Disable LLM analysis (only perform repository analysis and file retrieval)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--demo-individual',
        action='store_true',
        help='Enable detailed individual file analysis demonstration'
    )
    
    parser.add_argument(
        '--demo-patterns',
        action='store_true',
        help='Enable detailed pattern analysis demonstration'
    )
    
    parser.add_argument(
        '--save-prompts',
        action='store_true',
        help='Save generated prompts to separate files for inspection'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate repository URL
    if not args.repo_url.startswith('https://dev.azure.com/'):
        print("❌ Error: Repository URL must be an Azure DevOps URL")
        print("   Example: https://dev.azure.com/myorg/myproject/_git/myrepo")
        sys.exit(1)
    
    try:
        # Create and run demo
        demo = LLMCodeAnalyzerDemo(
            repo_url=args.repo_url,
            enable_llm=not args.disable_llm,
            max_files=args.max_files,
            focus_files=args.focus_files
        )
        
        # Set demo options
        demo.demo_individual = args.demo_individual
        demo.demo_patterns = args.demo_patterns
        demo.save_prompts = args.save_prompts
        
        results = await demo.run_demo()
        
        # Exit with error code if there were errors
        if results.get('errors'):
            print(f"\n❌ Demo completed with {len(results['errors'])} errors")
            sys.exit(1)
        else:
            print("\n✅ Demo completed successfully!")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Demo failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    # Run the async main function
    asyncio.run(main())
