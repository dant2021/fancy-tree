"""Core functionality for fancy_tree."""

from .config import (
    get_language_config, 
    detect_language, 
    detect_available_languages,
    show_language_status_and_install
)
from .discovery import (
    discover_files, 
    classify_files, 
    scan_repository,
    get_repository_info
)
from .extraction import (
    extract_symbols_generic,
    extract_symbols_from_file,
    process_repository,
    get_parser_for_language
)
from .formatter import (
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