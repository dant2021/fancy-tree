"""Base classes for the signature extraction registry pattern."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from tree_sitter import Node


class SignatureExtractor(ABC):
    """Abstract base class for language-specific signature extractors."""
    
    @abstractmethod
    def extract_function_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract function signature using language-specific logic."""
        pass
    
    @abstractmethod
    def extract_class_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract class signature using language-specific logic."""
        pass
    
    def extract_method_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract method signature (defaults to function signature)."""
        return self.extract_function_signature(node, source_code, template)
    
    def get_node_text(self, node: Node, source_code: str | bytes) -> str:
        """
        Return the exact source substring represented by *node*.

        Tree-sitter reports byte offsets, therefore we must index the UTF-8
        encoded byte array, not the Python ``str``.
        """
        if isinstance(source_code, str):
            source_bytes = source_code.encode("utf-8")
        else:
            source_bytes = source_code

        return source_bytes[node.start_byte:node.end_byte].decode("utf-8")
    
    def find_child_by_type(self, node: Node, node_type: str) -> Optional[Node]:
        """Helper to find first child node of specific type."""
        for child in node.children:
            if child.type == node_type:
                return child
        return None
    
    def find_children_by_type(self, node: Node, node_type: str) -> list[Node]:
        """Helper to find all child nodes of specific type."""
        return [child for child in node.children if child.type == node_type]


class NotImplementedExtractor(SignatureExtractor):
    """Fallback extractor for languages without specific implementation."""
    
    def __init__(self, language: str):
        self.language = language
    
    def extract_function_signature(self, node: Node, source_code: str, template: str) -> str:
        """Return basic signature without language-specific logic."""
        name = self._extract_basic_name(node, source_code)
        return template.format(name=name, params="...", return_type="", visibility="")
    
    def extract_class_signature(self, node: Node, source_code: str, template: str) -> str:
        """Return basic class signature without language-specific logic."""
        name = self._extract_basic_name(node, source_code)
        return template.format(name=name, visibility="")
    
    def _extract_basic_name(self, node: Node, source_code: str) -> str:
        """Extract name using basic heuristics."""
        # Try to find identifier nodes
        for child in node.children:
            if "identifier" in child.type:
                return self.get_node_text(child, source_code)
        
        # Fallback to first child that looks like a name
        for child in node.children:
            if child.type in ["identifier", "type_identifier", "name"]:
                return self.get_node_text(child, source_code)
        
        return "unknown"


# Registry for signature extractors
SIGNATURE_EXTRACTORS: Dict[str, SignatureExtractor] = {}


def register_extractor(language: str, extractor: SignatureExtractor) -> None:
    """Register a signature extractor for a language."""
    SIGNATURE_EXTRACTORS[language] = extractor


def get_signature_extractor(language: str) -> SignatureExtractor:
    """Get signature extractor for language, with fallback."""
    if language in SIGNATURE_EXTRACTORS:
        return SIGNATURE_EXTRACTORS[language]
    else:
        # Return fallback extractor for unsupported languages
        fallback = NotImplementedExtractor(language)
        return fallback


def list_supported_languages() -> list[str]:
    """Get list of languages with implemented extractors."""
    return list(SIGNATURE_EXTRACTORS.keys())