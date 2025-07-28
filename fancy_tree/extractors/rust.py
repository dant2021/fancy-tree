"""Rust-specific signature extraction using tree-sitter."""

from .base import SignatureExtractor
from tree_sitter import Node
from typing import Optional


class RustExtractor(SignatureExtractor):
    """Rust signature extractor for functions, structs, traits, and impls."""
    
    def extract_function_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract Rust function signature."""
        name = self._get_function_name(node, source_code)
        params = self._get_parameters(node, source_code)
        return_type = self._get_return_type(node, source_code)
        
        if return_type:
            return f"fn {name}({params}) -> {return_type}"
        else:
            return f"fn {name}({params})"
    
    def extract_class_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract Rust struct, trait, or impl signature."""
        name = self._get_name(node, source_code)
        
        if node.type == "struct_item":
            return f"struct {name}"
        elif node.type == "trait_item":
            return f"trait {name}"
        elif node.type == "impl_item":
            return f"impl {name}"
        else:
            return f"type {name}"
    
    def _get_function_name(self, node: Node, source_code: str) -> str:
        """Extract function name."""
        name_node = self.find_child_by_type(node, "identifier")
        if name_node:
            return self.get_node_text(name_node, source_code)
        return "unknown_function"
    
    def _get_name(self, node: Node, source_code: str) -> str:
        """Extract type name."""
        for child_type in ["type_identifier", "identifier"]:
            name_node = self.find_child_by_type(node, child_type)
            if name_node:
                return self.get_node_text(name_node, source_code)
        return "unknown"
    
    def _get_parameters(self, node: Node, source_code: str) -> str:
        """Extract function parameters."""
        params_node = self.find_child_by_type(node, "parameters")
        if params_node:
            params_text = self.get_node_text(params_node, source_code)
            return params_text.strip("()")
        return ""
    
    def _get_return_type(self, node: Node, source_code: str) -> Optional[str]:
        """Extract return type."""
        # Look for -> return_type pattern
        for child in node.children:
            if self.get_node_text(child, source_code).strip() == "->":
                # Next sibling should be the return type
                next_idx = node.children.index(child) + 1
                if next_idx < len(node.children):
                    return self.get_node_text(node.children[next_idx], source_code)
        return None 