"""Command-line interface for fancy_tree."""

import sys
import json
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.panel import Panel

from .core.extraction import process_repository
from .core.formatter import format_repository_tree

app = typer.Typer(name="fancy-tree", help="Git-enabled, cross-language code analysis with tree-sitter")
console = Console()


@app.command()
def scan(
    path: Optional[Path] = typer.Argument(None, help="Repository path to scan (default: current directory)"),
    languages: Optional[List[str]] = typer.Option(None, "--lang", "-l", help="Filter by specific languages"),
    max_files: Optional[int] = typer.Option(None, "--max-files", "-m", help="Maximum number of files to process"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path (default: stdout)"),
    format: str = typer.Option("tree", "--format", "-f", help="Output format: tree, json"),
    group_by_language: bool = typer.Option(True, "--group-by-lang/--group-by-structure", help="Group output by language or directory structure"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress progress output"),
):
    """Scan a repository and extract code structure."""
    
    # Default to current directory
    if path is None:
        path = Path.cwd()
    
    # Validate path
    if not path.exists():
        console.print(f"Error: Path '{path}' does not exist", style="red")
        raise typer.Exit(1)
    
    if not path.is_dir():
        console.print(f"Error: Path '{path}' is not a directory", style="red")
        raise typer.Exit(1)
    
    if not quiet:
        console.print(f"Scanning repository: {path}")
        if languages:
            console.print(f"Language filter: {', '.join(languages)}")
        if max_files:
            console.print(f"Max files: {max_files}")
    
    try:
        # Process repository
        repo_summary = process_repository(
            repo_path=path,
            language_filter=languages,
            max_files=max_files
        )
        
        # Format output
        if format == "json":
            output_content = json.dumps(repo_summary.to_dict(), indent=2)
        elif format == "tree":
            output_content = format_repository_tree(
                repo_summary, 
                group_by_language=group_by_language
            )
        else:
            console.print(f"Error: Unknown format '{format}'. Use 'tree' or 'json'", style="red")
            raise typer.Exit(1)
        
        # Output results
        if output:
            output.write_text(output_content, encoding='utf-8')
            if not quiet:
                console.print(f"Results written to: {output}")
        else:
            console.print(output_content)
        
        if not quiet:
            console.print(f"\nProcessed {repo_summary.total_files} files in {len(repo_summary.languages)} languages")
    
    except Exception as e:
        console.print(f"Error processing repository: {e}", style="red")
        if not quiet:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
def languages():
    """List supported languages and their status."""
    from .extractors import list_supported_languages
    from .core.config import detect_available_languages
    
    console.print(Panel("Fancy Tree - Supported Languages", style="bold blue"))
    
    # Show implemented extractors
    supported = list_supported_languages()
    console.print(f"\nImplemented extractors: {len(supported)}")
    for lang in sorted(supported):
        console.print(f"  ✓ {lang}")
    
    # Try to detect language availability in current directory
    try:
        current_path = Path.cwd()
        availability = detect_available_languages(current_path)
        
        if availability:
            console.print(f"\nLanguages detected in {current_path}:")
            for lang, info in availability.items():
                status = "AVAILABLE" if info.get("parser_available", False) else "PARSER MISSING"
                file_count = info.get("file_count", 0)
                console.print(f"  {lang}: {file_count} files ({status})")
        
    except Exception as e:
        console.print(f"\nNote: Could not detect languages in current directory: {e}")


@app.command()
def version():
    """Show version information."""
    try:
        from . import __version__
    except ImportError:
        __version__ = "1.0.0"
    console.print(f"fancy-tree version {__version__}")


@app.command()
def test(
    path: Optional[Path] = typer.Argument(None, help="Path to test (default: current directory)")
):
    """Test fancy_tree functionality on a directory."""
    if path is None:
        path = Path.cwd()
    
    console.print(Panel(f"Testing fancy_tree on: {path}", style="bold green"))
    
    try:
        # Quick test
        repo_summary = process_repository(path, max_files=10)
        
        console.print(f"✓ Successfully processed {repo_summary.total_files} files")
        console.print(f"✓ Found {len(repo_summary.languages)} languages: {list(repo_summary.languages.keys())}")
        
        # Show supported vs unsupported
        supported_count = sum(1 for supported in repo_summary.supported_languages.values() if supported)
        total_langs = len(repo_summary.supported_languages)
        console.print(f"✓ Language support: {supported_count}/{total_langs} languages supported")
        
        console.print("\nTest completed successfully!")
        
    except Exception as e:
        console.print(f"✗ Test failed: {e}", style="red")
        raise typer.Exit(1)


if __name__ == "__main__":
    app() 