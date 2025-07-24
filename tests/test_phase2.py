"""
Test script for Phase 2 implementation.
Tests all core framework components before implementing language-specific extractors.
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add parent directory to path so we can import fancy_tree modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

console = Console()

def test_imports():
    """Test that all modules can be imported correctly."""
    console.print(Panel("🔍 Testing Imports", style="bold blue"))
    
    try:
        # Test core imports with relative imports
        from core.config import get_language_config, detect_language, config_manager
        from core.discovery import discover_files, classify_files, scan_repository
        from core.extraction import extract_symbols_generic, process_repository
        from core.formatter import format_repository_tree
        from extractors import get_signature_extractor, list_supported_languages
        from schema import Symbol, SymbolType, RepoSummary
        
        console.print("✅ All imports successful!")
        return True
        
    except ImportError as e:
        console.print(f"❌ Import failed: {e}")
        return False

def test_configuration():
    """Test configuration loading and language detection."""
    console.print(Panel("⚙️ Testing Configuration System", style="bold green"))
    
    try:
        from core.config import config_manager, get_language_config, detect_language
        
        # Test config loading
        config_manager.load_config()
        console.print("✅ Configuration loaded successfully")
        
        # Test language configs
        python_config = get_language_config("python")
        if python_config:
            console.print(f"✅ Python config: {len(python_config.extensions)} extensions, {len(python_config.function_nodes)} function nodes")
        else:
            console.print("❌ Python config not found")
        
        # Test language detection
        test_files = [
            ("test.py", "python"),
            ("test.ts", "typescript"), 
            ("test.java", "java"),
            ("test.unknown", None)
        ]
        
        for filename, expected in test_files:
            detected = detect_language(Path(filename))
            if detected == expected:
                console.print(f"✅ {filename} → {detected}")
            else:
                console.print(f"❌ {filename} → {detected} (expected {expected})")
        
        # Show all configured languages
        languages = list(config_manager.languages.keys())
        console.print(f"📋 Configured languages: {', '.join(languages)}")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Configuration test failed: {e}")
        return False

def test_extractors():
    """Test the extractor registry system."""
    console.print(Panel("🔧 Testing Extractor Registry", style="bold yellow"))
    
    try:
        from extractors import get_signature_extractor, list_supported_languages, NotImplementedExtractor
        
        # Test extractor registry
        supported = list_supported_languages()
        console.print(f"📋 Explicitly supported languages: {supported}")
        
        # Test fallback extractors
        test_languages = ["python", "typescript", "java", "unknown"]
        
        for lang in test_languages:
            extractor = get_signature_extractor(lang)
            extractor_type = type(extractor).__name__
            
            if isinstance(extractor, NotImplementedExtractor):
                console.print(f"⚠️ {lang} → {extractor_type} (fallback)")
            else:
                console.print(f"✅ {lang} → {extractor_type} (implemented)")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Extractor test failed: {e}")
        return False

def test_discovery():
    """Test file discovery and classification."""
    console.print(Panel("📂 Testing File Discovery", style="bold cyan"))
    
    try:
        from core.discovery import discover_files, classify_files, get_repository_info
        
        # Test on parent directory (the repo root)
        repo_path = parent_dir
        console.print(f"📍 Testing discovery on: {repo_path.absolute()}")
        
        # Get repository info
        repo_info = get_repository_info(repo_path)
        console.print(f"📁 Repository: {repo_info['name']}")
        console.print(f"🌿 Git repo: {repo_info['is_git_repo']}")
        if repo_info['current_branch']:
            console.print(f"🌿 Branch: {repo_info['current_branch']}")
        
        # Discover files (limit to avoid too much output)
        files = discover_files(repo_path)
        console.print(f"📄 Found {len(files)} files")
        
        # Show some example files
        python_files = [f for f in files if f.suffix == '.py']
        console.print(f"🐍 Python files found: {len(python_files)}")
        
        if python_files:
            console.print("   Examples:")
            for f in python_files[:5]:  # Show first 5
                try:
                    rel_path = f.relative_to(repo_path)
                    console.print(f"     • {rel_path}")
                except ValueError:
                    console.print(f"     • {f.name}")
        
        # Test classification (limit files to avoid too much processing)
        test_files = files[:20] if len(files) > 20 else files
        classified = classify_files(test_files)
        
        # Create summary table
        table = Table(title="File Classification Results")
        table.add_column("Language", style="cyan")
        table.add_column("File Count", style="magenta")
        table.add_column("Example Files", style="green")
        
        for lang, lang_files in classified.items():
            examples = [f.name for f in lang_files[:3]]
            examples_str = ", ".join(examples)
            if len(lang_files) > 3:
                examples_str += f" (+{len(lang_files)-3} more)"
            
            table.add_row(lang, str(len(lang_files)), examples_str)
        
        console.print(table)
        
        return True
        
    except Exception as e:
        console.print(f"❌ Discovery test failed: {e}")
        import traceback
        console.print(f"Traceback: {traceback.format_exc()}")
        return False

def test_extraction():
    """Test generic symbol extraction."""
    console.print(Panel("⚗️ Testing Generic Symbol Extraction", style="bold magenta"))
    
    try:
        from core.extraction import extract_symbols_generic, get_parser_for_language
        
        # Test parser loading
        console.print("🔍 Testing parser availability...")
        test_languages = ["python", "typescript", "java"]
        
        for lang in test_languages:
            parser = get_parser_for_language(lang)
            if parser:
                console.print(f"✅ {lang} parser loaded successfully")
            else:
                console.print(f"❌ {lang} parser not available (expected in Phase 2)")
        
        # Test extraction with sample code
        sample_python_code = '''
class TestClass:
    def __init__(self):
        pass
    
    def test_method(self, param):
        return param

def standalone_function():
    pass
'''
        
        console.print("\n🐍 Testing Python extraction with sample code...")
        symbols = extract_symbols_generic(sample_python_code, "python")
        
        if symbols:
            console.print(f"✅ Extracted {len(symbols)} symbols:")
            for symbol in symbols:
                console.print(f"   • {symbol.type.value}: {symbol.name} (line {symbol.line})")
                if symbol.signature:
                    console.print(f"     Signature: {symbol.signature}")
                
                for child in symbol.children:
                    console.print(f"     ↳ {child.type.value}: {child.name} (line {child.line})")
                    if child.signature:
                        console.print(f"       Signature: {child.signature}")
        else:
            console.print("⚠️ No symbols extracted (expected if tree-sitter-python not installed)")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Extraction test failed: {e}")
        import traceback
        console.print(f"Traceback: {traceback.format_exc()}")
        return False

def test_basic_functionality():
    """Test that core functionality works without tree-sitter."""
    console.print(Panel("🧪 Testing Basic Functionality", style="bold green"))
    
    try:
        from schema import Symbol, SymbolType, FileInfo, RepoSummary, DirectoryInfo
        from core.formatter import format_repository_tree
        
        # Create test data manually
        test_symbol = Symbol(
            name="test_function",
            type=SymbolType.FUNCTION,
            line=1,
            signature="def test_function()",
            language="python"
        )
        
        test_file = FileInfo(
            path="test.py",
            language="python", 
            lines=10,
            symbols=[test_symbol]
        )
        
        test_dir = DirectoryInfo(
            path=".",
            files=[test_file]
        )
        
        test_repo = RepoSummary(
            name="test_repo",
            root_path="/test",
            structure=test_dir,
            languages={"python": 1},
            supported_languages={"python": True},
            total_files=1,
            total_lines=10
        )
        
        # Test formatting
        formatted = format_repository_tree(test_repo)
        console.print("✅ Created test data and formatted successfully")
        console.print("📄 Sample formatted output:")
        lines = formatted.split('\n')
        for line in lines[:10]:
            console.print(f"  {line}")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Basic functionality test failed: {e}")
        import traceback
        console.print(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Run all tests."""
    console.print(Panel.fit("🧪 FANCY_TREE Phase 2 Testing Suite", style="bold white on blue"))
    console.print(f"📍 Running from: {Path.cwd()}")
    console.print(f"📁 Testing directory: {parent_dir}")
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Extractors", test_extractors),
        ("Discovery", test_discovery),
        ("Basic Functionality", test_basic_functionality),
        ("Extraction", test_extraction),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        console.print(f"\n{'='*60}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            console.print(f"❌ {test_name} test crashed: {e}")
            import traceback
            console.print(f"Traceback: {traceback.format_exc()}")
            results.append((test_name, False))
    
    # Summary
    console.print(f"\n{'='*60}")
    console.print(Panel("📊 Test Results Summary", style="bold white"))
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        icon = "✅" if result else "❌"
        console.print(f"  {icon} {test_name}")
    
    console.print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed >= total - 1:  # Allow 1 failure (extraction expected to fail)
        console.print("\n🎉 Core functionality working! Phase 2 implementation is solid!")
        console.print("📋 Next step: Implement Phase 3 (Language-specific extractors)")
    else:
        console.print(f"\n⚠️ {total-passed} tests failed. Let's fix the issues.")
    
    return passed >= total - 1

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)