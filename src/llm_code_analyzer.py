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
import aiohttp
from dataclasses import dataclass

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
                 api_base: Optional[str] = None):
        """
        Initialize LLM Code Analyzer
        
        Args:
            api_key: OpenAI API key or other LLM provider key
            model: Model to use (gpt-4, gpt-3.5-turbo, claude, etc.)
            api_base: Custom API base URL for other providers
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.api_base = api_base or "https://api.openai.com/v1"
        
        if not self.api_key:
            logger.warning("No LLM API key provided. Code explanations will be limited.")
        
        # Configuration
        self.max_code_length = int(os.getenv('MAX_CODE_LENGTH_FOR_LLM', 8000))
        self.max_concurrent_requests = int(os.getenv('MAX_CONCURRENT_LLM_REQUESTS', 3))
        
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
        if not self.api_key:
            logger.warning("No API key available, skipping LLM analysis")
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
        max_files = int(os.getenv('MAX_FILES_FOR_LLM_ANALYSIS', 15))
        
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
        Call the LLM API with the analysis prompt
        
        Args:
            prompt: The analysis prompt
            
        Returns:
            LLM response text
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert software engineer who provides clear, detailed code analysis and explanations."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 1500,
            "temperature": 0.1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"LLM API error {response.status}: {error_text}")
                
                result = await response.json()
                return result['choices'][0]['message']['content']
    
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
        if not explanations:
            return {
                'total_files_analyzed': 0,
                'complexity_distribution': {},
                'common_patterns': [],
                'key_technologies': [],
                'improvement_themes': [],
                'architecture_insights': []
            }
        
        # Analyze complexity distribution
        complexity_counts = {}
        for explanation in explanations.values():
            complexity = explanation.complexity_assessment.split(' ')[0]  # Get first word
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
        
        # Find common patterns
        all_patterns = []
        for explanation in explanations.values():
            all_patterns.extend(explanation.code_patterns)
        
        pattern_counts = {}
        for pattern in all_patterns:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        common_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Analyze dependencies/technologies
        all_dependencies = []
        for explanation in explanations.values():
            all_dependencies.extend(explanation.dependencies)
        
        dependency_counts = {}
        for dep in all_dependencies:
            dependency_counts[dep] = dependency_counts.get(dep, 0) + 1
        
        key_technologies = sorted(dependency_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Common improvement themes
        all_improvements = []
        for explanation in explanations.values():
            all_improvements.extend(explanation.improvement_suggestions)
        
        improvement_counts = {}
        for improvement in all_improvements:
            # Simple keyword extraction for themes
            if 'test' in improvement.lower():
                improvement_counts['Testing'] = improvement_counts.get('Testing', 0) + 1
            if 'error' in improvement.lower() or 'exception' in improvement.lower():
                improvement_counts['Error Handling'] = improvement_counts.get('Error Handling', 0) + 1
            if 'performance' in improvement.lower():
                improvement_counts['Performance'] = improvement_counts.get('Performance', 0) + 1
            if 'documentation' in improvement.lower() or 'comment' in improvement.lower():
                improvement_counts['Documentation'] = improvement_counts.get('Documentation', 0) + 1
        
        return {
            'total_files_analyzed': len(explanations),
            'complexity_distribution': complexity_counts,
            'common_patterns': [pattern for pattern, count in common_patterns],
            'key_technologies': [tech for tech, count in key_technologies],
            'improvement_themes': list(improvement_counts.keys()),
            'architecture_insights': []  # Could be enhanced with more analysis
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
