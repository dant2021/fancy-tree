"""TypeScript-specific signature extraction using tree-sitter."""

from .base import SignatureExtractor
from tree_sitter import Node
from typing import Optional, List


class TypeScriptExtractor(SignatureExtractor):
    """TypeScript signature extractor for functions, methods, classes, and interfaces."""
    
    def extract_function_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract TypeScript function signature."""
        name = self.get_function_name(node, source_code) or "anonymous"
        params = self._get_parameters(node, source_code)
        return_type = self._get_return_type(node, source_code)
        
        if self.node_type(node) in ("method_definition", "method_signature"):
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
        
        if self.node_type(node) == "interface_declaration":
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
    
    def get_function_name(
        self, node: Node, source_code: str, name_nodes=None
    ) -> Optional[str]:
        """Resolve declarations and bound arrows; callbacks have no emitted identity."""
        if self.node_type(node) != "arrow_function":
            name = node.child_by_field_name("name")
            return self.get_node_text(name, source_code) if name is not None else None

        # Parentheses and type assertions do not change an arrow's binding.
        value = node
        parent = node.parent
        if callable(parent):
            parent = parent()
        while parent is not None and self.node_type(parent) in (
            "parenthesized_expression",
            "as_expression",
            "satisfies_expression",
            "type_assertion",
            "non_null_expression",
        ):
            value = parent
            parent = parent.parent
            if callable(parent):
                parent = parent()

        if parent is None or parent.child_by_field_name("value") != value:
            return None
        parent_type = self.node_type(parent)
        if parent_type == "variable_declarator":
            name = parent.child_by_field_name("name")
            allowed = ("identifier",)
        elif parent_type in ("pair", "public_field_definition"):
            name = parent.child_by_field_name(
                "key" if parent_type == "pair" else "name"
            )
            allowed = (
                "property_identifier",
                "private_property_identifier",
                "string",
                "number",
            )
        else:
            return None
        if name is not None and self.node_type(name) in allowed:
            return self.get_node_text(name, source_code)
        return None
    
    def _get_class_name(self, node: Node, source_code: str) -> str:
        """Extract class or interface name."""
        for child_type in ["type_identifier", "identifier"]:
            name_node = self.find_child_by_type(node, child_type)
            if name_node:
                return self.get_node_text(name_node, source_code)
        return "unknown_class"
    
    def _get_parameters(self, node: Node, source_code: str) -> str:
        """Extract function parameters with types."""
        params_node = node.child_by_field_name("parameters")
        if params_node is not None:
            params_text = self.get_node_text(params_node, source_code)
            return params_text[1:-1]
        parameter = node.child_by_field_name("parameter")
        if parameter is not None:
            return self.get_node_text(parameter, source_code)
        return ""
    
    def _get_return_type(self, node: Node, source_code: str) -> Optional[str]:
        """Extract return type annotation."""
        type_annotation = self.find_child_by_type(node, "type_annotation")
        if type_annotation:
            # Get the type part (skip the ':')
            for child in self.node_children(type_annotation):
                if self.node_type(child) != ":":
                    return self.get_node_text(child, source_code)
        return None
    
    def _get_class_inheritance(self, node: Node, source_code: str) -> Optional[str]:
        """Extract class inheritance."""
        heritage_clause = self.find_child_by_type(node, "class_heritage")
        if heritage_clause:
            extends_clause = self.find_child_by_type(heritage_clause, "extends_clause")
            if extends_clause:
                # Find the type being extended
                for child in self.node_children(extends_clause):
                    if self.node_type(child) in ["identifier", "type_identifier"]:
                        return self.get_node_text(child, source_code)
        return None
    
    def _get_interface_inheritance(self, node: Node, source_code: str) -> Optional[str]:
        """Extract interface inheritance."""
        heritage_clause = self.find_child_by_type(
            node, ("extends_type_clause", "extends_clause")
        )
        if heritage_clause:
            # Get all extended interfaces
            extended = []
            for child in self.node_children(heritage_clause):
                if self.node_type(child) not in ("extends", ",", "comment"):
                    extended.append(self.get_node_text(child, source_code))
            return ", ".join(extended) if extended else None
        return None
