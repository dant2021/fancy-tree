"""Signature extractor registry and initialization."""

from .base import SignatureExtractor, register_extractor, get_signature_extractor, list_supported_languages
from .python import PythonExtractor
from .typescript import TypeScriptExtractor
from .java import JavaExtractor
from .go import GoExtractor

# Register all available extractors
def initialize_extractors():
    """Initialize and register all signature extractors."""
    register_extractor("python", PythonExtractor())
    register_extractor("typescript", TypeScriptExtractor())
    register_extractor("java", JavaExtractor())
    register_extractor("go",     GoExtractor())

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