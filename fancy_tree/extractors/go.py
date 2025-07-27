"""Go‑specific signature extraction using tree‑sitter."""

from __future__ import annotations

from tree_sitter import Node
from .base import SignatureExtractor
from typing import Optional


class GoExtractor(SignatureExtractor):
    """Go signature extractor with support for free functions, methods and type decls."""

    # —————————————————— public API —————————————————— #

    def extract_function_signature(
        self, node: Node, source_code: str, template: str
    ) -> str:
        """Extract Go func / method signature with receiver and return type(s)."""
        recv      = self._get_receiver(node, source_code)
        name      = self._get_function_name(node, source_code)
        params    = self._get_parameters(node, source_code)
        ret_types = self._get_return_type(node, source_code)

        if recv:          # → Method
            return f"func ({recv}) {name}({params}) {ret_types}".rstrip()
        else:             # → Free function
            return f"func {name}({params}) {ret_types}".rstrip()

    def extract_class_signature(
        self, node: Node, source_code: str, template: str
    ) -> str:
        """
        Extract Go 'type' declarations.
        We treat structs and interfaces like classes for consistency.
        """
        spec = self.find_child_by_type(node, "type_spec")
        if not spec:
            return "type <unknown>"

        ident = self.find_child_by_type(spec, "type_identifier")
        name  = self.get_node_text(ident, source_code)

        body  = self.find_child_by_type(spec, ("struct_type", "interface_type"))
        kind  = "struct" if body and body.type == "struct_type" else "interface"

        return f"type {name} {kind}"

    # —————————————————— helpers —————————————————— #

    def _get_function_name(self, node: Node, src: str) -> str:
        ident = self.find_child_by_type(node, "identifier")
        return self.get_node_text(ident, src) if ident else "unknown_func"

    def _get_receiver(self, node: Node, src: str) -> Optional[str]:
        recv = node.child_by_field_name("receiver")
        if not recv:
            return None
        # receiver block looks like: ( parameter_list )
        # We keep it verbatim but drop the surrounding parens later
        param = self.find_child_by_type(recv, "parameter_declaration")
        return self.get_node_text(param, src).strip() if param else None

    def _get_parameters(self, node: Node, src: str) -> str:
        params = node.child_by_field_name("parameters")
        text   = self.get_node_text(params, src).strip("()") if params else ""
        return text

    def _get_return_type(self, node: Node, src: str) -> str:
        """
        Go allows either:
            func f() int
            func f() (int, error)
        Tree‑sitter labels both as 'result'.
        """
        result = node.child_by_field_name("result")
        if not result:
            return ""
        # Strip extra whitespace; keep enclosing () if grammar emitted them.
        return self.get_node_text(result, src).strip()
