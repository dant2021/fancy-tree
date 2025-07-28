"""C#-specific signature extraction using tree-sitter."""

from .base import SignatureExtractor
from tree_sitter import Node
from typing import Optional


class CsharpExtractor(SignatureExtractor):
    """C# signature extractor for methods, classes, and interfaces."""
    
    def extract_function_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract C# method signature."""
        visibility = self._get_visibility(node, source_code)
        name = self._get_method_name(node, source_code)
        params = self._get_parameters(node, source_code)
        return_type = self._get_return_type(node, source_code)
        
        parts = []
        if visibility:
            parts.append(visibility)
        if return_type:
            parts.append(return_type)
        parts.append(f"{name}({params})")
        
        return " ".join(parts)
    
    def extract_class_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract C# class or interface signature."""
        visibility = self._get_visibility(node, source_code)
        name = self._get_class_name(node, source_code)
        inheritance = self._get_inheritance(node, source_code)
        
        parts = []
        if visibility:
            parts.append(visibility)
        
        if node.type == "class_declaration":
            parts.append("class")
        elif node.type == "interface_declaration":
            parts.append("interface")
        elif node.type == "struct_declaration":
            parts.append("struct")
        
        parts.append(name)
        
        if inheritance:
            parts.append(f": {inheritance}")
        
        return " ".join(parts)
    
    def _get_visibility(self, node: Node, source_code: str) -> Optional[str]:
        """Extract visibility modifier."""
        modifiers = self.find_child_by_type(node, "modifiers")
        if modifiers:
            for child in modifiers.children:
                text = self.get_node_text(child, source_code)
                if text in ["public", "private", "protected", "internal"]:
                    return text
        return None
    
    def _get_method_name(self, node: Node, source_code: str) -> str:
        """Extract method name."""
        identifier = self.find_child_by_type(node, "identifier")
        if identifier:
            return self.get_node_text(identifier, source_code)
        return "unknown_method"
    
    def _get_class_name(self, node: Node, source_code: str) -> str:
        """Extract class name."""
        identifier = self.find_child_by_type(node, "identifier")
        if identifier:
            return self.get_node_text(identifier, source_code)
        return "unknown_class"
    
    def _get_parameters(self, node: Node, source_code: str) -> str:
        """Extract method parameters."""
        param_list = self.find_child_by_type(node, "parameter_list")
        if param_list:
            params_text = self.get_node_text(param_list, source_code)
            return params_text.strip("()")
        return ""
    
    def _get_return_type(self, node: Node, source_code: str) -> Optional[str]:
        """Extract return type."""
        # Look for type before the method name
        for child in node.children:
            if child.type in ["predefined_type", "identifier", "generic_name"]:
                return self.get_node_text(child, source_code)
        return None
    
    def _get_inheritance(self, node: Node, source_code: str) -> Optional[str]:
        """Extract class inheritance."""
        base_list = self.find_child_by_type(node, "base_list")
        if base_list:
            bases = []
            for child in base_list.children:
                if child.type == "identifier":
                    bases.append(self.get_node_text(child, source_code))
            return ", ".join(bases) if bases else None
        return None