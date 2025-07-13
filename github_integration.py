import os
import git
import shutil
import requests
from typing import Dict, List, Optional
from urllib.parse import urlparse
import tempfile
import logging

logger = logging.getLogger(__name__)

class GitHubIntegration:
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
        self.headers = {}
        
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"
            self.headers["Accept"] = "application/vnd.github.v3+json"
    
    def validate_repo_url(self, repo_url: str) -> bool:
        """Validate if the repository URL is accessible"""
        try:
            parsed = urlparse(repo_url)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # For GitHub, check if repo exists
            if "github.com" in parsed.netloc:
                return self._check_github_repo_exists(repo_url)
            
            # For other Git providers, try to clone (dry run)
            return self._test_git_access(repo_url)
            
        except Exception as e:
            logger.error(f"Error validating repo URL {repo_url}: {e}")
            return False
    
    def _check_github_repo_exists(self, repo_url: str) -> bool:
        """Check if GitHub repository exists using API"""
        try:
            # Extract owner and repo from URL
            parts = repo_url.replace("https://github.com/", "").replace(".git", "").split("/")
            if len(parts) < 2:
                return False
            
            owner, repo = parts[0], parts[1]
            
            # Call GitHub API
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            response = requests.get(api_url, headers=self.headers)
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error checking GitHub repo: {e}")
            return False
    
    def _test_git_access(self, repo_url: str) -> bool:
        """Test Git access by attempting to list remote references"""
        try:
            # Create a temporary directory for testing
            with tempfile.TemporaryDirectory() as temp_dir:
                # Try to list remote references
                git.cmd.Git().ls_remote(repo_url)
                return True
                
        except Exception as e:
            logger.error(f"Error testing Git access: {e}")
            return False
    
    def clone_repository(self, repo_url: str, target_dir: str, branch: str = "main") -> bool:
        """Clone repository to target directory"""
        try:
            # Remove target directory if it exists
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            
            # Clone repository
            logger.info(f"Cloning repository {repo_url} to {target_dir}")
            
            # Try different branch names
            branches_to_try = [branch, "main", "master", "develop"]
            
            for branch_name in branches_to_try:
                try:
                    repo = git.Repo.clone_from(
                        repo_url, 
                        target_dir, 
                        branch=branch_name,
                        depth=1  # Shallow clone for faster operation
                    )
                    logger.info(f"Successfully cloned repository on branch '{branch_name}'")
                    return True
                except git.GitCommandError as e:
                    if "Remote branch" in str(e) and "not found" in str(e):
                        continue
                    else:
                        raise
            
            logger.error(f"Failed to clone repository on any branch: {branches_to_try}")
            return False
            
        except Exception as e:
            logger.error(f"Error cloning repository: {e}")
            return False
    
    def pull_latest_changes(self, repo_dir: str) -> bool:
        """Pull latest changes from repository"""
        try:
            if not os.path.exists(repo_dir):
                logger.error(f"Repository directory does not exist: {repo_dir}")
                return False
            
            repo = git.Repo(repo_dir)
            
            # Fetch latest changes
            origin = repo.remotes.origin
            origin.fetch()
            
            # Pull changes
            origin.pull()
            
            logger.info(f"Successfully pulled latest changes for {repo_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error pulling latest changes: {e}")
            return False
    
    def get_repository_info(self, repo_url: str) -> Dict[str, str]:
        """Get repository information"""
        try:
            if "github.com" in repo_url:
                return self._get_github_repo_info(repo_url)
            else:
                return self._get_generic_repo_info(repo_url)
                
        except Exception as e:
            logger.error(f"Error getting repository info: {e}")
            return {}
    
    def _get_github_repo_info(self, repo_url: str) -> Dict[str, str]:
        """Get GitHub repository information using API"""
        try:
            # Extract owner and repo from URL
            parts = repo_url.replace("https://github.com/", "").replace(".git", "").split("/")
            if len(parts) < 2:
                return {}
            
            owner, repo = parts[0], parts[1]
            
            # Call GitHub API
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            response = requests.get(api_url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "name": data.get("name", ""),
                    "description": data.get("description", ""),
                    "language": data.get("language", ""),
                    "stars": str(data.get("stargazers_count", 0)),
                    "forks": str(data.get("forks_count", 0)),
                    "default_branch": data.get("default_branch", "main"),
                    "last_updated": data.get("updated_at", "")
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting GitHub repo info: {e}")
            return {}
    
    def _get_generic_repo_info(self, repo_url: str) -> Dict[str, str]:
        """Get generic repository information"""
        try:
            # For non-GitHub repos, we can only extract basic info from URL
            parsed = urlparse(repo_url)
            repo_name = os.path.basename(parsed.path).replace(".git", "")
            
            return {
                "name": repo_name,
                "description": "",
                "language": "",
                "stars": "0",
                "forks": "0",
                "default_branch": "main",
                "last_updated": ""
            }
            
        except Exception as e:
            logger.error(f"Error getting generic repo info: {e}")
            return {}
    
    def detect_test_frameworks(self, repo_dir: str) -> List[str]:
        """Detect which test frameworks are used in the repository"""
        frameworks = []
        
        try:
            # Check for pytest
            if self._has_pytest_tests(repo_dir):
                frameworks.append("pytest")
            
            # Check for Cucumber
            if self._has_cucumber_tests(repo_dir):
                frameworks.append("cucumber")
            
            # Check for Robot Framework
            if self._has_robot_tests(repo_dir):
                frameworks.append("robot")
            
        except Exception as e:
            logger.error(f"Error detecting test frameworks: {e}")
        
        return frameworks
    
    def _has_pytest_tests(self, repo_dir: str) -> bool:
        """Check if repository has pytest tests"""
        try:
            # Look for test files
            for root, dirs, files in os.walk(repo_dir):
                for file in files:
                    if file.startswith("test_") and file.endswith(".py"):
                        return True
                    if file.endswith("_test.py"):
                        return True
            
            # Check for pytest.ini or setup.cfg
            pytest_configs = ["pytest.ini", "setup.cfg", "pyproject.toml"]
            for config in pytest_configs:
                if os.path.exists(os.path.join(repo_dir, config)):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for pytest tests: {e}")
            return False
    
    def _has_cucumber_tests(self, repo_dir: str) -> bool:
        """Check if repository has Cucumber tests"""
        try:
            # Look for .feature files
            for root, dirs, files in os.walk(repo_dir):
                for file in files:
                    if file.endswith(".feature"):
                        return True
            
            # Check for cucumber configuration files
            cucumber_configs = ["cucumber.yml", "cucumber.json", "features"]
            for config in cucumber_configs:
                if os.path.exists(os.path.join(repo_dir, config)):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for Cucumber tests: {e}")
            return False
    
    def _has_robot_tests(self, repo_dir: str) -> bool:
        """Check if repository has Robot Framework tests"""
        try:
            # Look for .robot files
            for root, dirs, files in os.walk(repo_dir):
                for file in files:
                    if file.endswith(".robot") or file.endswith(".txt"):
                        # Check if it's actually a Robot Framework file
                        file_path = os.path.join(root, file)
                        if self._is_robot_file(file_path):
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for Robot Framework tests: {e}")
            return False
    
    def _is_robot_file(self, file_path: str) -> bool:
        """Check if a file is a Robot Framework test file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Look for Robot Framework keywords
            robot_keywords = [
                "*** Test Cases ***",
                "*** Keywords ***",
                "*** Variables ***",
                "*** Settings ***",
                "Library    ",
                "Resource    ",
                "Test Setup",
                "Test Teardown"
            ]
            
            for keyword in robot_keywords:
                if keyword in content:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if file is Robot Framework: {e}")
            return False
    
    def get_test_directories(self, repo_dir: str) -> Dict[str, List[str]]:
        """Get directories containing tests for each framework"""
        test_dirs = {
            "pytest": [],
            "cucumber": [],
            "robot": []
        }
        
        try:
            for root, dirs, files in os.walk(repo_dir):
                # Skip .git and other hidden directories
                if "/.git" in root or "/__pycache__" in root or "/node_modules" in root:
                    continue
                
                has_pytest = any(f.startswith("test_") and f.endswith(".py") for f in files)
                has_cucumber = any(f.endswith(".feature") for f in files)
                has_robot = any(f.endswith(".robot") or (f.endswith(".txt") and self._is_robot_file(os.path.join(root, f))) for f in files)
                
                if has_pytest:
                    test_dirs["pytest"].append(root)
                if has_cucumber:
                    test_dirs["cucumber"].append(root)
                if has_robot:
                    test_dirs["robot"].append(root)
        
        except Exception as e:
            logger.error(f"Error getting test directories: {e}")
        
        return test_dirs 