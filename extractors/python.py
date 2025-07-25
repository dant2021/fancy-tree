"""Python-specific signature extraction using tree-sitter."""

from .base import SignatureExtractor
from tree_sitter import Node
from typing import Optional, List


class PythonExtractor(SignatureExtractor):
    """Python signature extractor with full support for functions, methods, and classes."""
    
    def extract_function_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract Python function signature with parameters and return type."""
        name = self._get_function_name(node, source_code)
        params = self._get_parameters(node, source_code)
        return_type = self._get_return_type(node, source_code)
        
        if return_type:
            return f"def {name}({params}) -> {return_type}"
        else:
            return f"def {name}({params})"
    
    def extract_class_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract Python class signature with inheritance."""
        name = self._get_class_name(node, source_code)
        inheritance = self._get_inheritance(node, source_code)
        
        if inheritance:
            return f"class {name}({inheritance})"
        else:
            return f"class {name}"
    
    def _get_function_name(self, node: Node, source_code: str) -> str:
        """Extract function name from function_definition node."""
        name_node = self.find_child_by_type(node, "identifier")
        if name_node:
            return self.get_node_text(name_node, source_code)
        return "unknown_function"
    
    def _get_class_name(self, node: Node, source_code: str) -> str:
        """Extract class name from class_definition node."""
        name_node = self.find_child_by_type(node, "identifier")
        if name_node:
            return self.get_node_text(name_node, source_code)
        return "unknown_class"
    
    def _get_parameters(self, node: Node, source_code: str) -> str:
        """Extract function parameters."""
        params_node = self.find_child_by_type(node, "parameters")
        if params_node:
            return self.get_node_text(params_node, source_code).strip("()")
        return ""
    
    def _get_return_type(self, node: Node, source_code: str) -> Optional[str]:
        """Extract return type annotation if present."""
        for child in node.children:
            if child.type == "type":
                return self.get_node_text(child, source_code)
        return None
    
    def _get_inheritance(self, node: Node, source_code: str) -> Optional[str]:
        """Extract inheritance information from class."""
        argument_list = self.find_child_by_type(node, "argument_list")
        if argument_list:
            return self.get_node_text(argument_list, source_code).strip("()")
        return None 