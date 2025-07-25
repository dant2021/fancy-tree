"""TypeScript-specific signature extraction using tree-sitter."""

from .base import SignatureExtractor
from tree_sitter import Node
from typing import Optional, List


class TypeScriptExtractor(SignatureExtractor):
    """TypeScript signature extractor for functions, methods, classes, and interfaces."""
    
    def extract_function_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract TypeScript function signature."""
        name = self._get_function_name(node, source_code)
        params = self._get_parameters(node, source_code)
        return_type = self._get_return_type(node, source_code)
        
        if node.type == "method_definition":
            # Method signature
            if return_type:
                return f"{name}({params}): {return_type}"
            else:
                return f"{name}({params})"
        else:
            # Function signature
            if return_type:
                return f"function {name}({params}): {return_type}"
            else:
                return f"function {name}({params})"
    
    def extract_class_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract TypeScript class or interface signature."""
        name = self._get_class_name(node, source_code)
        
        if node.type == "interface_declaration":
            inheritance = self._get_interface_inheritance(node, source_code)
            if inheritance:
                return f"interface {name} extends {inheritance}"
            else:
                return f"interface {name}"
        else:
            # Class declaration
            inheritance = self._get_class_inheritance(node, source_code)
            if inheritance:
                return f"class {name} extends {inheritance}"
            else:
                return f"class {name}"
    
    def _get_function_name(self, node: Node, source_code: str) -> str:
        """Extract function or method name."""
        # Try different identifier types
        for child_type in ["identifier", "property_identifier"]:
            name_node = self.find_child_by_type(node, child_type)
            if name_node:
                return self.get_node_text(name_node, source_code)
        return "unknown_function"
    
    def _get_class_name(self, node: Node, source_code: str) -> str:
        """Extract class or interface name."""
        for child_type in ["type_identifier", "identifier"]:
            name_node = self.find_child_by_type(node, child_type)
            if name_node:
                return self.get_node_text(name_node, source_code)
        return "unknown_class"
    
    def _get_parameters(self, node: Node, source_code: str) -> str:
        """Extract function parameters with types."""
        params_node = self.find_child_by_type(node, "formal_parameters")
        if params_node:
            params_text = self.get_node_text(params_node, source_code)
            return params_text.strip("()")
        return ""
    
    def _get_return_type(self, node: Node, source_code: str) -> Optional[str]:
        """Extract return type annotation."""
        type_annotation = self.find_child_by_type(node, "type_annotation")
        if type_annotation:
            # Get the type part (skip the ':')
            for child in type_annotation.children:
                if child.type != ":":
                    return self.get_node_text(child, source_code)
        return None
    
    def _get_class_inheritance(self, node: Node, source_code: str) -> Optional[str]:
        """Extract class inheritance."""
        heritage_clause = self.find_child_by_type(node, "class_heritage")
        if heritage_clause:
            extends_clause = self.find_child_by_type(heritage_clause, "extends_clause")
            if extends_clause:
                # Find the type being extended
                for child in extends_clause.children:
                    if child.type in ["identifier", "type_identifier"]:
                        return self.get_node_text(child, source_code)
        return None
    
    def _get_interface_inheritance(self, node: Node, source_code: str) -> Optional[str]:
        """Extract interface inheritance."""
        heritage_clause = self.find_child_by_type(node, "extends_clause")
        if heritage_clause:
            # Get all extended interfaces
            extended = []
            for child in heritage_clause.children:
                if child.type in ["identifier", "type_identifier"]:
                    extended.append(self.get_node_text(child, source_code))
            return ", ".join(extended) if extended else None
        return None 