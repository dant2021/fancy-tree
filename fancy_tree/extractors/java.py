"""Java-specific signature extraction using tree-sitter."""

from .base import SignatureExtractor
from tree_sitter import Node
from typing import Optional, List


class JavaExtractor(SignatureExtractor):
    """Java signature extractor for methods and classes."""
    
    def extract_function_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract Java method signature with modifiers, return type, and parameters."""
        modifiers = self._get_modifiers(node, source_code)
        return_type = self._get_return_type(node, source_code)
        name = self._get_method_name(node, source_code)
        params = self._get_parameters(node, source_code)
        
        parts = []
        if modifiers:
            parts.append(modifiers)
        if return_type:
            parts.append(return_type)
        parts.append(f"{name}({params})")
        
        return " ".join(parts)
    
    def extract_class_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract Java class signature with modifiers and inheritance."""
        modifiers = self._get_modifiers(node, source_code)
        name = self._get_class_name(node, source_code)
        inheritance = self._get_inheritance(node, source_code)
        
        parts = []
        if modifiers:
            parts.append(modifiers)
        parts.append("class")
        parts.append(name)
        if inheritance:
            parts.append(inheritance)
        
        return " ".join(parts)
    
    def _get_modifiers(self, node: Node, source_code: str) -> Optional[str]:
        """Extract access modifiers and other modifiers."""
        modifiers = []
        modifiers_node = self.find_child_by_type(node, "modifiers")
        if modifiers_node:
            for child in modifiers_node.children:
                modifier_text = self.get_node_text(child, source_code)
                modifiers.append(modifier_text)
        return " ".join(modifiers) if modifiers else None
    
    def _get_method_name(self, node: Node, source_code: str) -> str:
        """Extract method name."""
        name_node = self.find_child_by_type(node, "identifier")
        if name_node:
            return self.get_node_text(name_node, source_code)
        return "unknown_method"
    
    def _get_class_name(self, node: Node, source_code: str) -> str:
        """Extract class name."""
        name_node = self.find_child_by_type(node, "identifier")
        if name_node:
            return self.get_node_text(name_node, source_code)
        return "unknown_class"
    
    def _get_parameters(self, node: Node, source_code: str) -> str:
        """Extract method parameters with types."""
        params_node = self.find_child_by_type(node, "formal_parameters")
        if params_node:
            params_text = self.get_node_text(params_node, source_code)
            return params_text.strip("()")
        return ""
    
    def _get_return_type(self, node: Node, source_code: str) -> Optional[str]:
        """Extract return type."""
        # Look for type nodes
        for child in node.children:
            if child.type in ["type_identifier", "primitive_type", "generic_type", "array_type"]:
                return self.get_node_text(child, source_code)
        return None
    
    def _get_inheritance(self, node: Node, source_code: str) -> Optional[str]:
        """Extract inheritance information."""
        parts = []
        
        # Check for extends clause
        superclass = self.find_child_by_type(node, "superclass")
        if superclass:
            type_node = self.find_child_by_type(superclass, "type_identifier")
            if type_node:
                parts.append(f"extends {self.get_node_text(type_node, source_code)}")
        
        # Check for implements clause
        super_interfaces = self.find_child_by_type(node, "super_interfaces")
        if super_interfaces:
            interfaces = []
            for child in super_interfaces.children:
                if child.type == "type_identifier":
                    interfaces.append(self.get_node_text(child, source_code))
            if interfaces:
                parts.append(f"implements {', '.join(interfaces)}")
        
        return " ".join(parts) if parts else None 