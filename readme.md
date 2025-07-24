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