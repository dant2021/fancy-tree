"""JavaScript-specific signature extraction using tree-sitter."""

from .base import SignatureExtractor
from tree_sitter import Node
from typing import Optional


class JavaScriptExtractor(SignatureExtractor):
    """JavaScript signature extractor for functions, methods, and classes."""
    
    def extract_function_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract JavaScript function signature."""
        name = self._get_function_name(node, source_code)
        params = self._get_parameters(node, source_code)
        
        if node.type == "method_definition":
            # Method signature
            return f"{name}({params})"
        elif node.type == "arrow_function":
            # Arrow function - try to get name from parent assignment
            arrow_name = self._get_arrow_function_name(node, source_code)
            return f"{arrow_name} = ({params}) => {{}}"
        else:
            # Regular function declaration
            return f"function {name}({params})"
    
    def extract_class_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract JavaScript class signature."""
        name = self._get_class_name(node, source_code)
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
        return "anonymous"
    
    def _get_arrow_function_name(self, node: Node, source_code: str) -> str:
        """Extract name for arrow functions from parent assignment."""
        # Check if parent is an assignment
        parent = node.parent
        if parent and parent.type in ["assignment_expression", "variable_declarator"]:
            # Look for identifier in the assignment
            identifier = self.find_child_by_type(parent, "identifier")
            if identifier:
                return self.get_node_text(identifier, source_code)
        return "anonymous"
    
    def _get_class_name(self, node: Node, source_code: str) -> str:
        """Extract class name."""
        name_node = self.find_child_by_type(node, "identifier")
        if name_node:
            return self.get_node_text(name_node, source_code)
        return "unknown_class"
    
    def _get_parameters(self, node: Node, source_code: str) -> str:
        """Extract function parameters."""
        params_node = self.find_child_by_type(node, "formal_parameters")
        if params_node:
            params_text = self.get_node_text(params_node, source_code)
            return params_text.strip("()")
        return ""
    
    def _get_class_inheritance(self, node: Node, source_code: str) -> Optional[str]:
        """Extract class inheritance."""
        heritage_clause = self.find_child_by_type(node, "class_heritage")
        if heritage_clause:
            # Find the extends clause
            for child in heritage_clause.children:
                if child.type == "extends_clause":
                    # Get the class being extended
                    identifier = self.find_child_by_type(child, "identifier")
                    if identifier:
                        return self.get_node_text(identifier, source_code)
        return None 