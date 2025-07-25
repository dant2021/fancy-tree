# Test tree-sitter-languages directly
from tree_sitter_languages import get_language
from tree_sitter import Parser

# Test getting a language
try:
    python_lang = get_language("python")
    print(f"✓ get_language('python') worked: {type(python_lang)}")
    
    # Test creating parser
    parser = Parser()
    print(f"✓ Parser() worked: {type(parser)}")
    
    # Test setting language - this might be where it breaks
    parser.set_language(python_lang)
    print("✓ parser.set_language() worked")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()