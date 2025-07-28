"""PHP-specific signature extraction using tree-sitter."""

from .base import SignatureExtractor
from tree_sitter import Node
from typing import Optional


class PhpExtractor(SignatureExtractor):
    """PHP signature extractor for functions, methods, and classes."""
    
    def extract_function_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract PHP function signature."""
        name = self._get_function_name(node, source_code)
        params = self._get_parameters(node, source_code)
        
        return f"function {name}({params})"
    
    def extract_class_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract PHP class signature."""
        name = self._get_class_name(node, source_code)
        inheritance = self._get_inheritance(node, source_code)
        
        if node.type == "class_declaration":
            if inheritance:
                return f"class {name} extends {inheritance}"
            else:
                return f"class {name}"
        elif node.type == "interface_declaration":
            return f"interface {name}"
        elif node.type == "trait_declaration":
            return f"trait {name}"
        else:
            return f"class {name}"
    
    def _get_function_name(self, node: Node, source_code: str) -> str:
        """Extract function name."""
        name_node = self.find_child_by_type(node, "name")
        if name_node:
            return self.get_node_text(name_node, source_code)
        return "unknown_function"
    
    def _get_class_name(self, node: Node, source_code: str) -> str:
        """Extract class name."""
        name_node = self.find_child_by_type(node, "name")
        if name_node:
            return self.get_node_text(name_node, source_code)
        return "unknown_class"
    
    def _get_parameters(self, node: Node, source_code: str) -> str:
        """Extract function parameters."""
        formal_params = self.find_child_by_type(node, "formal_parameters")
        if formal_params:
            params_text = self.get_node_text(formal_params, source_code)
            return params_text.strip("()")
        return ""
    
    def _get_inheritance(self, node: Node, source_code: str) -> Optional[str]:
        """Extract class inheritance."""
        base_clause = self.find_child_by_type(node, "base_clause")
        if base_clause:
            name_node = self.find_child_by_type(base_clause, "name")
            if name_node:
                return self.get_node_text(name_node, source_code)
        return None 