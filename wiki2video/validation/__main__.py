#!/usr/bin/env python3
"""
Main entry point for the validation module.

This allows running the validation system with:
    python -m videogen.validation
"""

try:
    from .base_validator import main
except ImportError:
    from base_validator import main

if __name__ == "__main__":
    main()
