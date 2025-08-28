"""
Tests for CodeAnalyzer class
"""

import unittest
from unittest.mock import Mock, patch
import json

from src.code_analyzer import CodeAnalyzer


class TestCodeAnalyzer(unittest.TestCase):
    """Test cases for CodeAnalyzer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = CodeAnalyzer()
        
        self.sample_contents = [
            {
                'name': 'main.py',
                'path': 'main.py',
                'type': 'file',
                'size': 1500
            },
            {
                'name': 'utils.js',
                'path': 'src/utils.js',
                'type': 'file',
                'size': 800
            },
            {
                'name': 'README.md',
                'path': 'README.md',
                'type': 'file',
                'size': 1200
            },
            {
                'name': 'test_main.py',
                'path': 'tests/test_main.py',
                'type': 'file',
                'size': 600
            },
            {
                'name': 'package.json',
                'path': 'package.json',
                'type': 'file',
                'size': 400
            }
        ]
    
    def test_language_detection(self):
        """Test programming language detection"""
        # Test known extensions
        self.assertEqual(self.analyzer.LANGUAGE_EXTENSIONS['.py'], 'Python')
        self.assertEqual(self.analyzer.LANGUAGE_EXTENSIONS['.js'], 'JavaScript')
        self.assertEqual(self.analyzer.LANGUAGE_EXTENSIONS['.md'], 'Markdown')
    
    def test_analyze_repository_structure(self):
        """Test repository structure analysis"""
        result = self.analyzer.analyze_repository_structure(self.sample_contents)
        
        # Check basic counts
        self.assertEqual(result['total_files'], 5)
        self.assertEqual(result['total_size'], 4500)
        
        # Check language distribution
        self.assertIn('Python', result['languages'])
        self.assertIn('JavaScript', result['languages'])
        self.assertIn('Markdown', result['languages'])
        
        # Check file categorization
        self.assertIn('README.md', result['documentation_files'])
        self.assertIn('tests/test_main.py', result['test_files'])
        self.assertIn('package.json', result['config_files'])
    
    def test_categorize_special_files(self):
        """Test special file categorization"""
        analysis = {
            'config_files': [],
            'documentation_files': [],
            'test_files': [],
            'build_files': [],
            'source_files': []
        }
        
        # Test various file types
        test_cases = [
            ('package.json', 'package.json', 'config_files'),
            ('README.md', 'README.md', 'documentation_files'),
            ('test_utils.py', 'test_utils.py', 'test_files'),
            ('webpack.config.js', 'webpack.config.js', 'build_files'),
            ('main.py', 'main.py', 'source_files')
        ]
        
        for filename, filepath, expected_category in test_cases:
            self.analyzer._categorize_special_files(filename, filepath, analysis)
            self.assertIn(filepath, analysis[expected_category])
    
    def test_analyze_package_json(self):
        """Test package.json dependency analysis"""
        package_json_content = json.dumps({
            "name": "test-project",
            "dependencies": {
                "react": "^18.0.0",
                "express": "^4.18.0"
            },
            "devDependencies": {
                "jest": "^29.0.0",
                "webpack": "^5.0.0"
            }
        })
        
        dependencies = {
            'package_managers': [],
            'dependencies': {'npm': []},
            'dev_dependencies': {'npm': []},
            'frameworks': [],
            'build_tools': [],
            'testing_frameworks': []
        }
        
        self.analyzer._analyze_package_json(package_json_content, dependencies)
        
        # Check results
        self.assertIn('npm', dependencies['package_managers'])
        self.assertIn('react', dependencies['dependencies']['npm'])
        self.assertIn('express', dependencies['dependencies']['npm'])
        self.assertIn('jest', dependencies['dev_dependencies']['npm'])
        self.assertIn('webpack', dependencies['dev_dependencies']['npm'])
    
    def test_analyze_requirements_txt(self):
        """Test requirements.txt analysis"""
        requirements_content = """
django==4.2.0
requests>=2.28.0
# This is a comment
pytest==7.4.0
numpy==1.24.0
"""
        
        dependencies = {
            'package_managers': [],
            'dependencies': {'pip': []},
            'dev_dependencies': {'pip': []}
        }
        
        self.analyzer._analyze_requirements_txt(requirements_content, dependencies)
        
        # Check results
        self.assertIn('pip', dependencies['package_managers'])
        self.assertIn('django', dependencies['dependencies']['pip'])
        self.assertIn('requests', dependencies['dependencies']['pip'])
        self.assertIn('pytest', dependencies['dependencies']['pip'])
        self.assertIn('numpy', dependencies['dependencies']['pip'])
    
    def test_analyze_file_metrics(self):
        """Test file metrics analysis"""
        python_code = """
# This is a comment
import os

def hello_world():
    # Another comment
    print("Hello, World!")
    
    if True:
        print("Indented")

# Final comment
"""
        
        lines = python_code.strip().split('\n')
        metrics = self.analyzer._analyze_file_metrics(lines, 'Python')
        
        # Check metrics
        self.assertGreater(metrics['code_lines'], 0)
        self.assertGreater(metrics['comment_lines'], 0)
        self.assertGreater(metrics['max_indentation'], 0)
    
    def test_detect_project_type(self):
        """Test project type detection"""
        from pathlib import Path
        
        # Test Node.js project
        file_paths = [Path('package.json'), Path('src/index.js')]
        file_contents = {
            'package.json': '{"dependencies": {"react": "^18.0.0"}}'
        }
        
        project_type = self.analyzer._detect_project_type(file_paths, file_contents)
        self.assertEqual(project_type, 'Frontend Web Application')
        
        # Test Python project
        file_paths = [Path('requirements.txt'), Path('main.py')]
        file_contents = {
            'requirements.txt': 'django==4.2.0'
        }
        
        project_type = self.analyzer._detect_project_type(file_paths, file_contents)
        self.assertEqual(project_type, 'Django Web Application')
    
    def test_detect_architecture_patterns(self):
        """Test architecture pattern detection"""
        from pathlib import Path
        
        # Test MVC pattern
        file_paths = [
            Path('models/user.py'),
            Path('views/user_view.py'),
            Path('controllers/user_controller.py')
        ]
        
        patterns = self.analyzer._detect_architecture_patterns(file_paths, {})
        self.assertIn('MVC (Model-View-Controller)', patterns)
        
        # Test microservices pattern
        file_paths = [
            Path('docker-compose.yml'),
            Path('services/auth/main.py'),
            Path('services/user/main.py')
        ]
        
        patterns = self.analyzer._detect_architecture_patterns(file_paths, {})
        self.assertIn('Microservices', patterns)
    
    def test_framework_identification(self):
        """Test framework identification"""
        dependencies = {
            'frameworks': [],
            'testing_frameworks': [],
            'build_tools': []
        }
        
        packages = ['react', 'express', 'jest', 'webpack', 'django', 'pytest']
        self.analyzer._identify_frameworks(packages, dependencies)
        
        # Check results
        self.assertIn('React', dependencies['frameworks'])
        self.assertIn('Express.js', dependencies['frameworks'])
        self.assertIn('Django', dependencies['frameworks'])
        self.assertIn('Jest', dependencies['testing_frameworks'])
        self.assertIn('pytest', dependencies['testing_frameworks'])
        self.assertIn('Webpack', dependencies['build_tools'])


if __name__ == '__main__':
    unittest.main()
