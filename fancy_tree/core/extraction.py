"""Generic symbol extraction using tree-sitter and language configurations."""

from pathlib import Path
from typing import List, Optional, Dict, Any
from rich.console import Console
from tree_sitter import Parser, Language

# Change relative imports to absolute imports
from ..schema import Symbol, SymbolType, FileInfo, DirectoryInfo, RepoSummary
from ..extractors import get_signature_extractor
from .config import get_language_config
from .discovery import scan_repository, count_lines

console = Console()

# Parser cache to avoid recreating parsers
_parser_cache: Dict[str, Optional[Parser]] = {}


def get_parser_for_language(language: str) -> Optional[Parser]:
    """Get tree-sitter parser using tree-sitter-language-pack."""
    if language in _parser_cache:
        return _parser_cache[language]
    
    try:
        # Use the better maintained tree-sitter-language-pack
        from tree_sitter_language_pack import get_parser
        
        # This gives us a ready-to-use parser!
        parser = get_parser(language)
        
        _parser_cache[language] = parser
        console.print(f"Loaded parser for {language}")
        return parser
        
    except Exception as e:
        console.print(f"ERROR: Parser failed for {language}: {e}")
        console.print(f"    Try: pip install tree-sitter-language-pack")
        _parser_cache[language] = None
        return None


def extract_symbols_generic(source_code: str, language: str) -> List[Symbol]:
    """Generic symbol extraction using your proven pattern."""
    config = get_language_config(language)
    parser = get_parser_for_language(language)
    if not config or not parser:
        return []
    
    extractor = get_signature_extractor(language)
    
    # Parse source
    source_bytes = bytes(source_code, "utf8")
    tree = parser.parse(source_bytes)
    symbols = []
    
    def visit_node(node, parent_symbols=None, inside_class=False):
        if parent_symbols is None:
            parent_symbols = symbols
        
        # Use configuration to check node types
        if node.type in config.class_nodes:
            class_symbol = _extract_class_symbol(node, source_code, config, extractor, language)
            if class_symbol:
                parent_symbols.append(class_symbol)
                # Recurse with class_symbol.children as parent
                for child in node.children:
                    visit_node(child, class_symbol.children, inside_class=True)
        
        elif node.type in config.function_nodes:
            function_symbol = _extract_function_symbol(node, source_code, config, extractor, language, inside_class)
            if function_symbol:
                parent_symbols.append(function_symbol)
                # Recurse with function_symbol.children as parent
                for child in node.children:
                    visit_node(child, function_symbol.children, inside_class)
        
        else:
            # Continue traversing with same parent_symbols
            for child in node.children:
                visit_node(child, parent_symbols, inside_class)
    
    visit_node(tree.root_node)
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
        console.print(f"WARNING: Signature extraction failed for class {name}: {e}")
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
        console.print(f"ERROR: Error reading {file_path}: {e}")
        return []


def count_symbol_output_lines(symbols: List[Symbol]) -> int:
    """Count how many lines these symbols would produce in the output."""
    count = 0
    for symbol in symbols:
        count += 1  # The symbol itself
        count += count_symbol_output_lines(symbol.children)  # Recursively count children
    return count


def flatten_to_top_level(symbols: List[Symbol]) -> List[Symbol]:
    """Return only top-level symbols, removing all children."""
    flattened = []
    for symbol in symbols:
        # Create a copy of the symbol without children
        top_level_symbol = Symbol(
            name=symbol.name,
            type=symbol.type,
            line=symbol.line,
            signature=symbol.signature,
            language=symbol.language,
            children=[]  # Remove all children
        )
        flattened.append(top_level_symbol)
    return flattened


def process_file(file_path: Path, language: str, max_lines: Optional[int] = 25) -> FileInfo:
    """Process a single file and return FileInfo."""
    symbols = extract_symbols_from_file(file_path, language)
    lines = count_lines(file_path)
    
    # Check if the output would be too long
    output_lines = count_symbol_output_lines(symbols)
    if output_lines > max_lines:
        # Flatten to only top-level symbols
        symbols = flatten_to_top_level(symbols)
    
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


def _get_or_create_dir(root: DirectoryInfo, parts: list[str]) -> DirectoryInfo:
    """
    Walk / create sub‑DirectoryInfo objects for the given relative‑path parts
    and return the deepest DirectoryInfo.
    """
    current = root
    for part in parts:
        # look for an existing sub‑dir with this name
        sub = next((d for d in current.subdirs if d.name == part), None)
        if sub is None:
            sub = DirectoryInfo(
                path=str(Path(current.path) / part),
                name=part,
                subdirs=[],
                files=[]
            )
            current.subdirs.append(sub)
        current = sub
    return current


def process_repository(repo_path: Path, 
                      language_filter: Optional[List[str]] = None,
                      max_files: Optional[int] = None,
                      max_lines: Optional[int] = 25) -> RepoSummary:
    """
    Main orchestration function - processes entire repository.
    
    This is the high-level entry point that coordinates everything.
    """
    console.print(f"Processing repository with fancy_tree...")
    
    # Scan repository
    scan_results = scan_repository(repo_path, language_filter, max_files)
    
    # Check language availability and offer installation
    from .config import show_language_status_and_install
    availability = show_language_status_and_install(repo_path)
    
    # Build repository structure
    root_dir = DirectoryInfo(
        path=".",
        name=".",
        subdirs=[],
        files=[]
    )
    
    # Get classified files and find unclassified ones
    classified_files = scan_results["classified_files"]
    all_files = scan_results["files"]
    
    # Find unclassified files by comparing all files with classified files
    classified_file_set = set()
    for file_list in classified_files.values():
        classified_file_set.update(file_list)
    unclassified_files = [f for f in all_files if f not in classified_file_set]
    
    # Process files by language
    supported_languages = {}
    total_processed = 0
    
    for language, file_list in classified_files.items():
        console.print(f"Processing {len(file_list)} {language} files...")
        
        # Check if language is supported
        lang_info = availability.get(language, {})
        is_supported = lang_info.get("parser_available", False)
        supported_languages[language] = is_supported
        
        for file_path in file_list:
            try:
                # Make path relative to repo root
                try:
                    # Ensure both paths are absolute
                    abs_file = file_path.resolve()
                    abs_repo = repo_path.resolve()
                    rel_path = abs_file.relative_to(abs_repo)
                except ValueError:
                    # Fallback if paths are incompatible
                    rel_path = file_path.name
                
                file_info = process_file(file_path, language, max_lines)
                file_info.path = str(rel_path)
                
                # Build proper directory tree
                rel_parts = list(rel_path.parts)           # e.g. ['src', 'main', 'App.java']
                file_name = rel_parts.pop()                # keep the filename, pop directories
                target_dir = _get_or_create_dir(root_dir, rel_parts)
                target_dir.files.append(file_info)
                
                total_processed += 1
                
            except Exception as e:
                console.print(f"ERROR: Error processing {file_path}: {e}")
                continue
    
    # ----------------------------------------------------------
    # Attach files that didn't match any language
    # ----------------------------------------------------------
    for file_path in unclassified_files:
        try:
            rel_path = file_path.resolve().relative_to(repo_path.resolve())
        except ValueError:
            rel_path = file_path.name

        # no symbols, no lines, no language
        file_info = FileInfo(
            path=str(rel_path),
            language="other",
            lines=0,
            symbols=[],
            has_signature_support=False
        )

        parts = list(rel_path.parts)
        if parts:
            parts.pop()                                   # drop the filename
        _get_or_create_dir(root_dir, parts).files.append(file_info)
        total_processed += 1
    
    console.print(f"Processed {total_processed} files")
    
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
