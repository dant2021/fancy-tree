"""Generic symbol extraction using tree-sitter and language configurations."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Dict, Any
from rich.console import Console
from tree_sitter import Parser, Language

# Change relative imports to absolute imports
from ..schema import (
    Diagnostic,
    ExtractionResult,
    ExtractionStatus,
    Symbol,
    SymbolType,
    FileInfo,
    DirectoryInfo,
    RepoSummary,
)
from ..extractors import get_signature_extractor
from ..extractors.base import NotImplementedExtractor
from .config import get_language_config
from .discovery import scan_repository, count_lines

console = Console()
diagnostic_console = Console(stderr=True)

# Parser cache to avoid recreating parsers
_parser_cache: Dict[str, Optional[Parser]] = {}


def parse_tree(parser: Parser, source_code: str):
    """Parse source across tree-sitter APIs that accept either str or bytes."""
    try:
        return parser.parse(source_code)
    except TypeError:
        return parser.parse(source_code.encode("utf-8"))


def root_node(tree):
    """Return the root node across property and callable root_node APIs."""
    root = tree.root_node
    return root() if callable(root) else root


def node_type(node) -> str:
    """Return the node kind across tree-sitter Node API versions."""
    node_kind = getattr(node, "type", None)
    if node_kind is None:
        node_kind = node.kind
    if callable(node_kind):
        node_kind = node_kind()
    return node_kind


def node_children(node) -> list:
    """Return child nodes across sequence and child_count/child APIs."""
    children = getattr(node, "children", None)
    if callable(children):
        children = children()
    if children is not None:
        return children
    child_count = node.child_count
    if callable(child_count):
        child_count = child_count()
    return [node.child(i) for i in range(child_count)]


def node_start_line(node) -> int:
    """Return the 1-based start line across point/position APIs."""
    point = getattr(node, "start_point", None)
    if callable(point):
        point = point()
    if point is None:
        point = node.start_position
    if callable(point):
        point = point()
    # tree-sitter 0.26.0's Point.row getter returns a borrowed reference.
    # Indexing avoids corrupting reference counts, especially for rows > 256.
    try:
        row = point[0]
    except TypeError:
        # Some parser bindings expose a point object without tuple indexing.
        row = point.row
    return row + 1


def node_start_byte(node) -> int:
    """Return the start byte across property and callable APIs."""
    start_byte = node.start_byte
    return start_byte() if callable(start_byte) else start_byte


def node_end_byte(node) -> int:
    """Return the end byte across property and callable APIs."""
    end_byte = node.end_byte
    return end_byte() if callable(end_byte) else end_byte


def node_text(node, source_code: str) -> str:
    """Return node text by slicing UTF-8 bytes with tree-sitter byte offsets."""
    source_bytes = source_code.encode("utf-8")
    return source_bytes[node_start_byte(node):node_end_byte(node)].decode("utf-8")


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


def clear_failed_parsers() -> None:
    """Forget failed parser loads so they are retried, e.g. after an install."""
    for language in [lang for lang, parser in _parser_cache.items() if parser is None]:
        del _parser_cache[language]


def extract_symbols_with_diagnostics(
    source_code: str, language: str, *, file_path: Optional[Path] = None
) -> ExtractionResult:
    """Extract supported declarations and report incomplete parsing/extraction."""
    result = ExtractionResult()
    config = get_language_config(language)
    if config is None:
        result.diagnostics.append(
            Diagnostic(
                "unsupported_language", f"No extraction configuration for {language}."
            )
        )
        return result
    result.parser_language = config.get_parser_language(file_path)
    parser = get_parser_for_language(result.parser_language)
    if parser is None:
        result.status = ExtractionStatus.PARSER_UNAVAILABLE
        result.diagnostics.append(
            Diagnostic(
                "parser_unavailable",
                f"Parser unavailable for {result.parser_language}; symbols were not extracted.",
            )
        )
        return result

    try:
        tree = parse_tree(parser, source_code)
        root = root_node(tree)
        has_error = root.has_error
        if callable(has_error):
            has_error = has_error()
    except Exception as e:
        result.status = ExtractionStatus.FAILED
        result.diagnostics.append(Diagnostic("parse_failed", f"Parsing failed: {e}"))
        return result

    result.status = (
        ExtractionStatus.RECOVERED if has_error else ExtractionStatus.SUCCESS
    )
    if has_error:
        result.diagnostics.append(
            Diagnostic(
                "parse_error",
                "Syntax errors detected; symbols recovered from this tree may be incomplete.",
            )
        )
    
    extractor = get_signature_extractor(language)
    
    def visit_node(node, parent_symbols=None, inside_class=False):
        if parent_symbols is None:
            parent_symbols = result.symbols
        
        current_type = node_type(node)
        symbol = None
        child_inside_class = inside_class
        if current_type in config.class_nodes:
            symbol = _extract_class_symbol(
                node, source_code, config, extractor, language, result.diagnostics
            )
            child_inside_class = True
        elif current_type in config.interface_nodes:
            symbol = _extract_interface_symbol(
                node, source_code, config, extractor, language, result.diagnostics
            )
            child_inside_class = True
        elif current_type in config.function_nodes:
            symbol = _extract_function_symbol(
                node,
                source_code,
                config,
                extractor,
                language,
                inside_class,
                result.diagnostics,
            )
            # Declarations nested in a method are functions, not class members.
            child_inside_class = False

        if symbol is not None:
            parent_symbols.append(symbol)
            parent_symbols = symbol.children
        # Anonymous/unsupported declarations must never hide named descendants.
        for child in node_children(node):
            visit_node(child, parent_symbols, child_inside_class)
        
    try:
        visit_node(root)
    except Exception as e:
        result.diagnostics.append(
            Diagnostic(
                "extraction_failed",
                f"Symbol extraction failed; results may be incomplete: {e}",
            )
        )
    if any(
        d.code in ("signature_failed", "extraction_failed") for d in result.diagnostics
    ):
        result.status = ExtractionStatus.FAILED
    return result


def _warn_diagnostics(result: ExtractionResult, source: str) -> None:
    """Keep legacy list-returning entry points from hiding incomplete extraction."""
    for diagnostic in result.diagnostics:
        diagnostic_console.print(
            f"WARNING: {source}: {diagnostic.code}: {diagnostic.message}", markup=False
        )


def extract_symbols_generic(
    source_code: str, language: str, *, file_path: Optional[Path] = None
) -> List[Symbol]:
    """Return symbols; pass a file path to select dialects such as TSX."""
    result = extract_symbols_with_diagnostics(
        source_code, language, file_path=file_path
    )
    _warn_diagnostics(result, str(file_path) if file_path is not None else language)
    return result.symbols


def _extract_class_symbol(
    node,
    source_code: str,
    config,
    extractor,
    language: str,
    diagnostics: List[Diagnostic],
) -> Optional[Symbol]:
    """Extract class symbol using generic approach."""
    name = extractor.get_symbol_name(node, source_code, config.name_nodes)
    if not name:
        return None
    
    # Get signature using language-specific extractor
    try:
        template = config.get_template("class")
        signature = extractor.extract_class_signature(node, source_code, template)
    except Exception as e:
        diagnostics.append(
            Diagnostic(
                "signature_failed",
                f"Signature extraction failed for class {name}: {e}",
                node_start_line(node),
            )
        )
        signature = f"class {name}"
    
    return Symbol(
        name=name,
        type=SymbolType.CLASS,
        line=node_start_line(node),
        signature=signature,
        language=language
    )


def _extract_interface_symbol(
    node,
    source_code: str,
    config,
    extractor,
    language: str,
    diagnostics: List[Diagnostic],
) -> Optional[Symbol]:
    """Extract interface symbol using generic approach."""
    name = extractor.get_symbol_name(node, source_code, config.name_nodes)
    if not name:
        return None
    
    try:
        template = config.get_template("interface")
        signature = extractor.extract_class_signature(node, source_code, template)  # Reuse class extractor
    except Exception as e:
        diagnostics.append(
            Diagnostic(
                "signature_failed",
                f"Signature extraction failed for interface {name}: {e}",
                node_start_line(node),
            )
        )
        signature = f"interface {name}"
    
    return Symbol(
        name=name,
        type=SymbolType.INTERFACE,
        line=node_start_line(node),
        signature=signature,
        language=language
    )


def _extract_function_symbol(
    node,
    source_code: str,
    config,
    extractor,
    language: str,
    inside_class: bool,
    diagnostics: List[Diagnostic],
) -> Optional[Symbol]:
    """Extract function/method symbol using generic approach."""
    name = extractor.get_symbol_name(node, source_code, config.name_nodes)
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
        diagnostics.append(
            Diagnostic(
                "signature_failed",
                f"Signature extraction failed for {template_key} {name}: {e}",
                node_start_line(node),
            )
        )
        fallback = "def " if language == "python" else ""
        signature = f"{fallback}{name}(...)"
    
    return Symbol(
        name=name,
        type=symbol_type,
        line=node_start_line(node),
        signature=signature,
        language=language
    )


def extract_file_with_diagnostics(file_path: Path, language: str) -> ExtractionResult:
    """Read a source file and retain both parser dialect and failure diagnostics."""
    try:
        source_bytes = file_path.read_bytes()
    except OSError as e:
        return ExtractionResult(
            status=ExtractionStatus.FAILED,
            diagnostics=[Diagnostic("read_failed", f"Could not read source: {e}")],
        )
    try:
        source_code = source_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        # Legacy encodings usually only affect comments and strings; keep the symbols.
        source_code = source_bytes.decode("utf-8", errors="replace")
        decode_diagnostic = Diagnostic(
            "decode_replaced",
            f"Source is not valid UTF-8; undecodable bytes were replaced: {e}",
        )
    else:
        decode_diagnostic = None
    result = extract_symbols_with_diagnostics(source_code, language, file_path=file_path)
    if decode_diagnostic is not None:
        result.diagnostics.insert(0, decode_diagnostic)
    return result


def extract_symbols_from_file(file_path: Path, language: str) -> List[Symbol]:
    """Extract symbols from a single file, warning about incomplete extraction."""
    result = extract_file_with_diagnostics(file_path, language)
    _warn_diagnostics(result, str(file_path))
    return result.symbols


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
    result = extract_file_with_diagnostics(file_path, language)
    symbols = result.symbols
    lines = count_lines(file_path)
    
    # Check if the output would be too long
    output_lines = count_symbol_output_lines(symbols)
    if max_lines is not None and output_lines > max_lines:
        # Flatten to only top-level symbols
        symbols = flatten_to_top_level(symbols)
    
    # Check if language has signature support
    config = get_language_config(language)
    extractor = get_signature_extractor(language)
    has_signature_support = config is not None and not isinstance(
        extractor, NotImplementedExtractor
    )
    
    return FileInfo(
        path=str(file_path),
        language=language,
        lines=lines,
        symbols=symbols,
        has_signature_support=has_signature_support,
        extraction_status=result.status,
        parser_language=result.parser_language,
        diagnostics=result.diagnostics,
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
                      max_lines: Optional[int] = 25,
                      *, allow_install: bool = True) -> RepoSummary:
    """
    Main orchestration function - processes entire repository.
    
    This is the high-level entry point that coordinates everything.
    """
    console.print(f"Processing repository with fancy_tree...")
    
    # Scan repository
    scan_results = scan_repository(repo_path, language_filter, max_files)
    
    # Check language availability and offer installation
    from .config import show_language_status_and_install
    availability = show_language_status_and_install(repo_path, allow_install=allow_install)
    
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
            # Make path relative to repo root
            try:
                # Ensure both paths are absolute
                abs_file = file_path.resolve()
                abs_repo = repo_path.resolve()
                rel_path = abs_file.relative_to(abs_repo)
            except (OSError, ValueError):
                # Fallback if paths are incompatible
                rel_path = Path(file_path.name)

            try:
                file_info = process_file(file_path, language, max_lines)
            except Exception as e:
                # stderr stays visible when --quiet swallows progress output.
                diagnostic_console.print(
                    f"ERROR: Error processing {file_path}: {e}", markup=False
                )
                file_info = FileInfo(
                    path=str(rel_path),
                    language=language,
                    lines=0,
                    symbols=[],
                    has_signature_support=False,
                    extraction_status=ExtractionStatus.FAILED,
                    diagnostics=[
                        Diagnostic("process_failed", f"File processing failed: {e}")
                    ],
                )
            file_info.path = str(rel_path)
            
            # Build proper directory tree
            rel_parts = list(rel_path.parts)           # e.g. ['src', 'main', 'App.java']
            file_name = rel_parts.pop()                # keep the filename, pop directories
            target_dir = _get_or_create_dir(root_dir, rel_parts)
            target_dir.files.append(file_info)
            
            total_processed += 1
    
    # ----------------------------------------------------------
    # Attach files that didn't match any language
    # ----------------------------------------------------------
    for file_path in unclassified_files:
        try:
            rel_path = file_path.resolve().relative_to(repo_path.resolve())
        except ValueError:
            rel_path = Path(file_path.name)

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
