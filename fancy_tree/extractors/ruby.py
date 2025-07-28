"""Ruby-specific signature extraction using tree-sitter."""

from .base import SignatureExtractor
from tree_sitter import Node
from typing import Optional


class RubyExtractor(SignatureExtractor):
    """Ruby signature extractor for methods, classes, and modules."""
    
    def extract_function_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract Ruby method signature."""
        name = self._get_method_name(node, source_code)
        params = self._get_parameters(node, source_code)
        
        if params:
            return f"def {name}({params})"
        else:
            return f"def {name}"
    
    def extract_class_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract Ruby class or module signature."""
        name = self._get_name(node, source_code)
        inheritance = self._get_inheritance(node, source_code)
        
        if node.type == "class":
            if inheritance:
                return f"class {name} < {inheritance}"
            else:
                return f"class {name}"
        elif node.type == "module":
            return f"module {name}"
        else:
            return f"class {name}"
    
    def _get_method_name(self, node: Node, source_code: str) -> str:
        """Extract method name."""
        for child_type in ["identifier", "constant"]:
            name_node = self.find_child_by_type(node, child_type)
            if name_node:
                return self.get_node_text(name_node, source_code)
        return "unknown_method"
    
    def _get_name(self, node: Node, source_code: str) -> str:
        """Extract class/module name."""
        for child_type in ["constant", "identifier"]:
            name_node = self.find_child_by_type(node, child_type)
            if name_node:
                return self.get_node_text(name_node, source_code)
        return "unknown"
    
    def _get_parameters(self, node: Node, source_code: str) -> str:
        """Extract method parameters."""
        method_params = self.find_child_by_type(node, "method_parameters")
        if method_params:
            params_text = self.get_node_text(method_params, source_code)
            return params_text.strip("()")
        return ""
    
    def _get_inheritance(self, node: Node, source_code: str) -> Optional[str]:
        """Extract class inheritance."""
        superclass = self.find_child_by_type(node, "superclass")
        if superclass:
            constant = self.find_child_by_type(superclass, "constant")
            if constant:
                return self.get_node_text(constant, source_code)
        return None 