"""Comprehensive test for Phase 3 - Language extractors and full package functionality."""

import sys
from pathlib import Path
from textwrap import dedent

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test all imports
from schema import Symbol, SymbolType, FileInfo, RepoSummary, DirectoryInfo
from core.extraction import extract_symbols_generic, process_repository
from core.formatter import format_repository_tree
from extractors import get_signature_extractor, list_supported_languages
from extractors.python import PythonExtractor
from extractors.typescript import TypeScriptExtractor
from extractors.java import JavaExtractor


def test_python_extractor():
    """Test Python signature extraction."""
    print("Testing Python Extractor...")
    
    python_code = dedent("""
    def simple_function(a, b):
        return a + b
    
    def typed_function(name: str, age: int) -> str:
        return f"{name} is {age} years old"
    
    class UserManager:
        def __init__(self, db_connection):
            self.db = db_connection
        
        def create_user(self, name: str, email: str) -> User:
            return User(name, email)
    
    class DatabaseConnection(BaseConnection):
        pass
    """)
    
    symbols = extract_symbols_generic(python_code, "python")
    
    print(f"  Found {len(symbols)} symbols:")
    for symbol in symbols:
        print(f"    {symbol.type.name}: {symbol.name} -> {symbol.signature}")
        for child in symbol.children:
            print(f"      {child.type.name}: {child.name} -> {child.signature}")
    
    # Verify specific extractions
    assert len(symbols) >= 4, f"Expected at least 4 symbols, got {len(symbols)}"
    
    # Find typed function
    typed_func = next((s for s in symbols if s.name == "typed_function"), None)
    assert typed_func is not None, "typed_function not found"
    assert "-> str" in typed_func.signature, f"Return type not in signature: {typed_func.signature}"
    
    print("  Python extractor test PASSED")


def test_typescript_extractor():
    """Test TypeScript signature extraction."""
    print("Testing TypeScript Extractor...")
    
    typescript_code = dedent("""
    function calculateTotal(items: Item[]): number {
        return items.reduce((sum, item) => sum + item.price, 0);
    }
    
    interface UserInterface {
        name: string;
        age: number;
    }
    
    class UserService implements UserInterface {
        private users: User[] = [];
        
        public addUser(user: User): void {
            this.users.push(user);
        }
        
        public getUserCount(): number {
            return this.users.length;
        }
    }
    
    class ExtendedUserService extends UserService {
        constructor(private logger: Logger) {
            super();
        }
    }
    """)
    
    symbols = extract_symbols_generic(typescript_code, "typescript")
    
    print(f"  Found {len(symbols)} symbols:")
    for symbol in symbols:
        print(f"    {symbol.type.name}: {symbol.name} -> {symbol.signature}")
        for child in symbol.children:
            print(f"      {child.type.name}: {child.name} -> {child.signature}")
    
    # Verify specific extractions
    assert len(symbols) >= 4, f"Expected at least 4 symbols, got {len(symbols)}"
    
    # Find function with return type
    calc_func = next((s for s in symbols if s.name == "calculateTotal"), None)
    assert calc_func is not None, "calculateTotal function not found"
    assert ": number" in calc_func.signature, f"Return type not in signature: {calc_func.signature}"
    
    print("  TypeScript extractor test PASSED")


def test_java_extractor():
    """Test Java signature extraction."""
    print("Testing Java Extractor...")
    
    java_code = dedent("""
    public class UserManager {
        private List<User> users;
        
        public UserManager() {
            this.users = new ArrayList<>();
        }
        
        public void addUser(User user) {
            users.add(user);
        }
        
        public User getUserById(Long id) {
            return users.stream()
                .filter(u -> u.getId().equals(id))
                .findFirst()
                .orElse(null);
        }
        
        private boolean validateUser(User user) {
            return user != null && user.getName() != null;
        }
    }
    
    public interface UserRepository extends BaseRepository<User> {
        List<User> findByName(String name);
    }
    """)
    
    symbols = extract_symbols_generic(java_code, "java")
    
    print(f"  Found {len(symbols)} symbols:")
    for symbol in symbols:
        print(f"    {symbol.type.name}: {symbol.name} -> {symbol.signature}")
        for child in symbol.children:
            print(f"      {child.type.name}: {child.name} -> {child.signature}")
    
    # Verify specific extractions
    assert len(symbols) >= 2, f"Expected at least 2 symbols, got {len(symbols)}"
    
    # Find UserManager class
    user_manager = next((s for s in symbols if s.name == "UserManager"), None)
    assert user_manager is not None, "UserManager class not found"
    assert "public class" in user_manager.signature, f"Access modifier not in signature: {user_manager.signature}"
    
    print("  Java extractor test PASSED")


def test_registry_system():
    """Test the signature extractor registry."""
    print("Testing Registry System...")
    
    # Test supported languages
    supported = list_supported_languages()
    print(f"  Supported languages: {supported}")
    assert "python" in supported, "Python extractor not registered"
    assert "typescript" in supported, "TypeScript extractor not registered"
    assert "java" in supported, "Java extractor not registered"
    
    # Test getting extractors
    python_ext = get_signature_extractor("python")
    assert isinstance(python_ext, PythonExtractor), "Python extractor not correct type"
    
    typescript_ext = get_signature_extractor("typescript")
    assert isinstance(typescript_ext, TypeScriptExtractor), "TypeScript extractor not correct type"
    
    java_ext = get_signature_extractor("java")
    assert isinstance(java_ext, JavaExtractor), "Java extractor not correct type"
    
    # Test fallback for unsupported language
    fallback_ext = get_signature_extractor("unknown_language")
    assert fallback_ext is not None, "Should provide fallback extractor"
    
    print("  Registry system test PASSED")


def test_full_package_on_self():
    """Test the complete package on fancy_tree itself."""
    print("Testing Full Package on Self...")
    
    # Process current directory
    repo_path = Path.cwd()
    repo_summary = process_repository(repo_path, max_files=20)  # Limit for testing
    
    print(f"  Repository: {repo_summary.name}")
    print(f"  Total files: {repo_summary.total_files}")
    print(f"  Languages found: {repo_summary.languages}")
    print(f"  Supported languages: {repo_summary.supported_languages}")
    
    # Verify we found Python files
    assert "python" in repo_summary.languages, "Should find Python files in fancy_tree"
    assert repo_summary.languages["python"] > 0, "Should have at least one Python file"
    
    # Test formatting without emojis
    formatted_output = format_repository_tree(repo_summary)
    
    print("\n  Sample formatted output:")
    print("  " + "="*50)
    lines = formatted_output.split('\n')
    for line in lines[:20]:  # Show first 20 lines
        print(f"  {line}")
    if len(lines) > 20:
        print(f"  ... ({len(lines) - 20} more lines)")
    print("  " + "="*50)
    
    # Verify formatting doesn't contain emojis
    emoji_chars = ["🚀", "📁", "📊", "🔍", "✅", "❌", "🔧", "📄"]
    for emoji in emoji_chars:
        assert emoji not in formatted_output, f"Found emoji {emoji} in output - should be removed"
    
    # Verify proper formatting structure
    assert "Repository:" in formatted_output, "Should contain repository header"
    assert "Language Support:" in formatted_output, "Should contain language support section"
    assert "PYTHON Files" in formatted_output or "python Files" in formatted_output, "Should contain Python files section"
    
    print("  Full package test PASSED")


def test_error_handling():
    """Test error handling and graceful degradation."""
    print("Testing Error Handling...")
    
    # Test with invalid code
    invalid_code = "this is not valid python code at all!!!"
    symbols = extract_symbols_generic(invalid_code, "python")
    # Should return empty list, not crash
    assert isinstance(symbols, list), "Should return list even for invalid code"
    
    # Test with unsupported language
    symbols = extract_symbols_generic("some code", "unsupported_language")
    assert isinstance(symbols, list), "Should return list for unsupported language"
    
    print("  Error handling test PASSED")


def main():
    """Run all Phase 3 tests."""
    print("="*60)
    print("FANCY_TREE Phase 3 Complete Test Suite")
    print("="*60)
    
    tests = [
        ("Python Extractor", test_python_extractor),
        ("TypeScript Extractor", test_typescript_extractor),
        ("Java Extractor", test_java_extractor),
        ("Registry System", test_registry_system),
        ("Full Package Test", test_full_package_on_self),
        ("Error Handling", test_error_handling)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n[{passed+1}/{total}] {test_name}")
        print("-" * 40)
        try:
            test_func()
            passed += 1
            print(f"RESULT: PASSED")
        except Exception as e:
            print(f"RESULT: FAILED - {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\nSUCCESS: All Phase 3 tests passed!")
        print("Phase 3 implementation is complete and ready.")
        print("Next: Implement CLI interface for Phase 4")
    else:
        print(f"\nFAILED: {total-passed} tests failed. Please fix issues.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 