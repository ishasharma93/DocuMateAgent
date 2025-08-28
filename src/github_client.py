"""
GitHub API Client

Handles authentication and interaction with GitHub's REST API.
"""

import os
from typing import Optional, Dict, List, Any
from github import Github, Repository
from github.GithubException import GithubException
import logging

logger = logging.getLogger(__name__)


class GitHubClient:
    """Client for interacting with GitHub API"""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub client
        
        Args:
            token: GitHub personal access token. If not provided, will look for GITHUB_TOKEN env var
        """
        self.token = token or os.getenv('GITHUB_TOKEN')
        if not self.token:
            logger.warning("No GitHub token provided. API rate limits will be lower.")
            self.github = Github()
        else:
            self.github = Github(self.token)
    
    def get_repository(self, repo_url: str) -> Repository.Repository:
        """
        Get repository object from URL
        
        Args:
            repo_url: GitHub repository URL (e.g., https://github.com/owner/repo)
            
        Returns:
            Repository object
            
        Raises:
            ValueError: If URL format is invalid
            GithubException: If repository not found or access denied
        """
        try:
            # Extract owner/repo from URL
            if repo_url.startswith('https://github.com/'):
                repo_path = repo_url.replace('https://github.com/', '').rstrip('/')
            elif '/' in repo_url and not repo_url.startswith('http'):
                repo_path = repo_url
            else:
                raise ValueError(f"Invalid repository URL format: {repo_url}")
            
            if repo_path.count('/') != 1:
                raise ValueError(f"Invalid repository path format: {repo_path}")
            
            return self.github.get_repo(repo_path)
            
        except GithubException as e:
            logger.error(f"GitHub API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting repository: {e}")
            raise
    
    def get_repository_contents(self, repo: Repository.Repository, path: str = "") -> List[Dict[str, Any]]:
        """
        Get repository contents recursively
        
        Args:
            repo: Repository object
            path: Path within repository to start from
            
        Returns:
            List of file/directory information
        """
        contents = []
        
        try:
            items = repo.get_contents(path)
            if not isinstance(items, list):
                items = [items]
                
            for item in items:
                content_info = {
                    'name': item.name,
                    'path': item.path,
                    'type': item.type,
                    'size': item.size,
                    'sha': item.sha
                }
                
                if item.type == 'file':
                    content_info['download_url'] = item.download_url
                    contents.append(content_info)
                elif item.type == 'dir':
                    contents.append(content_info)
                    # Recursively get directory contents
                    try:
                        sub_contents = self.get_repository_contents(repo, item.path)
                        contents.extend(sub_contents)
                    except Exception as e:
                        logger.warning(f"Could not access directory {item.path}: {e}")
                        
        except GithubException as e:
            logger.error(f"Error getting contents for path {path}: {e}")
            raise
            
        return contents
    
    def get_file_content(self, repo: Repository.Repository, file_path: str) -> Optional[str]:
        """
        Get content of a specific file
        
        Args:
            repo: Repository object
            file_path: Path to file within repository
            
        Returns:
            File content as string, or None if unable to read
        """
        try:
            file_content = repo.get_contents(file_path)
            if file_content.encoding == 'base64':
                import base64
                return base64.b64decode(file_content.content).decode('utf-8')
            else:
                return file_content.decoded_content.decode('utf-8')
        except Exception as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return None
    
    def get_repository_info(self, repo: Repository.Repository) -> Dict[str, Any]:
        """
        Get basic repository information
        
        Args:
            repo: Repository object
            
        Returns:
            Dictionary with repository metadata
        """
        try:
            return {
                'name': repo.name,
                'full_name': repo.full_name,
                'description': repo.description,
                'url': repo.html_url,
                'clone_url': repo.clone_url,
                'language': repo.language,
                'languages': repo.get_languages(),
                'stars': repo.stargazers_count,
                'forks': repo.forks_count,
                'watchers': repo.watchers_count,
                'size': repo.size,
                'default_branch': repo.default_branch,
                'created_at': repo.created_at,
                'updated_at': repo.updated_at,
                'pushed_at': repo.pushed_at,
                'topics': repo.get_topics(),
                'license': repo.license.name if repo.license else None,
                'has_issues': repo.has_issues,
                'has_projects': repo.has_projects,
                'has_wiki': repo.has_wiki,
                'archived': repo.archived,
                'disabled': repo.disabled,
                'private': repo.private
            }
        except Exception as e:
            logger.error(f"Error getting repository info: {e}")
            return {}
    
    def get_commit_activity(self, repo: Repository.Repository, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent commit activity
        
        Args:
            repo: Repository object
            limit: Maximum number of commits to retrieve
            
        Returns:
            List of commit information
        """
        try:
            commits = repo.get_commits()[:limit]
            commit_info = []
            
            for commit in commits:
                commit_info.append({
                    'sha': commit.sha[:8],
                    'message': commit.commit.message.split('\n')[0],  # First line only
                    'author': commit.commit.author.name,
                    'date': commit.commit.author.date,
                    'url': commit.html_url
                })
                
            return commit_info
        except Exception as e:
            logger.warning(f"Could not get commit activity: {e}")
            return []
    
    def get_rate_limit(self) -> Dict[str, Any]:
        """
        Get current API rate limit status
        
        Returns:
            Rate limit information
        """
        try:
            rate_limit = self.github.get_rate_limit()
            return {
                'core': {
                    'limit': rate_limit.core.limit,
                    'remaining': rate_limit.core.remaining,
                    'reset': rate_limit.core.reset
                },
                'search': {
                    'limit': rate_limit.search.limit,
                    'remaining': rate_limit.search.remaining,
                    'reset': rate_limit.search.reset
                }
            }
        except Exception as e:
            logger.error(f"Error getting rate limit: {e}")
            return {}
