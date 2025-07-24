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

from ..schema import Symbol, SymbolType, FileInfo, DirectoryInfo, RepoSummary
from ..extractors import get_signature_extractor
from .config import get_language_config
from .discovery import scan_repository, count_lines

console = Console()

# Parser cache to avoid recreating parsers
_parser_cache: Dict[str, Optional[Parser]] = {}


def get_parser_for_language(language: str) -> Optional[Parser]:
    """Get tree-sitter parser for language with caching and dynamic loading."""
    if not TREE_SITTER_AVAILABLE:
        console.print("⚠️ Tree-sitter not available")
        return None
    
    if language in _parser_cache:
        return _parser_cache[language]
    
    config = get_language_config(language)
    if not config:
        console.print(f"⚠️ No configuration found for language: {language}")
        _parser_cache[language] = None
        return None
    
    package_name = config.tree_sitter_package
    module_name = package_name.replace('-', '_')
    
    try:
        # Dynamic import of tree-sitter language module
        language_module = __import__(module_name, fromlist=['language'])
        
        # Try different API patterns for tree-sitter
        parser = Parser()
        
        # Method 1: New API with Language wrapper
        try:
            language_func = getattr(language_module, 'language')
            if callable(language_func):
                # Try new API: Language(capsule, name)
                try:
                    language_obj = Language(language_func(), name=language)
                except TypeError:
                    # Try old API: Language(capsule) 
                    try:
                        language_obj = Language(language_func())
                    except:
                        # Direct assignment
                        language_obj = language_func()
            else:
                language_obj = language_func
            
            parser.language = language_obj
            
        except Exception as api_error:
            console.print(f"❌ API error for {language}: {api_error}")
            # Try alternative: direct set_language method
            try:
                language_func = getattr(language_module, 'language')
                parser.set_language(language_func())
            except Exception as alt_error:
                console.print(f"❌ Alternative API failed for {language}: {alt_error}")
                _parser_cache[language] = None
                return None
        
        _parser_cache[language] = parser
        console.print(f"✅ Loaded parser for {language}")
        return parser
        
    except ImportError as e:
        console.print(f"❌ Parser not available for {language}: {e}")
        _parser_cache[language] = None
        return None
    except Exception as e:
        console.print(f"❌ Error creating parser for {language}: {e}")
        _parser_cache[language] = None
        return None


def extract_symbols_generic(source_code: str, language: str) -> List[Symbol]:
    """
    THE core function - Generic symbol extraction for any configured language.
    
    This replaces ALL language-specific extraction functions!
    """
    config = get_language_config(language)
    if not config:
        console.print(f"⚠️ Language {language} not configured")
        return []
    
    parser = get_parser_for_language(language)
    if not parser:
        console.print(f"⚠️ Parser not available for {language}")
        return []
    
    extractor = get_signature_extractor(language)
    
    # Parse source code
    try:
        source_bytes = bytes(source_code, "utf8")
        tree = parser.parse(source_bytes)
        root_node = tree.root_node
    except Exception as e:
        console.print(f"❌ Parse error for {language}: {e}")
        return []
    
    symbols = []
    
    def visit_node(node, parent_symbols=None, inside_class=False):
        """Generic tree traversal using language configuration."""
        if parent_symbols is None:
            parent_symbols = symbols
        
        # Check for class/interface nodes
        if node.type in config.class_nodes:
            class_symbol = _extract_class_symbol(node, source_code, config, extractor, language)
            if class_symbol:
                parent_symbols.append(class_symbol)
                # Process children within class context
                for child in node.children:
                    visit_node(child, class_symbol.children, inside_class=True)
        
        # Check for interface nodes (if configured)
        elif hasattr(config, 'interface_nodes') and node.type in config.interface_nodes:
            interface_symbol = _extract_interface_symbol(node, source_code, config, extractor, language)
            if interface_symbol:
                parent_symbols.append(interface_symbol)
                # Process children within interface context
                for child in node.children:
                    visit_node(child, interface_symbol.children, inside_class=True)
        
        # Check for function/method nodes
        elif node.type in config.function_nodes:
            function_symbol = _extract_function_symbol(
                node, source_code, config, extractor, language, inside_class
            )
            if function_symbol:
                parent_symbols.append(function_symbol)
                # Process children within function context (for nested functions)
                for child in node.children:
                    visit_node(child, function_symbol.children, inside_class)
        
        else:
            # Continue traversing for other node types
            for child in node.children:
                visit_node(child, parent_symbols, inside_class)
    
    # Start traversal
    visit_node(root_node)
    return symbols


def _extract_class_symbol(node, source_code: str, config, extractor, language: str) -> Optional[Symbol]:
    """Extract class symbol using generic approach."""
    name = _extract_name_from_node(node, source_code, config)
    if not name:
        return None
    
    # Get signature using language-specific extractor
    try:
        template = config.get_template("class")
        signature = extractor.extract_class_signature(node, source_code, template)
    except Exception as e:
        console.print(f"⚠️ Signature extraction failed for class {name}: {e}")
        signature = f"class {name}"
    
    return Symbol(
        name=name,
        type=SymbolType.CLASS,
        line=node.start_point[0] + 1,
        signature=signature,
        language=language
    )


def _extract_interface_symbol(node, source_code: str, config, extractor, language: str) -> Optional[Symbol]:
    """Extract interface symbol using generic approach."""
    name = _extract_name_from_node(node, source_code, config)
    if not name:
        return None
    
    try:
        template = config.get_template("interface")
        signature = extractor.extract_class_signature(node, source_code, template)  # Reuse class extractor
    except Exception as e:
        console.print(f"⚠️ Signature extraction failed for interface {name}: {e}")
        signature = f"interface {name}"
    
    return Symbol(
        name=name,
        type=SymbolType.INTERFACE,
        line=node.start_point[0] + 1,
        signature=signature,
        language=language
    )


def _extract_function_symbol(node, source_code: str, config, extractor, language: str, inside_class: bool) -> Optional[Symbol]:
    """Extract function/method symbol using generic approach."""
    name = _extract_name_from_node(node, source_code, config)
    if not name:
        return None
    
    # Determine symbol type
    symbol_type = SymbolType.METHOD if inside_class else SymbolType.FUNCTION
    
    # Get appropriate template
    template_key = "method" if inside_class else "function"
    template = config.get_template(template_key)
    
    # Extract signature using language-specific extractor
    try:
        signature = extractor.extract_function_signature(node, source_code, template)
    except Exception as e:
        console.print(f"⚠️ Signature extraction failed for {template_key} {name}: {e}")
        fallback = "def " if language == "python" else ""
        signature = f"{fallback}{name}(...)"
    
    return Symbol(
        name=name,
        type=symbol_type,
        line=node.start_point[0] + 1,
        signature=signature,
        language=language
    )


def _extract_name_from_node(node, source_code: str, config) -> Optional[str]:
    """Extract name from node using configured name node types."""
    for child in node.children:
        if child.type in config.name_nodes:
            return source_code[child.start_byte:child.end_byte]
    
    return None


def extract_symbols_from_file(file_path: Path, language: str) -> List[Symbol]:
    """Extract symbols from a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source_code = f.read()
        
        return extract_symbols_generic(source_code, language)
        
    except Exception as e:
        console.print(f"❌ Error reading {file_path}: {e}")
        return []


def process_file(file_path: Path, language: str) -> FileInfo:
    """Process a single file and return FileInfo."""
    symbols = extract_symbols_from_file(file_path, language)
    lines = count_lines(file_path)
    
    # Check if language has signature support
    config = get_language_config(language)
    extractor = get_signature_extractor(language)
    has_signature_support = config is not None and not isinstance(extractor, type(extractor)) or hasattr(extractor, 'language')
    
    return FileInfo(
        path=str(file_path),
        language=language,
        lines=lines,
        symbols=symbols,
        has_signature_support=has_signature_support
    )


def process_repository(repo_path: Path, 
                      language_filter: Optional[List[str]] = None,
                      max_files: Optional[int] = None) -> RepoSummary:
    """
    Main orchestration function - processes entire repository.
    
    This is the high-level entry point that coordinates everything.
    """
    console.print(f"🚀 Processing repository with fancy_tree...")
    
    # Scan repository
    scan_results = scan_repository(repo_path, language_filter, max_files)
    
    # Check language availability and offer installation
    from .config import show_language_status_and_install
    availability = show_language_status_and_install(repo_path)
    
    # Build repository structure
    root_dir = DirectoryInfo(path=".")
    
    # Process files by language
    supported_languages = {}
    total_processed = 0
    
    for language, file_list in scan_results["classified_files"].items():
        console.print(f"📝 Processing {len(file_list)} {language} files...")
        
        # Check if language is supported
        lang_info = availability.get(language, {})
        is_supported = lang_info.get("parser_available", False)
        supported_languages[language] = is_supported
        
        for file_path in file_list:
            try:
                # Make path relative to repo root
                rel_path = file_path.relative_to(repo_path)
                file_info = process_file(file_path, language)
                file_info.path = str(rel_path)
                
                # For now, add all files to root directory
                # TODO: Build proper directory tree in Phase 4
                root_dir.files.append(file_info)
                total_processed += 1
                
            except Exception as e:
                console.print(f"❌ Error processing {file_path}: {e}")
                continue
    
    console.print(f"✅ Processed {total_processed} files")
    
    # Create repository summary
    repo_summary = RepoSummary(
        name=scan_results["repo_info"]["name"],
        root_path=str(repo_path),
        structure=root_dir,
        languages=scan_results["language_counts"],
        supported_languages=supported_languages,
        total_files=scan_results["total_files"],
        total_lines=scan_results["total_lines"]
    )
    
    return repo_summary