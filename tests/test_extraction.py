"""Test script to verify fancy_tree extraction works correctly."""

import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

sys.path.insert(0, str(Path(__file__).parent.parent))

console = Console()

def test_parser_loading():
    """Test that tree-sitter parsers load correctly."""
    console.print(Panel("🔍 Testing Parser Loading", style="bold blue"))
    
    try:
        from core.extraction import get_parser_for_language
        
        test_languages = ["python", "typescript", "java"]
        results = {}
        
        for lang in test_languages:
            parser = get_parser_for_language(lang)
            results[lang] = parser is not None
            status = "✅" if parser else "❌"
            console.print(f"  {status} {lang} parser")
        
        return all(results.values())
        
    except Exception as e:
        console.print(f"❌ Parser loading failed: {e}")
        return False

def test_extraction_on_sample(language: str, sample_code: str, expected_symbols: int):
    """Test symbol extraction on sample code."""
    try:
        from core.extraction import extract_symbols_generic
        
        symbols = extract_symbols_generic(sample_code, language)
        
        console.print(f"📝 {language.title()} extraction:")
        console.print(f"  Expected: {expected_symbols} symbols")
        console.print(f"  Found: {len(symbols)} symbols")
        
        for symbol in symbols:
            console.print(f"    • {symbol.type.value}: {symbol.name} (line {symbol.line})")
            if symbol.signature:
                console.print(f"      Signature: {symbol.signature}")
            for child in symbol.children:
                console.print(f"      ↳ {child.type.value}: {child.name} (line {child.line})")
        
        return len(symbols) >= expected_symbols
        
    except Exception as e:
        console.print(f"❌ {language} extraction failed: {e}")
        import traceback
        console.print(traceback.format_exc())
        return False

def test_full_repository():
    """Test processing the current repository."""
    console.print(Panel("📁 Testing Full Repository Processing", style="bold green"))
    
    try:
        from core.extraction import process_repository
        from core.formatter import format_repository_tree
        
        repo_path = Path(".")
        console.print(f"Processing: {repo_path.absolute()}")
        
        repo_summary = process_repository(repo_path)
        formatted_output = format_repository_tree(repo_summary)
        
        console.print(f"✅ Processed {repo_summary.total_files} files")
        console.print(f"✅ Languages: {list(repo_summary.languages.keys())}")
        
        # Show first 20 lines of output
        lines = formatted_output.split('\n')
        console.print("\n📄 Output Preview:")
        console.print("─" * 60)
        for line in lines[:20]:
            console.print(line)
        if len(lines) > 20:
            console.print(f"... ({len(lines) - 20} more lines)")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Repository processing failed: {e}")
        import traceback
        console.print(traceback.format_exc())
        return False

def main():
    """Run all tests."""
    console.print(Panel.fit("🧪 FANCY_TREE Extraction Testing", style="bold white on blue"))
    
    # Sample code for testing
    python_sample = '''
class UserManager:
    def __init__(self, db_connection):
        self.db = db_connection
    
    def create_user(self, name: str, email: str) -> bool:
        """Create a new user."""
        return True
    
    def delete_user(self, user_id: int) -> bool:
        """Delete a user by ID."""
        return False

def calculate_total(items: list) -> float:
    """Calculate total price of items."""
    return sum(item.price for item in items)

async def fetch_data():
    """Fetch data asynchronously."""
    pass
'''

    typescript_sample = '''
interface UserData {
    id: number;
    name: string;
    email: string;
}

class UserService {
    private apiUrl: string;
    
    constructor(apiUrl: string) {
        this.apiUrl = apiUrl;
    }
    
    async createUser(userData: UserData): Promise<boolean> {
        return true;
    }
    
    deleteUser(id: number): boolean {
        return false;
    }
}

function calculateTotal(items: any[]): number {
    return items.reduce((sum, item) => sum + item.price, 0);
}
'''

    java_sample = '''
public interface UserRepository {
    boolean save(User user);
    User findById(int id);
}

public class UserService {
    private UserRepository repository;
    
    public UserService(UserRepository repository) {
        this.repository = repository;
    }
    
    public boolean createUser(String name, String email) {
        User user = new User(name, email);
        return repository.save(user);
    }
    
    public User getUserById(int id) {
        return repository.findById(id);
    }
    
    private void validateUser(User user) {
        // validation logic
    }
}
'''

    tests = [
        ("Parser Loading", test_parser_loading),
        ("Python Extraction", lambda: test_extraction_on_sample("python", python_sample, 3)),  # UserManager, create_user, delete_user, calculate_total, fetch_data
        ("TypeScript Extraction", lambda: test_extraction_on_sample("typescript", typescript_sample, 3)),  # UserData, UserService, calculateTotal
        ("Java Extraction", lambda: test_extraction_on_sample("java", java_sample, 2)),  # UserRepository, UserService
        ("Full Repository", test_full_repository)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        console.print(f"\n{'='*60}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            console.print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    console.print(f"\n{'='*60}")
    console.print(Panel("📊 Test Results", style="bold white"))
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        icon = "✅" if result else "❌"
        console.print(f"  {icon} {test_name}")
    
    if passed == total:
        console.print(f"\n🎉 All {total} tests passed! Extraction is working!")
    else:
        console.print(f"\n⚠️ {total-passed}/{total} tests failed.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)