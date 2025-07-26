"""Enhanced data models for repository abstraction."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional
import json


class SymbolType(Enum):
    """Extended symbol types for multi-language support."""
    CLASS = "class"
    INTERFACE = "interface"
    ENUM = "enum"
    METHOD = "method"
    FUNCTION = "function"
    FIELD = "field"
    CONSTRUCTOR = "constructor"
    VARIABLE = "variable"
    TYPE_ALIAS = "type_alias"


@dataclass
class Symbol:
    """A code symbol with enhanced multi-language support."""
    name: str
    type: SymbolType
    line: int
    signature: Optional[str] = None
    language: Optional[str] = None  # NEW: Track source language
    children: List['Symbol'] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type.value,
            "line": self.line,
            "signature": self.signature,
            "language": self.language,
            "children": [child.to_dict() for child in self.children]
        }


@dataclass
class FileInfo:
    """Enhanced file information with language metadata."""
    path: str  # Relative to repo root
    language: str
    lines: int
    symbols: List[Symbol] = field(default_factory=list)
    has_signature_support: bool = True  # NEW: Track if signatures are implemented
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "language": self.language,
            "lines": self.lines,
            "has_signature_support": self.has_signature_support,
            "symbols": [symbol.to_dict() for symbol in self.symbols]
        }


@dataclass
class DirectoryInfo:
    """Directory information with enhanced metadata."""
    path: str
    name: str = ""  # Directory name
    files: List[FileInfo] = field(default_factory=list)
    subdirs: List['DirectoryInfo'] = field(default_factory=list)
    language_counts: Dict[str, int] = field(default_factory=dict)  # NEW: Language breakdown
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "files": [f.to_dict() for f in self.files],
            "subdirs": [d.to_dict() for d in self.subdirs],
            "language_counts": self.language_counts
        }


@dataclass
class RepoSummary:
    """Enhanced repository summary with language support tracking."""
    name: str
    root_path: str
    structure: DirectoryInfo
    languages: Dict[str, int] = field(default_factory=dict)  # language -> file_count
    supported_languages: Dict[str, bool] = field(default_factory=dict)  # NEW: Track availability
    total_files: int = 0
    total_lines: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository": {
                "name": self.name,
                "root_path": self.root_path,
                "total_files": self.total_files,
                "total_lines": self.total_lines,
                "languages": self.languages,
                "supported_languages": self.supported_languages
            },
            "structure": self.structure.to_dict()
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to clean JSON."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def save(self, output_path: Path) -> None:
        """Save to file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
    
    def print_summary(self) -> None:
        """Print enhanced summary with language support status."""
        print(f"Repository: {self.name}")
        print(f"Total files: {self.total_files}")
        print(f"Total lines: {self.total_lines}")
        print("\nLanguage Support:")
        for lang, count in sorted(self.languages.items()):
            support_status = "✅" if self.supported_languages.get(lang, False) else "❌"
            print(f"  {support_status} {lang}: {count} files")


# Keep existing utility functions
def create_flat_file_list(repo_summary: RepoSummary) -> List[Dict[str, Any]]:
    """Create a flat list of all files for easy LLM consumption."""
    files = []
    
    def collect_files(dir_info: DirectoryInfo, current_path: str = ""):
        for file_info in dir_info.files:
            files.append({
                "path": file_info.path,
                "language": file_info.language,
                "lines": file_info.lines,
                "has_signature_support": file_info.has_signature_support,
                "symbols": [s.to_dict() for s in file_info.symbols]
            })
        
        for subdir in dir_info.subdirs:
            collect_files(subdir, current_path)
    
    collect_files(repo_summary.structure)
    return files


def create_symbol_index(repo_summary: RepoSummary) -> Dict[str, List[Dict[str, Any]]]:
    """Create an index of all symbols by type for easy lookup."""
    index = {}
    
    def collect_symbols(symbols: List[Symbol], file_path: str):
        for symbol in symbols:
            symbol_type = symbol.type.value
            if symbol_type not in index:
                index[symbol_type] = []
            
            index[symbol_type].append({
                "name": symbol.name,
                "file": file_path,
                "line": symbol.line,
                "signature": symbol.signature,
                "language": symbol.language
            })
            
            # Recursively collect child symbols
            collect_symbols(symbol.children, file_path)
    
    flat_files = create_flat_file_list(repo_summary)
    for file_info in flat_files:
        file_symbols = [Symbol(
            name=s["name"], 
            type=SymbolType(s["type"]), 
            line=s["line"],
            signature=s.get("signature"),
            language=s.get("language")
        ) for s in file_info["symbols"]]
        collect_symbols(file_symbols, file_info["path"])
    
    return index