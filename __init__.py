"""
fancy_tree - Git-enabled, cross-language code analysis with tree-sitter
"""

__version__ = "1.0.0"
__author__ = "Antoine Descamps, Ishan Tiwari"

# Make key classes available at package level
from fancy_tree.schema import RepoSummary, DirectoryInfo, FileInfo, Symbol, SymbolType
from fancy_tree.core.extraction import extract_symbols_generic, process_repository
from fancy_tree.core.discovery import discover_files, classify_files
from fancy_tree.core.formatter import format_repository_tree

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
    "__version__",
]