# fancy-tree 🌳

A git-aware `tree` command that looks inside your files and shows functions, classes, and structure.

```bash
pip install fancy-tree
fancy-tree my-project/
```

## What It Does

It's the `tree` command, but now it can:
- Respect `.gitignore` files  
- Show functions and classes inside files
- Super easy to extend to most languages through tree-sitter 

## Quick Start

```bash
# Scan current directory
fancy-tree .

# Scan specific project  
fancy-tree /path/to/your/project

# Filter by languages
fancy-tree . --lang python javascript

# Limit files (for large repos)
fancy-tree . --max-files 50
```

## Sample Output
```
Repository: my-awesome-app
Total files: 42, Total lines: 3,847

PYTHON Files (15 files, SUPPORTED):
[FILE] user_service.py (python, 156 lines)
  class UserService:
    def create_user(self, name: str, email: str) -> User 
    def delete_user(self, user_id: int) -> bool 
    def validate_email(email: str) -> bool 

TYPESCRIPT Files (8 files, SUPPORTED):
[FILE] Button.tsx (typescript, 89 lines)
interface ButtonProps 
function Button(props: ButtonProps): JSX.Element
```
## Contributing

This project is **work in progress** and we'd love your help! Adding language support is surprisingly easy:

Run the regression suite with `python -m pip install -e . pytest` followed by
`python -m pytest -q`. CI covers Python 3.9 with the reported parser versions
(`tree-sitter==0.23.2`, `tree-sitter-language-pack==0.9.1`) and Python 3.12 with
the latest dependencies.

### Add a New Language
1. **Add to `config/languages.yaml`**:
   ```yaml
   your_language:
     extensions: [".ext"]
     function_nodes: ["function_declaration"]
     class_nodes: ["class_declaration"]
   ```

2. **Create extractor** in `extractors/your_language.py`:
   ```python
   class YourLanguageExtractor(SignatureExtractor):
       def extract_function_signature(self, node, source_code, template):
           return "your_function(params)"
   ```

3. **Test it**: `fancy-tree scan your-test-files/`

## Language Support

**Good**: Python, TypeScript, Java, Go  
**Basic**: JavaScript, Rust, Php, Ruby, C++, C, Csharp  
**Minimal**: 160+ more languages

*Want better support for your language? Contribute an extractor!*

TypeScript files use the TypeScript grammar for `.ts` and the TSX grammar for
`.tsx`; both are displayed as `typescript`. Extraction includes named functions,
classes, methods, interfaces, and arrows assigned to variables, static object
properties, or class fields. Anonymous callbacks and computed property arrows
are omitted, but named declarations inside them are still visited. General
exported constants (including Storybook story objects) and type aliases are not
currently listed.

Recognized source files always show their language and line count, even when
they contain no supported symbols. Syntax errors produce a warning alongside
any recovered symbols; parser, read, and extraction failures also appear as
per-file warnings. The language support summary reports parser availability,
not whether every file parsed successfully.

JSON output (`--json`) includes each file's `parser_language`, `extraction_status`,
and `diagnostics` (code, message, and optional line). Status is `success` for a
clean extraction, `recovered` for a tree with syntax errors, `parser_unavailable`
for a missing parser, `failed` for read/parse/extraction failures, or
`not_attempted` for unclassified/unsupported files. A successful extraction can
have an empty symbol list. Files that are not valid UTF-8 are still extracted,
with undecodable bytes replaced and a `decode_replaced` diagnostic. Progress goes
to stderr, so stdout is valid JSON; `--quiet` suppresses progress while
preserving diagnostics in the output and errors on stderr.
Quiet, JSON, and non-interactive scans report missing parsers without prompting
to install packages.

For Python callers, `extract_symbols_generic` and `extract_symbols_from_file`
still return symbol lists. Pass `file_path=Path("Component.tsx")` to the generic
helper to select TSX. Use `extract_symbols_with_diagnostics` or
`extract_file_with_diagnostics` from `fancy_tree.core` for structured results.

## Installation

```bash
# Standard installation
pip install fancy-tree

# Development version
git clone https://github.com/dant2021/fancy-tree.git
cd fancy-tree
pip install -e .
```

## FAQ

**Q: Why not just use `tree`?**  
A: `tree` shows files, we show what's *inside* the files.

## Thanks

Built by [@AntoineDescamps](https://github.com/dant2021) and [@IshanTiwari](https://github.com/IshanTiwari0112)

Powered by [tree-sitter](https://tree-sitter.github.io/) and [tree-sitter-language-pack](https://github.com/Goldziher/tree-sitter-language-pack)
