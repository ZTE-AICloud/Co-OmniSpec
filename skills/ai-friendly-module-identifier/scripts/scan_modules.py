#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import argparse
from pathlib import Path


def count_lines(file_path):
    """Count lines in a file, excluding empty lines."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def is_valid_file(file_path):
    """Check if file is valid for analysis."""
    # Skip hidden files
    if file_path.name.startswith('.'):
        return False

    # Skip binary files and large files
    try:
        with open(file_path, 'rb') as f:
            # Check if it's a binary file
            chunk = f.read(1024)
            if b'\x00' in chunk:
                return False
    except Exception:
        return False

    return True


def scan_directory(root_path, max_depth=None):
    """Scan directory and return module structure."""
    root_path = Path(root_path).resolve()
    modules = []

    for dir_path in root_path.rglob('*'):
        # Skip hidden directories
        if any(part.startswith('.') for part in dir_path.parts):
            continue

        # Skip if it's not a directory
        if not dir_path.is_dir():
            continue

        # Check depth limit
        rel_path = dir_path.relative_to(root_path)
        depth = len(rel_path.parts)

        if max_depth and depth > max_depth:
            continue

        # Get files in directory
        files = []
        try:
            for file_path in dir_path.iterdir():
                if file_path.is_file() and is_valid_file(file_path):
                    lines = count_lines(file_path)
                    # Only include files with content
                    if lines > 0:
                        files.append({
                            'name': file_path.name,
                            'lines': lines
                        })
        except PermissionError:
            continue

        # Only include directories with files
        if files:
            modules.append({
                'path': str(rel_path),
                'name': dir_path.name,
                'depth': depth,
                'files': files
            })

    return modules


def main():
    parser = argparse.ArgumentParser(description='Scan project directory for modules')
    parser.add_argument('project_path', help='Project root directory path')
    parser.add_argument('--depth', type=int, help='Maximum scan depth')

    args = parser.parse_args()

    if not os.path.exists(args.project_path):
        print(f"Error: Project path '{args.project_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    modules = scan_directory(args.project_path, args.depth)

    # Output as JSON
    json.dump(modules, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()