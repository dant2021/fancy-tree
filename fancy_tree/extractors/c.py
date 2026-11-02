"""C-specific signature extraction using tree-sitter."""

from .base import SignatureExtractor, node_parent
from tree_sitter import Node
from typing import Optional


class CExtractor(SignatureExtractor):
    """C signature extractor for functions, structs, and enums."""
    
    def extract_function_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract C function signature."""
        name = self.get_symbol_name(node, source_code) or "unknown_function"
        params = self._get_parameters(node, source_code)
        return_type = self._get_return_type(node, source_code)
        
        if return_type:
            return f"{return_type} {name}({params})"
        else:
            return f"{name}({params})"
    
    def extract_class_signature(self, node: Node, source_code: str, template: str) -> str:
        """Extract C struct or enum signature."""
        name = self._get_struct_name(node, source_code)
        
        if self.node_type(node) == "struct_specifier":
            return f"struct {name}"
        elif self.node_type(node) == "union_specifier":
            return f"union {name}"
        elif self.node_type(node) == "enum_specifier":
            return f"enum {name}"
        else:
            return f"type {name}"
    
    def get_symbol_name(
        self, node: Node, source_code: str, name_nodes=None
    ) -> Optional[str]:
        """Name definitions and prototypes; skip type references and variables."""
        if self.node_type(node) in ("struct_specifier", "union_specifier", "enum_specifier"):
            # `struct point p` only references a type; definitions have a body.
            if node.child_by_field_name("body") is None:
                return None
            return super().get_symbol_name(node, source_code, name_nodes)
        if self.node_type(node) not in ("function_definition", "function_declarator"):
            return super().get_symbol_name(node, source_code, name_nodes)
        declarator = self._get_function_declarator(node)
        if declarator is None:
            return None
        # A definition is named by its function_definition node, not its declarator;
        # declarators in parameters or casts are not symbols.
        owner = self._get_owner(declarator)
        if owner is None or (
            self.node_type(node) == "function_declarator"
            and self.node_type(owner) != "declaration"
        ):
            return None
        name = declarator.child_by_field_name("declarator")
        # Function pointers have a parenthesized declarator, not a name.
        if name is not None and self.node_type(name) == "identifier":
            return self.get_node_text(name, source_code)
        return None

    def _get_function_declarator(self, node: Node) -> Optional[Node]:
        """Find the function_declarator under any pointer declarators."""
        if self.node_type(node) == "function_declarator":
            return node
        declarator = node.child_by_field_name("declarator")
        while declarator is not None and self.node_type(declarator) == "pointer_declarator":
            declarator = declarator.child_by_field_name("declarator")
        if declarator is not None and self.node_type(declarator) == "function_declarator":
            return declarator
        return None

    def _get_owner(self, declarator: Node) -> Optional[Node]:
        """Return the definition or prototype declaration a function_declarator belongs to."""
        parent = node_parent(declarator)
        while parent is not None and self.node_type(parent) == "pointer_declarator":
            parent = node_parent(parent)
        if parent is not None and self.node_type(parent) in ("function_definition", "declaration"):
            return parent
        return None
    
    def _get_struct_name(self, node: Node, source_code: str) -> str:
        """Extract struct/enum name."""
        identifier = self.find_child_by_type(node, "type_identifier")
        if identifier:
            return self.get_node_text(identifier, source_code)
        return "anonymous"
    
    def _get_parameters(self, node: Node, source_code: str) -> str:
        """Extract function parameters."""
        declarator = self._get_function_declarator(node)
        if declarator:
            param_list = declarator.child_by_field_name("parameters")
            if param_list:
                params_text = self.get_node_text(param_list, source_code)
                return params_text[1:-1]
        return ""
    
    def _get_return_type(self, node: Node, source_code: str) -> Optional[str]:
        """Extract return type, including pointer declarators such as int *f()."""
        declarator = self._get_function_declarator(node)
        owner = self._get_owner(declarator) if declarator is not None else None
        return_type = owner.child_by_field_name("type") if owner is not None else None
        if return_type is None:
            return None
        # Each declarator in `int *a(void), b(void);` has its own pointer depth.
        pointers = 0
        parent = node_parent(declarator)
        while parent is not None and self.node_type(parent) == "pointer_declarator":
            pointers += 1
            parent = node_parent(parent)
        return self.get_node_text(return_type, source_code) + "*" * pointers
