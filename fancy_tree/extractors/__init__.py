"""Signature extractor registry and initialization."""

from .base import SignatureExtractor, register_extractor, get_signature_extractor, list_supported_languages
from .python import PythonExtractor
from .typescript import TypeScriptExtractor
from .java import JavaExtractor
from .go import GoExtractor
from .javascript import JavaScriptExtractor
from .rust import RustExtractor
from .c import CExtractor
from .cpp import CppExtractor
from .csharp import CsharpExtractor
from .php import PhpExtractor
from .ruby import RubyExtractor


# Register all available extractors
def initialize_extractors():
    """Initialize and register all signature extractors."""
    register_extractor("python", PythonExtractor())
    register_extractor("typescript", TypeScriptExtractor())
    register_extractor("java", JavaExtractor())
    register_extractor("go", GoExtractor())
    register_extractor("javascript", JavaScriptExtractor())
    register_extractor("rust", RustExtractor())
    register_extractor("c", CExtractor())
    register_extractor("cpp", CppExtractor())
    register_extractor("csharp", CsharpExtractor())
    register_extractor("php", PhpExtractor())
    register_extractor("ruby", RubyExtractor())

# Auto-initialize when module is imported
initialize_extractors()

__all__ = [
    "SignatureExtractor",
    "get_signature_extractor", 
    "list_supported_languages",
    "PythonExtractor",
    "TypeScriptExtractor", 
    "JavaExtractor"
]