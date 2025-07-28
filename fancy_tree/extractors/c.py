"""C-specific signature extraction using tree-sitter."""

from .base import SignatureExtractor
from tree_sitter import Node
from typing import Optional


class CExtractor(SignatureExtractor):
    """C signature extractor for functions, structs, and enums."""
    
    def extract_function_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract C function signature."""
        name = self._get_function_name(node, source_code)
        params = self._get_parameters(node, source_code)
        return_type = self._get_return_type(node, source_code)
        
        if return_type:
            return f"{return_type} {name}({params})"
        else:
            return f"{name}({params})"
    
    def extract_class_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract C struct or enum signature."""
        name = self._get_struct_name(node, source_code)
        
        if node.type == "struct_specifier":
            return f"struct {name}"
        elif node.type == "union_specifier":
            return f"union {name}"
        elif node.type == "enum_specifier":
            return f"enum {name}"
        else:
            return f"type {name}"
    
    def _get_function_name(self, node: Node, source_code: str) -> str:
        """Extract function name."""
        # For function_definition, look for function_declarator
        if node.type == "function_definition":
            declarator = self.find_child_by_type(node, "function_declarator")
            if declarator:
                identifier = self.find_child_by_type(declarator, "identifier")
                if identifier:
                    return self.get_node_text(identifier, source_code)
        
        # For function_declarator, find identifier directly
        identifier = self.find_child_by_type(node, "identifier")
        if identifier:
            return self.get_node_text(identifier, source_code)
        
        return "unknown_function"
    
    def _get_struct_name(self, node: Node, source_code: str) -> str:
        """Extract struct/enum name."""
        identifier = self.find_child_by_type(node, "type_identifier")
        if identifier:
            return self.get_node_text(identifier, source_code)
        return "anonymous"
    
    def _get_parameters(self, node: Node, source_code: str) -> str:
        """Extract function parameters."""
        # Look for parameter_list in function_declarator
        declarator = self.find_child_by_type(node, "function_declarator")
        if declarator:
            param_list = self.find_child_by_type(declarator, "parameter_list")
            if param_list:
                params_text = self.get_node_text(param_list, source_code)
                return params_text.strip("()")
        return ""
    
    def _get_return_type(self, node: Node, source_code: str) -> Optional[str]:
        """Extract return type."""
        # For function_definition, the first child is usually the return type
        if node.type == "function_definition" and node.children:
            first_child = node.children[0]
            if first_child.type != "function_declarator":
                return self.get_node_text(first_child, source_code)
        return None 