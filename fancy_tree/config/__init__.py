"""Configuration management for fancy_tree."""

from pathlib import Path

# Path to the languages configuration
LANGUAGES_CONFIG_PATH = Path(__file__).parent / "languages.yaml"

__all__ = ["LANGUAGES_CONFIG_PATH"]