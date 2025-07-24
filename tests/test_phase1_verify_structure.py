"""Verify Phase 1 structure is complete."""

from pathlib import Path

def verify_structure():
    """Check that all Phase 1 files and directories exist."""
    base = Path(".")
    
    required_files = [
        "__init__.py",
        "schema.py", 
        "main.py",
        "pyproject.toml",
        "requirements.txt",
        ".gitignore",
        "core/__init__.py",
        "extractors/__init__.py",
        "extractors/base.py", 
        "config/__init__.py",
        "config/languages.yaml"
    ]
    
    print("🔍 Verifying Phase 1 Structure...")
    all_good = True
    
    for file_path in required_files:
        full_path = base / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            all_good = False
    
    if all_good:
        print("\n🎉 Phase 1 structure complete!")
        print("📋 Next: Implement Phase 2 (Core Framework)")
    else:
        print("\n⚠️ Some files are missing. Please create them.")

if __name__ == "__main__":
    verify_structure()