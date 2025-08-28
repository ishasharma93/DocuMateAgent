"""
Tests for GitHubRepoSummarizer class
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json

from src.repo_summarizer import GitHubRepoSummarizer


class TestGitHubRepoSummarizer(unittest.TestCase):
    """Test cases for GitHubRepoSummarizer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.summarizer = GitHubRepoSummarizer()
        
        # Mock repository data
        self.mock_repo_info = {
            'name': 'test-repo',
            'full_name': 'testuser/test-repo',
            'description': 'A test repository',
            'url': 'https://github.com/testuser/test-repo',
            'language': 'Python',
            'languages': {'Python': 1000, 'JavaScript': 500},
            'stars': 42,
            'forks': 15,
            'size': 1024,
            'created_at': '2023-01-01',
            'updated_at': '2023-12-01'
        }
        
        self.mock_contents = [
            {
                'name': 'main.py',
                'path': 'main.py',
                'type': 'file',
                'size': 1500,
                'sha': 'abc123'
            },
            {
                'name': 'README.md',
                'path': 'README.md',
                'type': 'file',
                'size': 800,
                'sha': 'def456'
            },
            {
                'name': 'requirements.txt',
                'path': 'requirements.txt',
                'type': 'file',
                'size': 200,
                'sha': 'ghi789'
            }
        ]
    
    def test_initialization(self):
        """Test GitHubRepoSummarizer initialization"""
        summarizer = GitHubRepoSummarizer()
        
        self.assertIsNotNone(summarizer.github_client)
        self.assertIsNotNone(summarizer.code_analyzer)
        self.assertIsNotNone(summarizer.markdown_generator)
        self.assertEqual(summarizer.max_file_size, 1024*1024)
    
    def test_initialization_with_token(self):
        """Test initialization with GitHub token"""
        token = "test_token"
        summarizer = GitHubRepoSummarizer(github_token=token)
        
        self.assertEqual(summarizer.github_client.token, token)
    
    @patch('src.repo_summarizer.GitHubClient')
    def test_analyze_repository_quick(self, mock_client_class):
        """Test quick repository analysis"""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_repo = Mock()
        mock_client.get_repository.return_value = mock_repo
        mock_client.get_repository_info.return_value = self.mock_repo_info
        mock_client.get_repository_contents.return_value = self.mock_contents
        
        summarizer = GitHubRepoSummarizer()
        
        # Test quick analysis
        result = summarizer.analyze_repository(
            'https://github.com/testuser/test-repo',
            quick_analysis=True
        )
        
        # Verify results
        self.assertIn('repository_info', result)
        self.assertIn('structure_analysis', result)
        self.assertEqual(result['analysis_metadata']['quick_analysis'], True)
        
        # Verify GitHub client was called
        mock_client.get_repository.assert_called_once()
        mock_client.get_repository_info.assert_called_once()
        mock_client.get_repository_contents.assert_called_once()
    
    def test_filter_contents(self):
        """Test content filtering"""
        contents = [
            {'name': 'main.py', 'path': 'main.py', 'type': 'file', 'size': 1000},
            {'name': '__pycache__', 'path': '__pycache__/test.pyc', 'type': 'file', 'size': 500},
            {'name': 'node_modules', 'path': 'node_modules/package/index.js', 'type': 'file', 'size': 2000},
            {'name': 'large_file.txt', 'path': 'large_file.txt', 'type': 'file', 'size': 2*1024*1024},
            {'name': '.gitignore', 'path': '.gitignore', 'type': 'file', 'size': 100},
            {'name': 'test.py', 'path': 'test.py', 'type': 'file', 'size': 800}
        ]
        
        filtered = self.summarizer._filter_contents(contents)
        
        # Should keep main.py, .gitignore, and test.py
        # Should exclude __pycache__, node_modules, and large_file.txt
        self.assertEqual(len(filtered), 3)
        
        paths = [item['path'] for item in filtered]
        self.assertIn('main.py', paths)
        self.assertIn('.gitignore', paths)
        self.assertIn('test.py', paths)
        self.assertNotIn('__pycache__/test.pyc', paths)
        self.assertNotIn('node_modules/package/index.js', paths)
        self.assertNotIn('large_file.txt', paths)
    
    def test_prioritize_files(self):
        """Test file prioritization"""
        files = [
            {'path': 'src/utils.py', 'name': 'utils.py'},
            {'path': 'README.md', 'name': 'README.md'},
            {'path': 'package.json', 'name': 'package.json'},
            {'path': 'deep/nested/file.py', 'name': 'file.py'},
            {'path': 'test_file.py', 'name': 'test_file.py'}
        ]
        
        prioritized = self.summarizer._prioritize_files(files)
        
        # README.md and package.json should be at the top
        self.assertEqual(prioritized[0]['name'], 'README.md')
        self.assertEqual(prioritized[1]['name'], 'package.json')
    
    def test_set_configuration(self):
        """Test configuration updates"""
        initial_max_size = self.summarizer.max_file_size
        
        self.summarizer.set_configuration(
            max_file_size=2*1024*1024,
            max_files_to_analyze=1000
        )
        
        self.assertEqual(self.summarizer.max_file_size, 2*1024*1024)
        self.assertEqual(self.summarizer.max_files_to_analyze, 1000)
        self.assertNotEqual(self.summarizer.max_file_size, initial_max_size)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    @patch('src.repo_summarizer.GitHubRepoSummarizer')
    def test_quick_summary(self, mock_summarizer_class):
        """Test quick_summary convenience function"""
        from src.repo_summarizer import quick_summary
        
        mock_summarizer = Mock()
        mock_summarizer_class.return_value = mock_summarizer
        mock_summarizer.analyze_and_summarize.return_value = "Quick summary"
        
        result = quick_summary('https://github.com/test/repo')
        
        self.assertEqual(result, "Quick summary")
        mock_summarizer.analyze_and_summarize.assert_called_once_with(
            'https://github.com/test/repo',
            output_type='quick',
            quick_analysis=True
        )
    
    @patch('src.repo_summarizer.GitHubRepoSummarizer')
    def test_full_analysis(self, mock_summarizer_class):
        """Test full_analysis convenience function"""
        from src.repo_summarizer import full_analysis
        
        mock_summarizer = Mock()
        mock_summarizer_class.return_value = mock_summarizer
        mock_summarizer.analyze_and_summarize.return_value = "Full analysis"
        
        result = full_analysis('https://github.com/test/repo', 'output.md')
        
        self.assertEqual(result, "Full analysis")
        mock_summarizer.analyze_and_summarize.assert_called_once_with(
            'https://github.com/test/repo',
            output_file='output.md',
            output_type='full',
            quick_analysis=False
        )


if __name__ == '__main__':
    unittest.main()
