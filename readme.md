# fancy-tree 🌳

A git-aware `tree` command that looks inside your files and shows functions, classes, and structure.

```bash
pip install fancy-tree
fancy-tree scan my-project/
```

## What It Does

It's the `tree` command, but now it can:
- Respect `.gitignore` files  
- Show functions and classes inside files
- Super easy to extend to most languages through tree-sitter 

## Quick Start

```bash
# Scan current directory
fancy-tree scan .

# Scan specific project  
fancy-tree scan /path/to/your/project

# Filter by languages
fancy-tree scan . --lang python javascript

# Limit files (for large repos)
fancy-tree scan . --max-files 50
```

## Sample Output
```
Repository: my-awesome-app
Total files: 42, Total lines: 3,847

PYTHON Files (15 files, SUPPORTED):
[FILE] user_service.py (python, 156 lines)
  class UserService:
    def create_user(self, name: str, email: str) -> User # line 23
    def delete_user(self, user_id: int) -> bool # line 45
    def validate_email(email: str) -> bool # line 67

TYPESCRIPT Files (8 files, SUPPORTED):
[FILE] Button.tsx (typescript, 89 lines)
interface ButtonProps # line 5
function Button(props: ButtonProps): JSX.Element # line 12
```
## Contributing

This project is **work in progress** and we'd love your help! Adding language support is surprisingly easy:

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
