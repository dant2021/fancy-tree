from pathlib import Path

import pytest

from fancy_tree.core import extraction
from fancy_tree.core.config import detect_language
from fancy_tree.schema import ExtractionStatus, SymbolType


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "filenames", [("Widget.tsx", "types.ts"), ("types.ts", "Widget.tsx")]
)
def test_dialects_use_independent_parsers_in_either_order(filenames):
    extraction._parser_cache.clear()
    results = {}
    for filename in filenames:
        path = FIXTURES / filename
        assert detect_language(path) == "typescript"
        results[filename] = extraction.process_file(path, "typescript")

    component = results["Widget.tsx"]
    assert component.parser_language == "tsx"
    assert component.language == "typescript"
    assert component.extraction_status == ExtractionStatus.SUCCESS
    assert component.diagnostics == []
    assert [symbol.name for symbol in component.symbols] == [
        "Props",
        "Widget",
        "ArrowWidget",
    ]
    assert component.symbols[1].signature == "function Widget(props: Props)"
    assert component.symbols[2].signature == "function ArrowWidget({ name }: Props)"

    types = results["types.ts"]
    assert types.parser_language == "typescript"
    assert types.extraction_status == ExtractionStatus.SUCCESS
    assert types.diagnostics == []
    assert types.symbols[0].name == "identity"
    assert types.symbols[0].signature == "function identity(value: T): T"


def test_legacy_file_and_source_helpers_keep_returning_symbol_lists():
    path = FIXTURES / "Widget.tsx"
    symbols = extraction.extract_symbols_from_file(path, "typescript")
    generic = extraction.extract_symbols_generic(
        path.read_text(), "typescript", file_path=Path("Widget.TSX")
    )
    assert [symbol.to_dict() for symbol in symbols] == [
        symbol.to_dict() for symbol in generic
    ]
    assert [symbol.name for symbol in symbols] == ["Props", "Widget", "ArrowWidget"]


@pytest.mark.parametrize(
    "source,name,signature",
    [
        ("export const Widget = () => 1;", "Widget", "function Widget()"),
        (
            "export const double = value => value * 2;",
            "double",
            "function double(value)",
        ),
        ("const double = (value) => value * 2;", "double", "function double(value)"),
        (
            "const double = (value: number): number => value * 2;",
            "double",
            "function double(value: number): number",
        ),
        (
            "const run = (fn: () => void) => fn();",
            "run",
            "function run(fn: () => void)",
        ),
        ("const obj = { render: value => value };", "render", "function render(value)"),
        ('const obj = { "render": () => 1 };', '"render"', 'function "render"()'),
        (
            "const wrapped = ((value: number) => value) satisfies Callback;",
            "wrapped",
            "function wrapped(value: number)",
        ),
        (
            "const wrapped = ((value: number) => value) as Callback;",
            "wrapped",
            "function wrapped(value: number)",
        ),
        ("export function Widget() { return 1; }", "Widget", "function Widget()"),
        (
            "// café ☕\nexport const doublé = valeur => valeur * 2;",
            "doublé",
            "function doublé(valeur)",
        ),
    ],
)
def test_function_identity_matches_signature(source, name, signature):
    result = extraction.extract_symbols_with_diagnostics(source, "typescript")
    assert result.status == ExtractionStatus.SUCCESS
    assert result.diagnostics == []
    assert len(result.symbols) == 1
    symbol = result.symbols[0]
    assert symbol.name == name
    assert symbol.signature == signature
    assert symbol.type == SymbolType.FUNCTION


def test_named_arrows_preserve_nested_functions():
    source = """export const outer = () => {
  function inner() { return 1; }
  return inner();
};"""
    result = extraction.extract_symbols_with_diagnostics(source, "typescript")
    assert result.status == ExtractionStatus.SUCCESS
    (outer,) = result.symbols
    (inner,) = outer.children
    assert (outer.name, outer.signature, outer.line) == ("outer", "function outer()", 1)
    assert (inner.name, inner.signature, inner.line) == ("inner", "function inner()", 2)


@pytest.mark.parametrize(
    "source",
    [
        "items.map(() => { function inner() {} return inner(); });",
        "items.map(value => { function inner() {} return inner(); });",
        "items.map(value => inner); function inner() {}",
        "const obj = { [key]: value => { function inner() {} } };",
        "const wrapped = memo(value => { function inner() {} });",
    ],
)
def test_anonymous_arrows_never_borrow_names_and_do_not_hide_descendants(source):
    result = extraction.extract_symbols_with_diagnostics(source, "typescript")
    assert result.status == ExtractionStatus.SUCCESS
    assert [(symbol.name, symbol.signature) for symbol in result.symbols] == [
        ("inner", "function inner()")
    ]


@pytest.mark.parametrize(
    "heritage", ["", " extends Base", " extends Base<string>, Other"]
)
def test_interfaces_include_inheritance_and_methods(heritage):
    result = extraction.extract_symbols_with_diagnostics(
        f"export interface Props{heritage} {{ name: string; render(value: string): void; }}",
        "typescript",
    )
    assert result.status == ExtractionStatus.SUCCESS
    (interface,) = result.symbols
    assert interface.type == SymbolType.INTERFACE
    assert interface.name == "Props"
    assert interface.signature == f"interface Props{heritage}"
    (method,) = interface.children
    assert (method.name, method.type, method.signature) == (
        "render",
        SymbolType.METHOD,
        "render(value: string): void",
    )


def test_class_methods_and_field_arrows_keep_their_names():
    result = extraction.extract_symbols_with_diagnostics(
        "export class Widget { render() { function inner() {} return 1; } callback = value => value; }",
        "typescript",
    )
    assert result.status == ExtractionStatus.SUCCESS
    (cls,) = result.symbols
    assert (cls.name, cls.type) == ("Widget", SymbolType.CLASS)
    render, callback = cls.children
    assert (render.name, render.type, render.signature) == (
        "render",
        SymbolType.METHOD,
        "render()",
    )
    assert (callback.name, callback.type) == ("callback", SymbolType.METHOD)
    (inner,) = render.children
    assert (inner.name, inner.type) == ("inner", SymbolType.FUNCTION)


def test_python_class_and_nested_function_still_extract():
    source = """class Greeter:
    def hello(self, name: str) -> str:
        def inner():
            return name
        return inner()
"""
    result = extraction.extract_symbols_with_diagnostics(source, "python")
    assert result.status == ExtractionStatus.SUCCESS
    (cls,) = result.symbols
    (method,) = cls.children
    (inner,) = method.children
    assert (cls.name, cls.type) == ("Greeter", SymbolType.CLASS)
    assert (method.name, method.type) == ("hello", SymbolType.METHOD)
    assert "name: str" in method.signature
    assert (inner.name, inner.type) == ("inner", SymbolType.FUNCTION)


def test_object_type_literal_members_are_not_functions():
    result = extraction.extract_symbols_with_diagnostics(
        "type T = { m(): void }; interface I { n(): void; p: { q(): void } }",
        "typescript",
    )
    (interface,) = result.symbols
    assert interface.name == "I"
    assert [child.name for child in interface.children] == ["n"]


def test_abstract_classes_keep_abstract_and_concrete_members():
    result = extraction.extract_symbols_with_diagnostics(
        "export abstract class B { abstract a(): void; b() {} }", "typescript"
    )
    (cls,) = result.symbols
    assert (cls.name, cls.type, cls.signature) == (
        "B",
        SymbolType.CLASS,
        "abstract class B",
    )
    assert [(m.name, m.type, m.signature) for m in cls.children] == [
        ("a", SymbolType.METHOD, "a(): void"),
        ("b", SymbolType.METHOD, "b()"),
    ]


def test_class_field_arrows_use_method_signatures():
    result = extraction.extract_symbols_with_diagnostics(
        "class A { #p = () => 1; static s = (x: number): string => '' }",
        "typescript",
    )
    (cls,) = result.symbols
    assert [(m.name, m.type, m.signature) for m in cls.children] == [
        ("#p", SymbolType.METHOD, "#p()"),
        ("s", SymbolType.METHOD, "s(x: number): string"),
    ]
