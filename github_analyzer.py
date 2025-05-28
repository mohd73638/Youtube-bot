import os
import logging
from code_analyzer import CodeAnalyzer
import asyncio
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class GitHubAnalyzer:
    async def analyze_repository(self, repo_url):
        # Dummy implementation for testing
        return {
            "success": True,
            "data": {
                "repository": {
                    "name": "ExampleRepo",
                    "owner": "octocat",
                    "stars": 42,
                    "language": "Python"
                },
                "issues": [],
                "suggestions": ["Use type hints", "Add more unit tests"]
            }
        }

    async def check_api_status(self):
        # Dummy implementation for testing
        return True 
    
    def parse_repo_url(self, repo_url: str) -> tuple:
        """Parse GitHub repository URL to extract owner and repo name"""
        try:
            # Remove trailing slash and common suffixes
            repo_url = repo_url.rstrip('/').replace('.git', '')
            
            # Extract from different URL formats
            from urllib.parse import urlparse
            parsed_url = urlparse(repo_url)
            if parsed_url.hostname == "github.com":
                # Extract from https://github.com/owner/repo format
                parts = parsed_url.path.strip("/").split("/")
                if len(parts) >= 2:
                    owner = parts[0]
                    repo = parts[1]
                    return owner, repo
            
            raise ValueError(f"Invalid GitHub URL format: {repo_url}")
            
        except Exception as e:
            logger.error(f"Error parsing repository URL: {str(e)}")
            raise ValueError(f"Could not parse repository URL: {repo_url}")
    
    async def analyze_repository(self, repo_url: str) -> Dict[str, Any]:
        """Analyze a GitHub repository for code issues"""
        try:
            # Parse repository URL
            owner, repo_name = self.parse_repo_url(repo_url)
            logger.info(f"Analyzing repository: {owner}/{repo_name}")
            
            # Get repository from GitHub
            try:
                repo = self.github.get_repo(f"{owner}/{repo_name}")
            except GithubException as e:
                if e.status == 404:
                    return {
                        "success": False,
                        "error": f"Repository not found: {owner}/{repo_name}"
                    }
                elif e.status == 403:
                    return {
                        "success": False,
                        "error": "Access denied. Repository may be private or rate limit exceeded."
                    }
                else:
                    return {
                        "success": False,
                        "error": f"GitHub API error: {e.data.get('message', str(e))}"
                    }
            
            # Gather repository information
            repo_info = {
                "name": repo.name,
                "full_name": repo.full_name,
                "owner": repo.owner.login,
                "description": repo.description,
                "language": repo.language,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "open_issues": repo.open_issues_count,
                "size": repo.size,
                "created_at": repo.created_at.isoformat() if repo.created_at else None,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None
            }
            
            # Analyze repository contents
            analysis_result = await self._analyze_repository_contents(repo)
            
            return {
                "success": True,
                "data": {
                    "repository": repo_info,
                    "issues": analysis_result["issues"],
                    "suggestions": analysis_result["suggestions"],
                    "file_analysis": analysis_result["file_analysis"]
                }
            }
            
        except ValueError as e:
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error analyzing repository: {str(e)}")
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}"
            }
    
    async def _analyze_repository_contents(self, repo) -> Dict[str, Any]:
        """Analyze the contents of a repository"""
        issues = []
        suggestions = []
        file_analysis = {}
        
        try:
            # Get repository contents
            contents = repo.get_contents("")
            files_analyzed = 0
            max_files = 20  # Limit analysis to prevent timeout
            
            while contents and files_analyzed < max_files:
                file_content = contents.pop(0)
                
                try:
                    if file_content.type == "dir":
                        # Add directory contents to the queue
                        dir_contents = repo.get_contents(file_content.path)
                        contents.extend(dir_contents)
                        continue
                    
                    # Skip binary files and very large files
                    if file_content.size > 100000:  # Skip files larger than 100KB
                        continue
                    
                    # Analyze specific file types
                    file_extension = self._get_file_extension(file_content.name)
                    if not self._should_analyze_file(file_extension):
                        continue
                    
                    # Get file content
                    try:
                        file_data = file_content.decoded_content.decode("utf-8")
                    except (UnicodeDecodeError, Exception):
                        # Skip files that can't be decoded
                        continue
                    
                    # Analyze the file
                    file_issues = await self.code_analyzer.analyze_file(
                        file_content.name, 
                        file_data, 
                        file_extension
                    )
                    
                    if file_issues:
                        issues.extend(file_issues)
                        file_analysis[file_content.path] = len(file_issues)
                    
                    files_analyzed += 1
                    
                except Exception as e:
                    logger.warning(f"Error analyzing file {file_content.name}: {str(e)}")
                    continue
            
            # Generate general suggestions based on repository structure
            repo_suggestions = await self._generate_repository_suggestions(repo, file_analysis)
            suggestions.extend(repo_suggestions)
            
            logger.info(f"Analysis complete: {files_analyzed} files analyzed, {len(issues)} issues found")
            
        except Exception as e:
            logger.error(f"Error analyzing repository contents: {str(e)}")
            suggestions.append("Could not fully analyze repository contents due to access limitations")
        
        return {
            "issues": issues,
            "suggestions": suggestions,
            "file_analysis": file_analysis
        }
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename"""
        return filename.split(".")[-1].lower() if "." in filename else ""
    
    def _should_analyze_file(self, extension: str) -> bool:
        """Check if file should be analyzed based on extension"""
        analyzable_extensions = {
            "py", "js", "ts", "jsx", "tsx", "java", "cpp", "c", "h", 
            "cs", "php", "rb", "go", "rs", "swift", "kt", "scala",
            "html", "css", "scss", "less", "json", "xml", "yaml", "yml",
            "md", "txt", "sh", "bash", "sql", "dockerfile"
        }
        return extension in analyzable_extensions
    
    async def _generate_repository_suggestions(self, repo, file_analysis: Dict) -> List[str]:
        """Generate suggestions based on repository analysis"""
        suggestions = []
        
        try:
            # Check for common files
            contents = repo.get_contents("")
            file_names = [f.name.lower() for f in contents if f.type == "file"]
            
            # Check for README
            if not any("readme" in name for name in file_names):
                suggestions.append("Consider adding a README.md file to document your project")
            
            # Check for license
            if not any("license" in name for name in file_names):
                suggestions.append("Consider adding a LICENSE file to specify project licensing")
            
            # Check for gitignore
            if ".gitignore" not in file_names:
                suggestions.append("Consider adding a .gitignore file to exclude unnecessary files")
            
            # Check for CI/CD configuration
            ci_files = [".github", ".gitlab-ci.yml", "Jenkinsfile", ".travis.yml"]
            if not any(ci_file in file_names for ci_file in ci_files):
                suggestions.append("Consider setting up CI/CD pipeline for automated testing")
            
            # Language-specific suggestions
            if repo.language:
                lang_suggestions = self._get_language_specific_suggestions(repo.language.lower(), file_names)
                suggestions.extend(lang_suggestions)
            
            # Check repository statistics
            if repo.open_issues_count > 10:
                suggestions.append(f"High number of open issues ({repo.open_issues_count}). Consider addressing some issues")
            
            if file_analysis:
                total_issues = sum(file_analysis.values())
                if total_issues > 0:
                    suggestions.append(f"Found {total_issues} code issues across {len(file_analysis)} files")
            
        except Exception as e:
            logger.warning(f"Error generating repository suggestions: {str(e)}")
        
        return suggestions
    
    def _get_language_specific_suggestions(self, language: str, file_names: List[str]) -> List[str]:
        """Get language-specific suggestions"""
        suggestions = []
        
        if language == "python":
            if "requirements.txt" not in file_names and "pyproject.toml" not in file_names:
                suggestions.append("Consider adding requirements.txt or pyproject.toml for dependency management")
            if "setup.py" not in file_names and "pyproject.toml" not in file_names:
                suggestions.append("Consider adding setup.py or pyproject.toml for package configuration")
                
        elif language == "javascript" or language == "typescript":
            if "package.json" not in file_names:
                suggestions.append("Consider adding package.json for dependency management")
            if ".eslintrc" not in file_names and ".eslintrc.json" not in file_names:
                suggestions.append("Consider adding ESLint configuration for code quality")
                
        elif language == "java":
            if "pom.xml" not in file_names and "build.gradle" not in file_names:
                suggestions.append("Consider using Maven (pom.xml) or Gradle (build.gradle) for build management")
                
        elif language == "go":
            if "go.mod" not in file_names:
                suggestions.append("Consider adding go.mod for module management")
        
        return suggestions
