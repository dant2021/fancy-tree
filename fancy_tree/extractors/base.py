"""Base classes for the signature extraction registry pattern."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from tree_sitter import Node
from typing import Union


def node_type(node: Node) -> str:
    """Return the node kind across tree-sitter Node API versions."""
    node_kind = getattr(node, "type", None)
    if node_kind is None:
        node_kind = node.kind
    if callable(node_kind):
        node_kind = node_kind()
    return node_kind


def node_children(node: Node) -> list[Node]:
    """Return child nodes across sequence and child_count/child APIs."""
    children = getattr(node, "children", None)
    if callable(children):
        children = children()
    if children is not None:
        return children
    child_count = node.child_count
    if callable(child_count):
        child_count = child_count()
    return [node.child(i) for i in range(child_count)]


def node_start_byte(node: Node) -> int:
    """Return the start byte across property and callable APIs."""
    start_byte = node.start_byte
    return start_byte() if callable(start_byte) else start_byte


def node_end_byte(node: Node) -> int:
    """Return the end byte across property and callable APIs."""
    end_byte = node.end_byte
    return end_byte() if callable(end_byte) else end_byte


def node_parent(node: Node) -> Optional[Node]:
    """Return the parent node across property and callable APIs."""
    parent = node.parent
    return parent() if callable(parent) else parent


# Expressions that wrap an arrow function without changing what it is bound to.
ARROW_WRAPPER_NODES = (
    "parenthesized_expression",
    "as_expression",
    "satisfies_expression",
    "type_assertion",
    "non_null_expression",
)
# Nodes that bind an arrow function, mapped to the field holding the bound name.
ARROW_BINDING_NAME_FIELDS = {
    "variable_declarator": "name",
    "pair": "key",
    "public_field_definition": "name",  # TypeScript class field
    "field_definition": "property",  # JavaScript class field
}
# Destructuring patterns and computed keys do not give an arrow a single name.
ARROW_BINDING_NAME_NODES = (
    "identifier",
    "property_identifier",
    "private_property_identifier",
    "string",
    "number",
)
CLASS_FIELD_NODES = ("public_field_definition", "field_definition")

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

    def get_symbol_name(
        self, node: Node, source_code: str, name_nodes=None
    ) -> Optional[str]:
        """Prefer the grammar's name field, with configured fallbacks for other grammars."""
        if self.node_type(node) == "arrow_function":
            return self.get_arrow_function_name(node, source_code)
        name = node.child_by_field_name("name")
        if name is not None:
            return self.get_node_text(name, source_code)
        for child in self.node_children(node):
            if self.node_type(child) in (name_nodes or ["identifier"]):
                return self.get_node_text(child, source_code)
        return None

    def get_arrow_binding(self, node: Node) -> Optional[Node]:
        """Return the declarator, pair or class field an arrow function is bound to."""
        # Parentheses and type assertions do not change an arrow's binding.
        value = node
        parent = node_parent(node)
        while parent is not None and self.node_type(parent) in ARROW_WRAPPER_NODES:
            value = parent
            parent = node_parent(parent)
        if parent is None or self.node_type(parent) not in ARROW_BINDING_NAME_FIELDS:
            return None
        if parent.child_by_field_name("value") != value:
            return None
        return parent

    def get_arrow_function_name(self, node: Node, source_code: str) -> Optional[str]:
        """Name arrows by their binding; callbacks have no emitted identity."""
        binding = self.get_arrow_binding(node)
        if binding is None:
            return None
        name = binding.child_by_field_name(
            ARROW_BINDING_NAME_FIELDS[self.node_type(binding)]
        )
        if name is not None and self.node_type(name) in ARROW_BINDING_NAME_NODES:
            return self.get_node_text(name, source_code)
        return None

    def get_node_text(self, node: Node, source_code: Union[str, bytes]) -> str:
        """
        Return the exact source substring represented by *node*.

        Tree-sitter reports byte offsets, therefore we must index the UTF-8
        encoded byte array, not the Python ``str``.
        """
        if isinstance(source_code, str):
            source_bytes = source_code.encode("utf-8")
        else:
            source_bytes = source_code

        return source_bytes[node_start_byte(node):node_end_byte(node)].decode("utf-8")

    def node_type(self, node: Node) -> str:
        """Return the node kind across tree-sitter Node API versions."""
        return node_type(node)

    def node_children(self, node: Node) -> list[Node]:
        """Return child nodes across sequence and child_count/child APIs."""
        return node_children(node)
    
    def find_child_by_type(self, node: Node, node_type: Union[str, tuple[str, ...]]) -> Optional[Node]:
        """Helper to find first child node of specific type."""
        for child in self.node_children(node):
            child_type = self.node_type(child)
            if child_type == node_type or (
                isinstance(node_type, tuple) and child_type in node_type
            ):
                return child
        return None
    
    def find_children_by_type(self, node: Node, node_type: Union[str, tuple[str, ...]]) -> list[Node]:
        """Helper to find all child nodes of specific type."""
        return [
            child
            for child in self.node_children(node)
            if self.node_type(child) == node_type
            or (isinstance(node_type, tuple) and self.node_type(child) in node_type)
        ]


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
        for child in self.node_children(node):
            if "identifier" in self.node_type(child):
                return self.get_node_text(child, source_code)
        
        # Fallback to first child that looks like a name
        for child in self.node_children(node):
            if self.node_type(child) in ["identifier", "type_identifier", "name"]:
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
