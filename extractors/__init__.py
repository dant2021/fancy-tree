"""Signature extractors for language-specific symbol processing."""

from .base import (
    SignatureExtractor, 
    NotImplementedExtractor,
    register_extractor, 
    get_signature_extractor,
    list_supported_languages,
    SIGNATURE_EXTRACTORS
)

# Import specific extractors (will be implemented in Phase 3)
# from .python import PythonExtractor
# from .typescript import TypeScriptExtractor  
# from .java import JavaExtractor

# Register extractors (will be activated in Phase 3)
# register_extractor("python", PythonExtractor())
# register_extractor("typescript", TypeScriptExtractor())
# register_extractor("java", JavaExtractor())

__all__ = [
    "SignatureExtractor",
    "NotImplementedExtractor", 
    "register_extractor",
    "get_signature_extractor",
    "list_supported_languages",
    "SIGNATURE_EXTRACTORS"
]