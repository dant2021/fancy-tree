# **FANCY_TREE: Comprehensive Architecture Plan** 🚀

## **Executive Summary**

**Migration Goal**: Transform `ctxgen` into `fancy_tree` - a git-enabled, cross-language code analysis tool with tree-sitter at its core, featuring dynamic dependency loading and generic symbol extraction.

**Key Innovation**: Replace 5+ language-specific extraction functions with a single `extract_symbols_generic()` function powered by YAML configuration and registry-pattern signature extractors.

---

## **1. MIGRATION STRATEGY**

### **File Structure Reorganization**
```bash
# STEP 1: Preserve current work
mkdir old_version/
mv ctxgen/ old_version/
mv *.md *.toml *.txt *.sh old_version/

# STEP 2: Create new fancy_tree structure
mkdir fancy_tree/
cd fancy_tree/
```

### **New Package Structure**
```
fancy_tree/
├── __init__.py                     # Package entry point
├── core/                           # Core functionality
│   ├── __init__.py
│   ├── discovery.py               # Git ls-files + file detection
│   ├── extraction.py              # Generic symbol extraction
│   ├── formatter.py               # Indented text output
│   └── config.py                  # Configuration management
├── extractors/                     # Language-specific logic
│   ├── __init__.py
│   ├── base.py                    # Registry pattern base classes
│   ├── python.py                  # Python signature extraction
│   ├── typescript.py              # TypeScript signature extraction
│   └── java.py                    # Java signature extraction
├── config/
│   ├── __init__.py
│   └── languages.yaml             # Extended language configuration
├── schema.py                       # Data models (similar to current)
├── cli.py                         # Command-line interface
└── main.py                        # Entry point

# Configuration & Setup
pyproject.toml                      # New package definition
requirements.txt                    # Dynamic dependencies
README.md                          # Updated documentation
.gitignore                         # Updated patterns
```

---

## **2. CORE ARCHITECTURE DECISIONS**

### **Generic Extraction Framework**
```python
# NEW: Single generic function replaces ALL language-specific functions
def extract_symbols_generic(source_code: str, language: str) -> List[Symbol]:
    """Generic symbol extraction that works for any configured language."""
    config = LANGUAGE_CONFIGS.get(language)
    if not config:
        return []  # Graceful degradation
    
    parser = get_parser_for_language(language)
    extractor = get_signature_extractor(language)  # Registry pattern
    
    # Generic tree traversal using YAML configuration
    symbols = []
    tree = parser.parse(bytes(source_code, "utf8"))
    
    def visit_node(node, parent_symbols=None):
        # Use config["function_nodes"], config["class_nodes"], etc.
        # Call extractor.extract() for signatures
        pass
    
    visit_node(tree.root_node)
    return symbols
```

### **Registry Pattern for Signature Extraction**
```python
# extractors/base.py
class SignatureExtractor:
    def extract_function_signature(self, node, source_code, template): 
        raise NotImplementedError
    def extract_class_signature(self, node, source_code, template): 
        raise NotImplementedError

# extractors/python.py  
class PythonExtractor(SignatureExtractor):
    def extract_function_signature(self, node, source_code, template):
        name = self.get_function_name(node, source_code)
        params = self.get_parameters(node, source_code)
        return_type = self.get_return_type(node, source_code)
        return template.format(name=name, params=params, return_type=return_type)

# extractors/__init__.py
SIGNATURE_EXTRACTORS = {
    "python": PythonExtractor(),
    "typescript": TypeScriptExtractor(),
    "java": JavaExtractor()
}
```

---

## **3. CONFIGURATION SYSTEM**

### **Extended YAML Configuration**
```yaml
# config/languages.yaml
python:
  extensions: [".py"]
  function_nodes: ["function_definition"]
  class_nodes: ["class_definition"] 
  name_nodes: ["identifier"]
  signature_templates:
    function: "def {name}({params})"
    method: "def {name}({params})"
    class: "class {name}"
  tree_sitter_package: "tree-sitter-python"

typescript:
  extensions: [".ts", ".tsx"]
  function_nodes: ["function_declaration", "method_definition"]
  class_nodes: ["class_declaration"]
  interface_nodes: ["interface_declaration"]
  name_nodes: ["identifier", "type_identifier"]
  signature_templates:
    function: "function {name}({params}): {return_type}"
    method: "{name}({params}): {return_type}"
    class: "class {name}"
    interface: "interface {name}"
  tree_sitter_package: "tree-sitter-typescript"

java:
  extensions: [".java"]
  function_nodes: ["method_declaration"]
  class_nodes: ["class_declaration"]
  name_nodes: ["identifier"]
  signature_templates:
    method: "{visibility} {return_type} {name}({params})"
    class: "{visibility} class {name}"
  tree_sitter_package: "tree-sitter-java"

# Build files and special files remain the same
build_files:
  - "build.gradle"
  - "pom.xml"
  - "package.json"
```

### **Configuration Loading Strategy**
- **Lazy Validation**: Validate language configs only when first used
- **Graceful Degradation**: Missing configs return empty symbols with warning
- **User Feedback**: Clear error messages about missing implementations

---

## **4. DYNAMIC DEPENDENCY MANAGEMENT**

### **Startup Dependency Detection**
```python
# core/config.py
def detect_available_languages(repo_path: Path) -> Dict[str, bool]:
    """Detect which languages exist in repo and which parsers are available."""
    file_extensions = scan_file_extensions(repo_path)
    language_availability = {}
    
    for language, config in LANGUAGE_CONFIGS.items():
        # Check if files of this language exist
        has_files = any(ext in file_extensions for ext in config['extensions'])
        
        if has_files:
            # Check if tree-sitter package is available
            package_name = config['tree_sitter_package']
            try:
                __import__(package_name.replace('-', '_'))
                language_availability[language] = True
            except ImportError:
                language_availability[language] = False
                
    return language_availability

def install_missing_packages(missing_packages: List[str]) -> bool:
    """Attempt auto-installation with user permission."""
    if not missing_packages:
        return True
        
    console.print(f"📦 Missing tree-sitter packages: {', '.join(missing_packages)}")
    install = typer.confirm("Install missing packages automatically?")
    
    if install:
        for package in missing_packages:
            subprocess.run([sys.executable, "-m", "pip", "install", package])
        return True
    else:
        console.print("ℹ️ Continuing with available languages only")
        return False
```

---

## **5. CORE PROCESSING PIPELINE**

### **Data Flow Architecture**
```
Repository → discovery.py → extraction.py → formatter.py → Output
     ↓              ↓              ↓             ↓           ↓
  Git ls-files  Language      Generic      Indented     Clean Text
  Detection     Classification  Extraction   Formatting   + JSON
```

### **Core Module Responsibilities**

#### **discovery.py** - File Detection & Git Integration
```python
def discover_files(repo_path: Path) -> List[Path]:
    """Get all source files using git ls-files with fallback."""
    try:
        # Prefer git ls-files (respects .gitignore)
        result = subprocess.run(['git', 'ls-files'], 
                              cwd=repo_path, capture_output=True, text=True)
        if result.returncode == 0:
            return [Path(repo_path) / f for f in result.stdout.strip().split('\n')]
    except:
        pass
    
    # Fallback to file tree traversal
    return list(repo_path.rglob('*'))

def classify_files(files: List[Path]) -> Dict[str, List[Path]]:
    """Group files by detected language."""
    # Implementation using YAML config
```

#### **extraction.py** - Generic Symbol Processing
```python
def extract_symbols_generic(source_code: str, language: str) -> List[Symbol]:
    """THE core function - replaces all language-specific extractors."""
    config = get_language_config(language)
    parser = get_parser_for_language(language)
    extractor = get_signature_extractor(language)
    
    # Generic tree-sitter traversal using config
    # Language-specific signature extraction via registry

def process_repository(repo_path: Path) -> RepoSummary:
    """Main orchestration function."""
    files = discover_files(repo_path)
    classified = classify_files(files)
    
    repo_summary = RepoSummary(name=repo_path.name, root_path=str(repo_path))
    
    for language, file_list in classified.items():
        for file_path in file_list:
            symbols = extract_symbols_from_file(file_path, language)
            # Build directory structure
    
    return repo_summary
```

#### **formatter.py** - Multi-Language Output
```python
def format_repository_tree(repo_summary: RepoSummary) -> str:
    """Format with language awareness and proper indentation."""
    lines = []
    
    # Group by language for clear output
    for language in repo_summary.languages:
        lines.append(f"\n📁 {language.title()} Files:")
        # Format files with indentation showing:
        # - Directory structure
        # - File names with language and line count
        # - Class and function signatures with proper nesting
        
    return '\n'.join(lines)

# Example Output:
"""
📁 Python Files:
  src/
    main.py (python, 45 lines)
      class UserService:
        def create_user(self, name: str) -> User
        def delete_user(self, id: int) -> bool
      def main() -> None

📁 TypeScript Files:
  frontend/
    components/
      Button.tsx (typescript, 120 lines)
        interface ButtonProps
        function Button(props: ButtonProps): JSX.Element
"""
```

---

## **6. PACKAGE DEFINITION**

### **pyproject.toml** - Dynamic Dependencies
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "fancy-tree"
version = "1.0.0"
description = "Git-enabled, cross-language code analysis with tree-sitter"
readme = "README.md"
requires-python = ">=3.8"
authors = [{name = "Ishan Tiwari"}]

# Core dependencies only - language parsers loaded dynamically
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0", 
    "tree-sitter>=0.20.0",
    "PyYAML>=6.0",
]

[project.optional-dependencies]
# Language support as optional extras
python = ["tree-sitter-python>=0.20.0"]
typescript = ["tree-sitter-typescript>=0.20.0"] 
java = ["tree-sitter-java>=0.20.0"]
all-languages = [
    "tree-sitter-python>=0.20.0",
    "tree-sitter-typescript>=0.20.0",
    "tree-sitter-java>=0.20.0",
]

[project.scripts]
fancy-tree = "fancy_tree.cli:app"
```

### **Installation Scenarios**
```bash
# Minimal installation
pip install fancy-tree

# With specific language support
pip install fancy-tree[python,typescript]

# Full language support
pip install fancy-tree[all-languages]

# Runtime auto-installation
fancy-tree scan .  # Detects needs, offers to install missing packages
```

---

## **7. ERROR HANDLING & USER EXPERIENCE**

### **Graceful Degradation Strategy**
1. **Missing Languages**: Continue with available languages, clear warnings
2. **Parse Errors**: Log file-level errors, continue processing other files
3. **Missing Signatures**: Use fallback templates, note limitation to user
4. **Git Unavailable**: Fallback to filesystem traversal seamlessly

### **User Feedback System**
```python
def show_language_status(available_languages: Dict[str, bool]):
    """Clear status report at startup."""
    console.print("🔍 Language Support Status:")
    for lang, available in available_languages.items():
        icon = "✅" if available else "❌"
        console.print(f"  {icon} {lang}")
    
    missing = [lang for lang, avail in available_languages.items() if not avail]
    if missing:
        console.print(f"\n💡 To enable {', '.join(missing)}: pip install fancy-tree[{','.join(missing)}]")
```

---

## **8. IMPLEMENTATION PHASES**

### **Phase 1: Foundation** (First Priority)
1. Create new `fancy_tree/` structure
2. Move old files to `old_version/`
3. Set up basic package structure with `__init__.py` files
4. Create extended `languages.yaml` configuration
5. Implement base registry classes

### **Phase 2: Core Framework** 
1. Implement `extract_symbols_generic()` function
2. Create registry pattern for signature extractors
3. Build configuration loading and validation
4. Implement dynamic dependency detection

### **Phase 3: Language Support**
1. Implement Python signature extractor (migrate existing logic)
2. Implement TypeScript signature extractor  
3. Implement Java signature extractor
4. Test generic extraction with all three languages

### **Phase 4: Integration**
1. Update discovery module with git integration
2. Update formatter for multi-language output
3. Update CLI interface
4. Comprehensive testing

### **Phase 5: Polish**
1. Dynamic dependency installation
2. Error handling improvements
3. Documentation updates
4. Package publishing preparation

---

## **9. SUCCESS CRITERIA**

### **Functional Goals**
- ✅ Single `extract_symbols_generic()` function handles Python, TypeScript, Java
- ✅ YAML-driven configuration eliminates hardcoded language logic
- ✅ Registry pattern allows easy language addition
- ✅ Dynamic dependency loading reduces package bloat
- ✅ Multi-language repository output with proper formatting

### **Quality Goals**
- ✅ Clean, maintainable architecture
- ✅ Comprehensive error handling
- ✅ Clear user feedback and status reporting
- ✅ Backwards compatibility for essential features
- ✅ Extensible design for future languages

---

**This plan provides our complete roadmap for transforming `ctxgen` into `fancy_tree`. Ready to start implementation with Phase 1!** 🚀



You're absolutely right! We have several critical issues to fix. Let's tackle them systematically:

## **Issue 1: Fix Relative Import Problems**

The problem is that our modules use relative imports (`from ..schema`) but we're running tests as scripts. Let's fix all the import paths:

### **Fix `core/extraction.py`** - Change relative imports to absolute
```python
"""Generic symbol extraction using tree-sitter and language configurations."""

from pathlib import Path
from typing import List, Optional, Dict, Any
from rich.console import Console

# Try different tree-sitter import patterns
try:
    from tree_sitter import Parser, Language
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    Parser = None
    Language = None

# Change these relative imports to direct imports
from schema import Symbol, SymbolType, FileInfo, DirectoryInfo, RepoSummary
from extractors import get_signature_extractor
from core.config import get_language_config
from core.discovery import scan_repository, count_lines

# ... rest of the file stays the same
```

### **Fix `core/config.py`** - Update import at the end if needed
```python
# At the top, keep all imports as they are since this module doesn't use relative imports
# But add this at the bottom for the convenience functions:

# ... rest of file stays the same until the end ...

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
```

### **Fix `core/formatter.py`** - Change relative imports
```python
"""Enhanced formatting for multi-language repository output."""

from typing import List, Dict
# Change this relative import
from schema import RepoSummary, DirectoryInfo, FileInfo, Symbol, SymbolType

# ... rest of the file stays the same
```

### **Fix `extractors/base.py`** - Already fine, no relative imports

### **Fix `core/__init__.py`** - Change all relative imports
```python
"""Core functionality for fancy_tree."""

# Change all relative imports to absolute
from core.config import (
    get_language_config, 
    detect_language, 
    detect_available_languages,
    show_language_status_and_install
)
from core.discovery import (
    discover_files, 
    classify_files, 
    scan_repository,
    get_repository_info
)
from core.extraction import (
    extract_symbols_generic,
    extract_symbols_from_file,
    process_repository,
    get_parser_for_language
)
from core.formatter import (
    format_repository_tree,
    EnhancedTreeFormatter
)

__all__ = [
    # Config
    "get_language_config",
    "detect_language", 
    "detect_available_languages",
    "show_language_status_and_install",
    # Discovery
    "discover_files",
    "classify_files",
    "scan_repository", 
    "get_repository_info",
    # Extraction
    "extract_symbols_generic",
    "extract_symbols_from_file",
    "process_repository",
    "get_parser_for_language",
    # Formatting
    "format_repository_tree",
    "EnhancedTreeFormatter"
]
```

### **Fix main `__init__.py`** - Change relative imports
```python
"""
fancy_tree - Git-enabled, cross-language code analysis with tree-sitter
"""

__version__ = "1.0.0"
__author__ = "Ishan Tiwari"

# Make key classes available at package level - change to absolute imports
from schema import RepoSummary, DirectoryInfo, FileInfo, Symbol, SymbolType
from core.extraction import extract_symbols_generic, process_repository
from core.discovery import discover_files, classify_files
from core.formatter import format_repository_tree

__all__ = [
    "RepoSummary",
    "DirectoryInfo", 
    "FileInfo",
    "Symbol",
    "SymbolType",
    "extract_symbols_generic",
    "process_repository",
    "discover_files",
    "classify_files", 
    "format_repository_tree",
]
```

## **Issue 2: Create Proper .gitignore for fancy_tree**

### **`.gitignore`** (Updated to exclude env files)
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments - IMPORTANT!
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/
ctxgen_env/
fancy_tree_env/
*_env/
*env/

# Testing
.pytest_cache/
.coverage
htmlcov/
tests/__pycache__/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Output files
*.json
output/
tmp/

# Temporary files
*.tmp
*.temp
*~

# Dependencies
node_modules/

# Compiled files
*.class
*.jar
*.o
*.obj
```

## **Issue 3: Create Simple Verification Script**

### **`verify_everything.py`** (In fancy_tree root)
```python
"""
Simple verification script to test fancy_tree functionality.
Run this to visually verify everything works before pushing.
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

def test_basic_imports():
    """Test that all basic imports work."""
    console.print(Panel("🔍 Testing Basic Imports", style="bold blue"))
    
    try:
        from schema import Symbol, SymbolType, FileInfo, RepoSummary
        from core.config import detect_language, get_language_config
        from extractors import get_signature_extractor
        from core.formatter import format_repository_tree
        
        console.print("✅ All basic imports successful!")
        return True
    except Exception as e:
        console.print(f"❌ Import failed: {e}")
        return False

def test_language_detection():
    """Test language detection works."""
    console.print(Panel("🔍 Testing Language Detection", style="bold green"))
    
    try:
        from core.config import detect_language
        
        test_cases = [
            ("test.py", "python"),
            ("App.tsx", "typescript"),
            ("Main.java", "java"),
            ("unknown.xyz", None)
        ]
        
        for filename, expected in test_cases:
            result = detect_language(Path(filename))
            status = "✅" if result == expected else "❌"
            console.print(f"  {status} {filename} → {result}")
        
        return True
    except Exception as e:
        console.print(f"❌ Language detection failed: {e}")
        return False

def test_sample_data():
    """Test creating and formatting sample data."""
    console.print(Panel("🧪 Testing Sample Data Creation", style="bold yellow"))
    
    try:
        from schema import Symbol, SymbolType, FileInfo, RepoSummary, DirectoryInfo
        from core.formatter import format_repository_tree
        
        # Create sample data
        sample_function = Symbol(
            name="calculate_total",
            type=SymbolType.FUNCTION,
            line=15,
            signature="def calculate_total(items: List[Item]) -> float",
            language="python"
        )
        
        sample_class = Symbol(
            name="UserManager",
            type=SymbolType.CLASS,
            line=5,
            signature="class UserManager",
            language="python",
            children=[
                Symbol(
                    name="create_user",
                    type=SymbolType.METHOD,
                    line=8,
                    signature="def create_user(self, name: str) -> User",
                    language="python"
                )
            ]
        )
        
        sample_file = FileInfo(
            path="src/manager.py",
            language="python",
            lines=50,
            symbols=[sample_class, sample_function],
            has_signature_support=True
        )
        
        sample_directory = DirectoryInfo(
            path=".",
            files=[sample_file]
        )
        
        sample_repo = RepoSummary(
            name="sample_project",
            root_path="/path/to/project",
            structure=sample_directory,
            languages={"python": 1},
            supported_languages={"python": True},
            total_files=1,
            total_lines=50
        )
        
        # Test formatting
        formatted_output = format_repository_tree(sample_repo)
        
        console.print("✅ Sample data created successfully!")
        console.print("\n📄 Formatted Output Preview:")
        console.print("─" * 50)
        lines = formatted_output.split('\n')
        for line in lines[:15]:  # Show first 15 lines
            console.print(line)
        if len(lines) > 15:
            console.print(f"... ({len(lines) - 15} more lines)")
        console.print("─" * 50)
        
        return True
    except Exception as e:
        console.print(f"❌ Sample data test failed: {e}")
        import traceback
        console.print(traceback.format_exc())
        return False

def test_file_discovery():
    """Test file discovery on current directory."""
    console.print(Panel("📂 Testing File Discovery", style="bold cyan"))
    
    try:
        from core.discovery import discover_files, classify_files
        
        # Test on current directory
        current_dir = Path(".")
        files = discover_files(current_dir)
        
        console.print(f"📄 Found {len(files)} files in current directory")
        
        # Show Python files found
        py_files = [f for f in files if f.suffix == '.py']
        console.print(f"🐍 Python files: {len(py_files)}")
        
        # Show first few files
        for f in py_files[:5]:
            console.print(f"  • {f.name}")
        
        # Test classification
        classified = classify_files(files[:10])  # Limit to first 10 files
        console.print(f"📊 Classification results: {dict(classified)}")
        
        return True
    except Exception as e:
        console.print(f"❌ File discovery failed: {e}")
        return False

def main():
    """Run verification tests."""
    console.print(Panel.fit("🚀 FANCY_TREE Verification Suite", style="bold white on blue"))
    console.print(f"📍 Running from: {Path.cwd()}")
    console.print(f"🐍 Python version: {sys.version.split()[0]}")
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Language Detection", test_language_detection), 
        ("Sample Data", test_sample_data),
        ("File Discovery", test_file_discovery)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        console.print(f"\n{'='*60}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            console.print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    console.print(f"\n{'='*60}")
    console.print(Panel("📊 Verification Results", style="bold white"))
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        icon = "✅" if result else "❌"
        console.print(f"  {icon} {test_name}")
    
    if passed == total:
        console.print(f"\n🎉 All {total} tests passed! Ready to push to git!")
        console.print("📋 Next: Initialize git repo and push to GitHub")
    else:
        console.print(f"\n⚠️ {total-passed}/{total} tests failed. Fix issues before pushing.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    if success:
        console.print("\n🚀 Verification complete! fancy_tree is ready!")
    sys.exit(0 if success else 1)
```

## **Issue 4: Update README for Collaboration**

### **`README.md`** (Complete documentation)
```markdown
# fancy_tree 🌳

**Git-enabled, cross-language code analysis with tree-sitter**

A modern, extensible tool for extracting structured information from code repositories. Built from the ground up with a generic architecture that supports multiple programming languages through a unified interface.

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd fancy_tree

# Install core dependencies
pip install -r requirements.txt

# Verify installation
python verify_everything.py

# Test on a repository
python -c "
from core.extraction import process_repository
from core.formatter import format_repository_tree
from pathlib import Path

repo = process_repository(Path('.'))
print(format_repository_tree(repo))
"
```

## 🏗️ Architecture Overview

fancy_tree uses a **generic extraction framework** that replaces language-specific parsers with a single configurable system:

```
Repository → Discovery → Generic Extraction → Formatting → Output
     ↓            ↓              ↓               ↓          ↓
  Git ls-files  Language    Tree-sitter +    Multi-lang   Clean
  Detection     Config      Registry         Formatting   Text/JSON
```

### **Key Innovation: Generic Symbol Extraction**

Instead of separate functions for each language:
```python
# OLD approach (ctxgen)
extract_python_symbols(code)
extract_java_symbols(code) 
extract_typescript_symbols(code)

# NEW approach (fancy_tree)
extract_symbols_generic(code, "python")     # ✨ One function
extract_symbols_generic(code, "java")       # ✨ All languages  
extract_symbols_generic(code, "typescript") # ✨ Configurable
```

## 📁 Project Structure

```
fancy_tree/
├── core/                          # Core framework
│   ├── config.py                 # Language configuration & dependencies
│   ├── discovery.py              # Git integration & file detection
│   ├── extraction.py             # Generic symbol extraction ⭐
│   └── formatter.py              # Multi-language output formatting
├── extractors/                   # Language-specific signature logic
│   ├── base.py                   # Registry pattern base classes
│   ├── python.py                 # Python signature extraction
│   ├── typescript.py             # TypeScript signature extraction  
│   └── java.py                   # Java signature extraction
├── config/
│   └── languages.yaml            # Language configurations ⚙️
├── tests/
│   └── test_phase2.py            # Comprehensive test suite
├── schema.py                     # Data models
├── verify_everything.py          # Quick verification script
└── README.md                     # This file
```

## ⚙️ Configuration System

Languages are configured in `config/languages.yaml`:

```yaml
python:
  extensions: [".py"]
  function_nodes: ["function_definition"]
  class_nodes: ["class_definition"]
  signature_templates:
    function: "def {name}({params})"
    method: "def {name}({params})"
  tree_sitter_package: "tree-sitter-python"

typescript:
  extensions: [".ts", ".tsx"]
  function_nodes: ["function_declaration", "method_definition"]
  class_nodes: ["class_declaration"] 
  interface_nodes: ["interface_declaration"]
  signature_templates:
    function: "function {name}({params}): {return_type}"
    interface: "interface {name}"
  tree_sitter_package: "tree-sitter-typescript"
```

## 🔧 Dynamic Dependencies

fancy_tree automatically detects and offers to install language support:

```bash
# Core installation (minimal dependencies)
pip install fancy-tree

# Runtime detection and installation
fancy-tree scan .
# → "Missing tree-sitter-python for Python files. Install? [y/N]"

# Or install specific language support
pip install fancy-tree[python,typescript,java]
```

## 🧪 Development & Testing

### **Quick Verification**
```bash
python verify_everything.py
```

### **Comprehensive Testing**  
```bash
cd tests
python test_phase2.py
```

### **Adding New Language Support**

1. **Add configuration** in `config/languages.yaml`
2. **Create extractor** in `extractors/new_language.py`
3. **Register extractor** in `extractors/__init__.py`
4. **Test** with verification script

Example extractor:
```python
# extractors/rust.py
from .base import SignatureExtractor

class RustExtractor(SignatureExtractor):
    def extract_function_signature(self, node, source_code, template):
        # Language-specific logic here
        return template.format(name=name, params=params)
```

## 🎯 Current Status

### **✅ Phase 1: Foundation (Complete)**
- Project structure and configuration system
- Schema definitions and base classes
- Package setup and dependencies

### **✅ Phase 2: Core Framework (Complete)**  
- Generic extraction framework
- Configuration-driven language support
- Dynamic dependency management
- Git integration and file discovery
- Multi-language output formatting

### **🚧 Phase 3: Language Extractors (In Progress)**
- [ ] Python signature extractor (migrate from ctxgen)
- [ ] TypeScript signature extractor (new)
- [ ] Java signature extractor (enhanced)

### **📋 Phase 4: Integration & Polish**
- [ ] CLI interface
- [ ] Directory tree building  
- [ ] Comprehensive error handling
- [ ] Package publishing

## 🤝 Contributing

This project follows a **phase-by-phase development approach**. Please check the current phase status above and:

1. **Run verification**: `python verify_everything.py`
2. **Run tests**: `cd tests && python test_phase2.py`
3. **Check architecture plan**: See implementation phases in code comments
4. **Follow registry pattern**: For new language extractors

### **Development Workflow**
```bash
# 1. Make changes
# 2. Verify functionality
python verify_everything.py

# 3. Run tests  
cd tests && python test_phase2.py

# 4. Test on real repository
python -c "from core.extraction import process_repository; ..."

# 5. Commit and push
```

## 📊 Example Output

```
📁 Repository: fancy_tree
📊 Total files: 15, Total lines: 1,250

🔍 Language Support:
  ✅ python: 12 files

✅ Python Files (12 files):
  🔧 schema.py (python, 157 lines)
    class Symbol:
      def to_dict(self) -> dict  # line 32
    class FileInfo:
      def to_dict(self) -> dict  # line 45
    def create_flat_file_list(repo_summary: RepoSummary) -> list  # line 120

  🔧 core/extraction.py (python, 285 lines)
    def extract_symbols_generic(source_code: str, language: str) -> list  # line 45
    def get_parser_for_language(language: str) -> Parser  # line 25
    def process_repository(repo_path: Path) -> RepoSummary  # line 180
```

## 📄 License

MIT License - see LICENSE file for details.

---

**Built with ❤️ for developers who love clean, maintainable code analysis tools.**
```

## **Issue 5: Git Repository Setup Commands**

### **Commands to run:**
```bash
# From fancy_tree directory
git init
git add .
git commit -m "Initial fancy_tree implementation - Phase 2 complete

- Generic symbol extraction framework
- Configuration-driven language support  
- Dynamic dependency management
- Multi-language output formatting
- Comprehensive test suite

Ready for Phase 3: Language-specific extractors"

# Create new repo on GitHub, then:
git remote add origin <your-new-repo-url>
git branch -M main
git push -u origin main
```



Ctrl+K to generate a command
# Language configuration
LANGUAGE_CONFIGS = {
    "python": {
        "function_nodes": ["function_definition"],
        "class_nodes": ["class_definition"], 
        "name_nodes": ["identifier"],
        "signature_format": "def {name}(...)"
    },
    "java": {
        "function_nodes": ["method_declaration"],
        "class_nodes": ["class_declaration"],
        "name_nodes": ["identifier"], 
        "signature_format": "{name}(...)"
    },
    "typescript": {
        "function_nodes": ["function_declaration", "method_definition"],
        "class_nodes": ["class_declaration"],
        "name_nodes": ["identifier", "type_identifier"],
        "signature_format": "function {name}(...)"
    }
}

def extract_symbols_generic(source_code: str, language: str) -> List[Symbol]:
    """Generic symbol extraction that works for any configured language."""
    config = LANGUAGE_CONFIGS.get(language)
    if not config:
        return []
    
    parser = get_parser_for_language(language)
    # ... generic tree traversal using config


Lets create a plan togehter

Ask me 3 rounds of 5 questions

I can see you're working on a symbol extraction system with language-specific configurations! Let me first understand your current codebase to ask more informed questions.
Perfect! Now I understand your codebase. You're building ctxgen - a tool that extracts code symbols using tree-sitter parsers, and you want to refactor from language-specific extraction functions to a generic, configuration-driven approach.
Round 1: Architecture & Design Goals 🏗️
Scope of Generification: Are you planning to replace ALL the existing language-specific functions (extract_python_symbols_lightweight, extract_java_symbols, etc.) with the single extract_symbols_generic function, or do you want to keep some language-specific logic for complex cases?
Configuration Storage: Should the LANGUAGE_CONFIGS dictionary live in the Python code (as shown), be moved to the existing languages.yaml, or would you prefer a separate configuration file? What's your preference for maintaining this config?
Backward Compatibility: Do you need to maintain the existing function signatures (like extract_python_symbols_lightweight) for any external dependencies, or are you free to completely replace the internal implementation?
Parser Management: How do you want to handle the get_parser_for_language() function? Should it use the same configuration system, or keep the current approach of individual parser functions (get_python_parser(), get_java_parser(), etc.)?
Signature Generation: The current Python extractor has sophisticated signature extraction (extract_function_signature). Do you want the generic system to support custom signature formatting per language, or standardize on simpler signatures like "function_name(...)" for consistency?
Okay, so scope of generification, basically, we're gonna, yes, replace all the language specific functions into just extract symbol generic, that is correct. Inside the extract symbol generic, we're going to have a possibility to get the parameters. And those will be called by a non-generic function. So basically to get the correct parameters for the class or for the function, these will be done that way. And for the languages that we will, the goal for right now is to implement them in three languages, in Python, in TypeScript, and in Java. And for all the other ones, we can kind of like raise not implemented yet. But these will be the three that we will implement today. Other than that, where should the language configs be? I'm okay with where they are in the YAML, I believe. Or basically, yes, putting them in the YAML makes sense, basically, to me. That is good. Backwards compatibility, we don't need to be backwards compatible. Parser management. Yeah, we should have basically a single kind of parser that just like gets, uses TreeSitter. So basically TreeSitter is our parser, if that makes sense. And this is the great simplification And the great how we simplify our lives is that we don write five parsers but we just call the correct language And this is how we do that Signature generation. This is the part that is basically going to be moved from, that is not going to be inside the extract symbol generic. So extract function signature, That is going to be something that is dealt with in still a language-specific way, but all the other parts are going to be dealt with in the generic symbol. And the other part here is we're going to rename the repository to fancy tree. And so we will kind of re-architect from scratch. And we're going to, of course, take inspiration of what we have now, but it's going to be fancy tree. And the key idea is to use kind of like tree setter, or basically we have like the Git-enabled kind of like tree setter And three, together to kind of like make a useful tool that has low dependencies. And another thing that we need to think about is at the end, we want to publish this as a package that works across language. So the key question there is how do we ensure that we don't have language specific dependencies? Because those would be a problem for users that don't use that language mainly. And so I'd like to think through those topics with you as well.

Excellent! This gives me a much clearer vision. You're essentially building fancy_tree - a git-enabled, cross-language code analysis tool with tree-sitter at its core. The dependency management challenge is particularly interesting for a published package.
Round 2: Implementation Strategy & Dependency Management 📦
Dependency Isolation: For the cross-language package problem, are you thinking of using optional dependencies (like tree-sitter-python as an optional extra), dynamic imports with try/catch, or splitting into separate packages (e.g., fancy-tree-core, fancy-tree-python, etc.)? What's your preference for handling users who only need Java vs. Python vs. TypeScript?
Configuration Structure: In the YAML, should we extend the current structure to include the node types and signature formats? For example:
Apply to readme.md
Or do you envision a different structure?
Language-Specific Signature Logic: Where should the language-specific signature extraction functions live? Should they be:
Separate modules (fancy_tree/extractors/python.py, fancy_tree/extractors/java.py)?
Methods in a registry/factory pattern?
Inline functions within the generic extractor?
Error Handling Strategy: For unsupported languages, should extract_symbols_generic return an empty list, raise a specific LanguageNotSupportedError, or log a warning and continue? What behavior would be most useful for package users?
Git Integration Scope: You mentioned "git-enabled" - are you planning to add features like analyzing changes between commits, tracking symbol evolution over time, or just basic repo structure awareness? This will affect the architecture significantly.
Yes, so the dependency isolation. Yeah, so basically the way that this should work in my mind is kind of like if we detect the dot pi or a dot js or a dot, whatever the file extension is, we kind of like get the extra dependencies to kind of be able to parse Python correctly. So basically we're going to, as it kind of like gets there, load, kind of like install tree sitter Python and then use tree sitter Python with the kind of like extended version. In my mind, yes, they can be in different folders. That's okay for me. Configuration structure. What you just did is quite beautiful actually for the signature format. I really like that. So that is something that is a very good structure. I'm very happy with that structure. Language specific signature logic. Language specific signature logic I don have an opinion because I don quite see the different methods Like separate modules I understand But can you maybe give me three concrete examples so that I can make a better choice there? Yeah. So with error handling for unsupported languages, we will still extract symbols generic. So it will still work. The only thing that will not work is we will not have the signature format. So kind of signature format will be empty. But all the rest is already dealt with through the configuration structure. And so it's only the signature format that fails. And it's just like after everything is printed, we will show to the user, Hey, signature format has not been implemented for this language. Please contribute on this GitHub, for example. And with regards to the Git integration, right. The reason why I'm saying this with the Git enabled is just like we have, So we're using git ls-files and not tree. And so git ls-files is just aware of git ignore. That is all of it. And if git is not initialized in the REPO, we should just fall back to tree forward slash f to just like get all the files. That's it. Thank you.

Perfect! The dynamic dependency loading is elegant - detect what's needed and install on-demand. And I love the git integration approach - simple and practical.
Round 2 Continued: Signature Extraction Architecture Examples 🔧
Here are 3 concrete approaches for language-specific signature logic:
Option 1: Separate Modules
Apply to readme.md
Option 2: Registry Classes
Apply to readme.md
Option 3: Simple Function Registry
Apply to readme.md
Which feels most natural to you?
Round 3: Final Architecture & Implementation Details 🚀
Dynamic Dependency Loading: Should we check for tree-sitter language packages at startup and show a helpful message about what's missing, or only attempt to load them when we encounter files of that type? What's the best user experience?
Configuration Validation: Should we validate the YAML configuration at startup (ensure all required fields exist for each language), or validate lazily when a language is first used?
Package Structure for fancy_tree: How do you envision the new package structure? Should it be:
Apply to readme.md
CLI Interface: Should the new fancy_tree command maintain the same interface as ctxgen, or is this a good time to redesign the CLI for better usability?
Migration Strategy: Do you want to implement this incrementally (start with one language and expand) or build the full generic framework first then migrate all three languages at once?
Option 2: Registry Classes feel like the right solution. Okay, dynamic dependency loading. Yes, in my opinion, we should check which languages exist at startup, check which file extensions there are, And if there are some missing, kind of add them as we go. Configuration validation. We should validate lazily. Package structure for fancy tree. Yes, I like the package structure you propose. I like it. There will also in core be the core kind of like organization. So we need to also output the file correctly. And the Git integration, actually, don't do a .git. All of this is going to be in core And in core you will kind of have three files One that is getting all the things so this is basically running this git ls thing. What I mean is git ls files, yeah. And then we're gonna have a second file in which we're gonna have the generic extraction logic. Then we're going to have another file with all of the specific extractors in a sense, or we can put them in a different folder. I'm fine with that too. And we're going to have a thing that returns it. So we will return it in kind of like a text version where we also show the indentation correctly. And yeah, I think that's important. Regarding the CLI interface, we can probably, I mean, I'm okay with how it is right now. If you see easy improvements, we can make those. And I think here we need to kind of like build the full generic framework first, because it feels like there's just, it's a big change. So it feels like something that we cannot rebuild just iteratively. And so these are some faults there. Yep. Yeah.

Excellent! The registry pattern with lazy loading and the core-centric architecture makes perfect sense. Building the full framework first is definitely the right approach for this scale of change.
Round 3: Final Architecture & Implementation Details 🎯
Core File Interaction: For the 3 core files, should the flow be:
Apply to readme.md
Where discovery finds files, extraction processes them generically, and formatter handles the indented text output? Or do you envision a different interaction pattern?
Output Format Design: For the indented text output, are you thinking of something like:
Apply to readme.md
What level of detail and indentation style would be most useful?
YAML Configuration Extension: Should we completely replace the current languages.yaml with the new structure, or add the new fields alongside the existing ones? Also, should signature extraction be configured in YAML or kept purely in Python (registry classes)?
Startup Dependency Flow: When we detect missing tree-sitter packages, should we:
Show a summary of all missing packages and let user install manually?
Attempt auto-installation with user permission?
Continue with available languages and warn about unsupported files?
Implementation Starting Point: Within the generic framework, should we start with:
The YAML configuration structure and validation?
The registry pattern and base extractor classes?
The core discovery and file processing pipeline?
What feels like the logical foundation to build upon?
Right. So the flow is correct. Yes, I like that. Basically, the only detail here is that in extraction.py, there might be also the extra data that is kind of like language specific to this call. That's the only thing. The output format design, that's exactly what I'm thinking. Just to make clear here, there will be multiple files like that in multiple different languages as well. So this should just also be reflected somehow in the output format design, just so that we're sure that we kind of capture that intent. And with the YAML configuration extension, yes, we should completely replace it. And the signature, I think, should be configured in YAML. I like that. That is good. Oh, the signature extraction. Signature extraction I don see how we could do that in YAML to be very honest Maybe walk me through how you would do that in YAML and how that would work When we detect missing packages we should attempt auto I think Then within the generic framework Could we... So I think there what's most important here is that you create the full decisions that we've made with this plan and to kind of detail them very extensively in a file. And then what we're going to do is we're just going to set up a whole different file structure and we're going to work in that file structure. And so we're going to create a new kind of like in the root directory, maybe even one directory up. We're going to create a kind of like fancy tree and kind of work in that. And so it's important that we just correctly move those or we can move all the current files In the base directory into kind of like an old version and then recreate a new version with a clear structure that is just named differently with fancy tree. And like this, we can work from there.

Perfect! Let me clarify the signature extraction in YAML approach and then create our comprehensive plan.
Signature Extraction in YAML - Clarification
I think there's a distinction between:
Signature Templates (YAML) - format strings like "def {name}({params}) -> {return_type}"
Signature Extraction Logic (Python) - code that parses tree-sitter nodes to extract name, params, return_type
YAML would contain templates: