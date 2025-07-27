"""Enhanced formatting for multi-language repository output."""

from typing import List, Dict
from pathlib import Path
from ..schema import RepoSummary, DirectoryInfo, FileInfo, Symbol, SymbolType
from collections import defaultdict


class EnhancedTreeFormatter:
    """Enhanced tree formatter with multi-language support."""
    
    def __init__(self, indent_size: int = 2, group_by_language: bool = True):
        self.indent_size = indent_size
        self.group_by_language = group_by_language
    
    def format_repository(self, repo_summary: RepoSummary) -> str:
        """Format entire repository with language grouping."""
        lines = []
        
        # Repository header
        lines.append(f"Repository: {repo_summary.name}")
        lines.append(f"Total files: {repo_summary.total_files}, Total lines: {repo_summary.total_lines}")
        lines.append("")
        
        # Language support status
        lines.append("Language Support:")
        for lang, count in repo_summary.languages.items():
            support_status = "SUPPORTED" if repo_summary.supported_languages.get(lang, False) else "NOT_SUPPORTED"
            lines.append(f"  {lang}: {count} files ({support_status})")
        lines.append("")
        
        if self.group_by_language:
            lines.extend(self._format_by_language(repo_summary))
        else:
            lines.extend(self._format_by_structure(repo_summary))
        
        return '\n'.join(lines)
    
    def _format_by_language(self, repo_summary: RepoSummary) -> List[str]:
        """Format grouped by language."""
        lines = []

        files_by_language = defaultdict(list)

        # walk the whole tree
        def walk(dir_info):
            for f in dir_info.files:
                files_by_language[f.language].append(f)
            for sub in dir_info.subdirs:
                walk(sub)

        walk(repo_summary.structure)
        
        # Format each language group
        for language in sorted(files_by_language.keys()):
            files = files_by_language[language]
            support_status = "SUPPORTED" if repo_summary.supported_languages.get(language, False) else "NOT_SUPPORTED"
            
            lines.append(f"{language.upper()} Files ({len(files)} files, {support_status}):")
            
            # Keep natural file ordering - remove sorted()
            for file_info in files:
                self._format_file(file_info, lines, 1)
            
            lines.append("")  # Empty line between languages
        
        return lines
        
    def _format_by_structure(self, repo_summary: RepoSummary) -> List[str]:
        """Format by directory structure (future implementation)."""
        lines = []
        self._format_directory(repo_summary.structure, lines, 0)
        return lines
    
    def _format_directory(
        self,
        dir_info: DirectoryInfo,
        lines: list[str],
        depth: int
    ) -> None:
        indent = self._indent(depth)

        # sort once, case‑insensitive – this is exactly what `tree` does
        subdirs = sorted(dir_info.subdirs, key=lambda d: d.name.lower())
        files   = sorted(dir_info.files,   key=lambda f: Path(f.path).name.lower())

        # ── 1. directories first ─────────────────────────────
        for sub in subdirs:
            lines.append(f"{indent}{sub.name}/")
            self._format_directory(sub, lines, depth + 1)

        # ── 2. files afterwards ─────────────────────────────
        for f in files:
            self._format_file(f, lines, depth)

    
    def _format_file(self,
                    file_info: FileInfo,
                    lines: List[str],
                    depth: int) -> None:
        """File header + its symbols (exactly what you already had)."""
        indent = self._indent(depth)
        filename = Path(file_info.path).name
        
        # If the file has no symbols we treat it as a generic asset.
        if not file_info.symbols:
            lines.append(f"{indent}{filename}")
            return

        lines.append(f"{indent}{filename} ({file_info.language}, "
                    f"{file_info.lines} lines)")

        for sym in file_info.symbols:
            self._format_symbol(sym, lines, depth + 1)
    
    def _format_symbol(self, symbol: Symbol, lines: List[str], depth: int):
        """Format symbol with enhanced signature display."""
        # Use signature if available, otherwise construct from type and name
        if symbol.signature:
            symbol_line = symbol.signature
        else:
            prefix = self._get_symbol_prefix(symbol.type)
            symbol_line = f"{prefix}{symbol.name}"
        
        # Remove line number from pretty output (kept in JSON)
        # symbol_line += f"  # line {symbol.line}"
        
        lines.append(self._indent(depth) + symbol_line)
        
        # Format child symbols
        for child in symbol.children:
            self._format_symbol(child, lines, depth + 1)
    
    def _get_symbol_prefix(self, symbol_type: SymbolType) -> str:
        """Get prefix for different symbol types."""
        prefixes = {
            SymbolType.CLASS: "class ",
            SymbolType.INTERFACE: "interface ",
            SymbolType.FUNCTION: "function ",
            SymbolType.METHOD: "method ",
            SymbolType.ENUM: "enum ",
            SymbolType.CONSTRUCTOR: "constructor ",
            SymbolType.FIELD: "field ",
            SymbolType.VARIABLE: "var "
        }
        return prefixes.get(symbol_type, "")
    
    def _indent(self, depth: int) -> str:
        """Generate indentation string."""
        return "  " * depth


# Convenience function
def format_repository_tree(repo_summary: RepoSummary, 
                          group_by_language: bool = True,
                          indent_size: int = 2) -> str:
    """Format repository as tree with multi-language support."""
    formatter = EnhancedTreeFormatter(indent_size, group_by_language)
    return formatter.format_repository(repo_summary)