import pytest

from fancy_tree.core import extraction
from fancy_tree.schema import ExtractionStatus, SymbolType


def symbols(source, language):
    result = extraction.extract_symbols_with_diagnostics(source, language)
    assert result.status == ExtractionStatus.SUCCESS, result.diagnostics
    return [(symbol.name, symbol.type, symbol.signature) for symbol in result.symbols]


def test_go_methods_keep_their_names_in_signatures():
    assert symbols("package p\nfunc (r *R) Meth(x int) error { return nil }\nfunc Free() {}", "go") == [
        ("Meth", SymbolType.FUNCTION, "func (r *R) Meth(x int) error"),
        ("Free", SymbolType.FUNCTION, "func Free()"),
    ]


@pytest.mark.parametrize(
    "source, name, signature",
    [
        ("const f = x => x;", "f", "f = (x) => {}"),
        ("const g = (a) => a;", "g", "g = (a) => {}"),
        ("const o = { h: () => 1 };", "h", "h = () => {}"),
    ],
)
def test_javascript_arrows_are_named_by_their_binding(source, name, signature):
    assert symbols(source, "javascript") == [(name, SymbolType.FUNCTION, signature)]


def test_javascript_callbacks_and_class_fields():
    source = "items.map(x => x); class A { p = () => 1; m() {} }"
    result = extraction.extract_symbols_with_diagnostics(source, "javascript")
    (cls,) = result.symbols
    assert [(m.name, m.type) for m in cls.children] == [
        ("p", SymbolType.METHOD),
        ("m", SymbolType.METHOD),
    ]


def test_c_definitions_and_prototypes_keep_types_and_parameters():
    source = (
        "int add(int a, int b) { int x = 1; return a + b; }\n"
        "static char *name(void);\n"
        "int proto(int);\n"
        "int (*callback)(int);\n"
        "int counter = 0;\n"
    )
    assert symbols(source, "c") == [
        ("add", SymbolType.FUNCTION, "int add(int a, int b)"),
        ("name", SymbolType.FUNCTION, "char* name(void)"),
        ("proto", SymbolType.FUNCTION, "int proto(int)"),
    ]
