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

app = typer.Typer(
    name="fancy-tree",
    help="Git-enabled, cross-language code analysis with tree-sitter",
    add_completion=False,                      # 1️⃣ hide completion options
    context_settings={"allow_interspersed_args": True}  # 2️⃣ let options appear after path
)
console = Console()

# Define subcommand names to avoid treating them as paths
SUBCOMMAND_NAMES = {"languages", "version", "test"}


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    path: Optional[Path] = typer.Argument(None, help="Repository path to scan (default: current directory)"),
    languages: Optional[List[str]] = typer.Option(None, "--lang", "-l", help="Filter by specific languages"),
    max_files: Optional[int] = typer.Option(100, "--max-files", "-m", help="Maximum number of files to process"),
    max_lines: Optional[int] = typer.Option(25, "--max-lines", help="Maximum number of lines for a file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path (default: stdout)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress progress output"),
):
    """Git-enabled, cross-language code analysis with tree-sitter.
    
    By default, fancy-tree scans the current directory and shows the code structure.
    """
    # If a subcommand was invoked, don't run the main scan logic
    if ctx.invoked_subcommand is not None:
        return
    
    # Manual routing for subcommand names passed as path
    if path and str(path) in SUBCOMMAND_NAMES:
        if str(path) == "version":
            version_command()
        elif str(path) == "languages":
            languages_command()
        elif str(path) == "test":
            test_command(None)
        return
    
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
            max_files=max_files,
            max_lines=max_lines
        )
        
        # Format output - always group by structure now
        if json_output:
            output_content = json.dumps(repo_summary.to_dict(), indent=2)
        else:
            output_content = format_repository_tree(
                repo_summary, 
                group_by_language=False  # Always structure grouping
            )
        
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


def version_command():
    """Actual version logic."""
    try:
        from . import __version__
    except ImportError:
        __version__ = "0.1.0"
    console.print(f"fancy-tree version {__version__}")


def languages_command():
    """Actual languages logic."""
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


def test_command(path: Optional[Path]):
    """Actual test logic."""
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


@app.command()
def version():
    """Show version information."""
    version_command()


@app.command()  
def languages():
    """List supported languages and their status."""
    languages_command()


@app.command()
def test(path: Optional[Path] = typer.Argument(None, help="Path to test (default: current directory)")):
    """Test fancy_tree functionality on a directory."""
    test_command(path)


if __name__ == "__main__":
    app() 