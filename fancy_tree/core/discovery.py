"""File discovery and repository scanning with git integration."""

import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple, Union
from rich.console import Console

from .config import detect_language, config_manager

console = Console()


def discover_files(repo_path: Path, include_ignored: bool = False) -> List[Path]:
    """Discover all source files using git ls-files with fallback."""
    repo_path = Path(repo_path).resolve()
    
    if not repo_path.exists():
        raise ValueError(f"Repository path does not exist: {repo_path}")
    
    files = []
    
    # Try git ls-files first (respects .gitignore)
    if not include_ignored:
        git_files = _get_git_files(repo_path)
        if git_files is not None:
            console.print(f"Using git ls-files: found {len(git_files)} tracked files")
            return git_files
    
    # Fallback to filesystem traversal
    console.print("Git not available, using filesystem traversal")
    fs_files = _get_filesystem_files(repo_path)
    console.print(f"Found {len(fs_files)} files via filesystem scan")
    return fs_files


def _get_git_files(repo_path: Path) -> Optional[List[Path]]:
    """Get files using git ls-files."""
    try:
        result = subprocess.run(
            ['git', 'ls-files'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            files = []
            for file_line in result.stdout.strip().split('\n'):
                if file_line.strip():
                    file_path = repo_path / file_line.strip()
                    if file_path.exists() and file_path.is_file():
                        files.append(file_path)
            return files
        else:
            console.print(f"Git command failed: {result.stderr}")
            return None
            
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
        console.print(f"Git not available: {e}")
        return None


def _get_filesystem_files(repo_path: Path) -> List[Path]:
    """Get files using filesystem traversal with ignore patterns."""
    config_manager.load_config()
    ignore_patterns = config_manager.ignore_patterns
    
    files = []
    
    def should_ignore(path: Path) -> bool:
        """Check if path should be ignored based on patterns."""
        path_str = str(path)
        path_name = path.name
        
        for pattern in ignore_patterns:
            if pattern.startswith('*'):
                # Pattern like "*.pyc"
                if path_name.endswith(pattern[1:]):
                    return True
            elif pattern in path_str:
                # Pattern like "__pycache__" or "node_modules"
                return True
        
        return False
    
    for file_path in repo_path.rglob('*'):
        if file_path.is_file() and not should_ignore(file_path):
            files.append(file_path)
    
    return files


def classify_files(
    files: List[Path], 
    *, 
    return_unclassified: bool = False
) -> Union[Tuple[Dict[str, List[Path]], List[Path]], Dict[str, List[Path]]]:
    """Group files by detected language."""
    classified = {}
    unclassified = []
    
    for file_path in files:
        language = detect_language(file_path)
        
        if language:
            if language not in classified:
                classified[language] = []
            classified[language].append(file_path)
        else:
            unclassified.append(file_path)
    
    # Report classification results
    total_classified = sum(len(files) for files in classified.values())
    console.print(f"Classified {total_classified} files, {len(unclassified)} unclassified")
    
    for language, lang_files in classified.items():
        console.print(f"  {language}: {len(lang_files)} files")
    
    if return_unclassified:
        return classified, unclassified
    return classified

def count_lines(file_path: Path) -> int:
    """Count lines in a file safely."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return len(f.readlines())
    except Exception:
        return 0


def filter_files_by_language(files: List[Path], target_languages: List[str]) -> List[Path]:
    """Filter files to include only specific languages."""
    if not target_languages:
        return files
    
    filtered = []
    for file_path in files:
        language = detect_language(file_path)
        if language in target_languages:
            filtered.append(file_path)
    
    return filtered


def get_repository_info(repo_path: Path) -> Dict[str, any]:
    """Get basic repository information."""
    repo_path = Path(repo_path).resolve()
    
    # Try to get git repository name
    repo_name = repo_path.name
    
    try:
        # Check if it's a git repository and get origin URL
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            origin_url = result.stdout.strip()
            # Extract repo name from URL
            if origin_url.endswith('.git'):
                repo_name = Path(origin_url).stem
            else:
                repo_name = Path(origin_url).name
    except:
        pass  # Use directory name as fallback
    
    # Get current git branch
    current_branch = None
    try:
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            current_branch = result.stdout.strip()
    except:
        pass
    
    return {
        "name": repo_name,
        "path": str(repo_path),
        "is_git_repo": (repo_path / ".git").exists(),
        "current_branch": current_branch
    }


def scan_repository(repo_path: Path, 
                   language_filter: Optional[List[str]] = None,
                   max_files: Optional[int] = None,
                   include_ignored: bool = False) -> Dict[str, any]:
    """Complete repository scan with classification and filtering."""
    
    console.print(f"Scanning repository: {repo_path}")
    
    # Get repository info
    repo_info = get_repository_info(repo_path)
    console.print(f"Repository: {repo_info['name']}")
    if repo_info['current_branch']:
        console.print(f"Branch: {repo_info['current_branch']}")
    
    # Discover files
    all_files = discover_files(repo_path, include_ignored)
    
    # Apply language filter
    if language_filter:
        all_files = filter_files_by_language(all_files, language_filter)
        console.print(f"Filtered to {len(all_files)} files for languages: {', '.join(language_filter)}")
    
    # Apply file limit
    if max_files and len(all_files) > max_files:
        all_files = all_files[:max_files]
        console.print(f"Limited to {max_files} files")
    
    # Classify by language
    classified_files = classify_files(all_files)
    
    # Calculate statistics
    total_lines = 0
    for file_path in all_files:
        total_lines += count_lines(file_path)
    
    return {
        "repo_info": repo_info,
        "files": all_files,
        "classified_files": classified_files,
        "total_files": len(all_files),
        "total_lines": total_lines,
        "language_counts": {lang: len(files) for lang, files in classified_files.items()}
    }