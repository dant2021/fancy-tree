"""Configuration management and dynamic dependency detection."""

import subprocess
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from rich.console import Console
import typer

console = Console()

class LanguageConfig:
    """Configuration for a single language."""
    
    def __init__(self, language: str, config_dict: Dict[str, Any]):
        self.language = language
        self.extensions = config_dict.get("extensions", [])
        self.function_nodes = config_dict.get("function_nodes", [])
        self.class_nodes = config_dict.get("class_nodes", [])
        self.interface_nodes = config_dict.get("interface_nodes", [])
        self.name_nodes = config_dict.get("name_nodes", ["identifier"])
        self.signature_templates = config_dict.get("signature_templates", {})
        self.tree_sitter_package = config_dict.get("tree_sitter_package", f"tree-sitter-{language}")
        self.language_function = config_dict.get("language_function", "language")
    
    def get_template(self, symbol_type: str) -> str:
        """Get signature template for symbol type with fallback."""
        return self.signature_templates.get(symbol_type, f"{symbol_type} {{name}}")
    
    def __repr__(self):
        return f"LanguageConfig({self.language}, {len(self.extensions)} extensions)"


class ConfigManager:
    """Manages language configurations and dependencies."""
    
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "languages.yaml"
        
        self.config_path = config_path
        self.languages: Dict[str, LanguageConfig] = {}
        self.build_files: List[str] = []
        self.ignore_patterns: List[str] = []
        self._loaded = False
    
    def load_config(self) -> None:
        """Load language configuration from YAML."""
        if self._loaded:
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Load language configurations
            for lang_name, lang_config in config.items():
                if lang_name in ['build_files', 'ignore_patterns']:
                    continue
                
                if isinstance(lang_config, dict) and 'extensions' in lang_config:
                    self.languages[lang_name] = LanguageConfig(lang_name, lang_config)
            
            # Load special configurations
            self.build_files = config.get('build_files', [])
            self.ignore_patterns = config.get('ignore_patterns', [])
            
            self._loaded = True
            
        except (FileNotFoundError, yaml.YAMLError) as e:
            console.print(f"Warning: Could not load language config: {e}")
    
    def get_language_config(self, language: str) -> Optional[LanguageConfig]:
        """Get configuration for specific language."""
        self.load_config()
        return self.languages.get(language)
    
    def detect_language_from_extension(self, file_path: Path) -> Optional[str]:
        """Detect language from file extension."""
        self.load_config()
        file_ext = file_path.suffix.lower()
        
        for lang_name, lang_config in self.languages.items():
            if file_ext in lang_config.extensions:
                return lang_name
        
        return None
    
    def scan_file_extensions(self, repo_path: Path) -> Set[str]:
        """Scan repository for file extensions."""
        extensions = set()
        
        try:
            # Use git ls-files if available
            result = subprocess.run(
                ['git', 'ls-files'], 
                cwd=repo_path, 
                capture_output=True, 
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                for file_line in result.stdout.strip().split('\n'):
                    if file_line.strip():
                        ext = Path(file_line).suffix.lower()
                        if ext:
                            extensions.add(ext)
            else:
                # Fallback to file system scan
                for file_path in repo_path.rglob('*'):
                    if file_path.is_file():
                        ext = file_path.suffix.lower()
                        if ext:
                            extensions.add(ext)
                            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception):
            # Fallback to file system scan
            for file_path in repo_path.rglob('*'):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext:
                        extensions.add(ext)
        
        return extensions
    
    def detect_available_languages(self, repo_path: Path) -> Dict[str, Dict[str, Any]]:
        """Detect which languages exist in repo and which parsers are available."""
        self.load_config()
        file_extensions = self.scan_file_extensions(repo_path)
        language_availability = {}
        
        for lang_name, lang_config in self.languages.items():
            # Check if files of this language exist
            has_files = any(ext in file_extensions for ext in lang_config.extensions)
            
            if has_files:
                # Check if tree-sitter package is available
                package_name = lang_config.tree_sitter_package
                module_name = package_name.replace('-', '_')
                
                try:
                    __import__(module_name)
                    parser_available = True
                except ImportError:
                    parser_available = False
                
                language_availability[lang_name] = {
                    "has_files": has_files,
                    "parser_available": parser_available,
                    "package_name": package_name,
                    "file_count": len([ext for ext in file_extensions if ext in lang_config.extensions])
                }
        
        return language_availability
    
    def install_missing_packages(self, missing_packages: List[str]) -> bool:
        """Attempt auto-installation with user permission."""
        if not missing_packages:
            return True
        
        console.print(f"Missing tree-sitter packages for optimal support:")
        for package in missing_packages:
            console.print(f"  - {package}")
        
        install = typer.confirm("Install missing packages automatically?")
        
        if install:
            console.print("Installing packages...")
            success_count = 0
            
            for package in missing_packages:
                try:
                    console.print(f"Installing {package}...")
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", package],
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    
                    if result.returncode == 0:
                        console.print(f"SUCCESS: {package} installed successfully")
                        success_count += 1
                    else:
                        console.print(f"ERROR: Failed to install {package}: {result.stderr}")
                        
                except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
                    console.print(f"ERROR: Error installing {package}: {e}")
            
            if success_count == len(missing_packages):
                console.print("SUCCESS: All packages installed successfully!")
                return True
            else:
                console.print(f"WARNING: {success_count}/{len(missing_packages)} packages installed")
                return False
        else:
            console.print("INFO: Continuing with available languages only")
            return False
    
    def show_language_status(self, language_availability: Dict[str, Dict[str, Any]]) -> None:
        """Display language support status."""
        console.print("Language Support Status:")
        
        if not language_availability:
            console.print("  No supported languages detected in repository")
            return
        
        missing_packages = []
        
        for lang, info in language_availability.items():
            has_files = info["has_files"]
            parser_available = info["parser_available"] 
            file_count = info.get("file_count", 0)
            
            if has_files:
                if parser_available:
                    console.print(f"  SUPPORTED: {lang}: {file_count} files (parser available)")
                else:
                    console.print(f"  NOT_SUPPORTED: {lang}: {file_count} files (parser missing)")
                    missing_packages.append(info["package_name"])
        
        if missing_packages:
            console.print(f"\nTIP: To enable full support: pip install {' '.join(missing_packages)}")
            return missing_packages
        else:
            console.print("\nSUCCESS: All detected languages have parser support!")
            return []


# Global config manager instance
config_manager = ConfigManager()

# Convenience functions
def get_language_config(language: str) -> Optional[LanguageConfig]:
    """Get language configuration."""
    return config_manager.get_language_config(language)

def detect_language(file_path: Path) -> Optional[str]:
    """Detect language from file path."""
    return config_manager.detect_language_from_extension(file_path)

def detect_available_languages(repo_path: Path) -> Dict[str, Dict[str, Any]]:
    """Detect available languages in repository."""
    return config_manager.detect_available_languages(repo_path)

def show_language_status_and_install(repo_path: Path) -> Dict[str, Dict[str, Any]]:
    """Show language status and offer to install missing packages."""
    availability = config_manager.detect_available_languages(repo_path)
    missing_packages = config_manager.show_language_status(availability)
    
    if missing_packages:
        config_manager.install_missing_packages(missing_packages)
        # Re-check availability after installation
        availability = config_manager.detect_available_languages(repo_path)
    
    return availability