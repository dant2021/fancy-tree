"""C++-specific signature extraction using tree-sitter."""

from .base import SignatureExtractor
from tree_sitter import Node
from typing import Optional


class CppExtractor(SignatureExtractor):
    """C++ signature extractor for functions, classes, and structs."""
    
    def extract_function_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract C++ function signature."""
        name = self._get_function_name(node, source_code)
        params = self._get_parameters(node, source_code)
        return_type = self._get_return_type(node, source_code)
        
        if return_type:
            return f"{return_type} {name}({params})"
        else:
            return f"{name}({params})"
    
    def extract_class_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract C++ class or struct signature."""
        name = self._get_class_name(node, source_code)
        inheritance = self._get_inheritance(node, source_code)
        
        if node.type == "class_specifier":
            if inheritance:
                return f"class {name} : {inheritance}"
            else:
                return f"class {name}"
        elif node.type == "struct_specifier":
            if inheritance:
                return f"struct {name} : {inheritance}"
            else:
                return f"struct {name}"
        elif node.type == "enum_specifier":
            return f"enum {name}"
        else:
            return f"type {name}"
    
    def _get_function_name(self, node: Node, source_code: str) -> str:
        """Extract function name."""
        if node.type == "function_definition":
            declarator = self.find_child_by_type(node, "function_declarator")
            if declarator:
                identifier = self.find_child_by_type(declarator, "identifier")
                if identifier:
                    return self.get_node_text(identifier, source_code)
        
        identifier = self.find_child_by_type(node, "identifier")
        if identifier:
            return self.get_node_text(identifier, source_code)
        
        return "unknown_function"
    
    def _get_class_name(self, node: Node, source_code: str) -> str:
        """Extract class name."""
        identifier = self.find_child_by_type(node, "type_identifier")
        if identifier:
            return self.get_node_text(identifier, source_code)
        return "unknown_class"
    
    def _get_parameters(self, node: Node, source_code: str) -> str:
        """Extract function parameters."""
        declarator = self.find_child_by_type(node, "function_declarator")
        if declarator:
            param_list = self.find_child_by_type(declarator, "parameter_list")
            if param_list:
                params_text = self.get_node_text(param_list, source_code)
                return params_text.strip("()")
        return ""
    
    def _get_return_type(self, node: Node, source_code: str) -> Optional[str]:
        """Extract return type."""
        if node.type == "function_definition" and node.children:
            first_child = node.children[0]
            if first_child.type != "function_declarator":
                return self.get_node_text(first_child, source_code)
        return None
    
    def _get_inheritance(self, node: Node, source_code: str) -> Optional[str]:
        """Extract class inheritance."""
        base_class_clause = self.find_child_by_type(node, "base_class_clause")
        if base_class_clause:
            # Get all base classes
            bases = []
            for child in base_class_clause.children:
                if child.type == "type_identifier":
                    bases.append(self.get_node_text(child, source_code))
            return ", ".join(bases) if bases else None
        return None 