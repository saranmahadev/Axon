"""
Script to rename all references from AxonML to Axon
"""

import os
from pathlib import Path

# Files to update
FILES_TO_UPDATE = [
    "README.md",
    "CHANGELOG.md",
    "mkdocs.yml",
    "docs/index.md",
    "docs/getting-started/installation.md",
    "docs/getting-started/quickstart.md",
    "docs/getting-started/configuration.md",
    "docs/concepts/overview.md",
    "docs/api/memory-system.md",
]

def replace_in_file(file_path: Path):
    """Replace AxonML with Axon in a file."""
    if not file_path.exists():
        print(f"Skipping {file_path} (not found)")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Count replacements
    count_axonml = content.count('AxonML')
    count_axonml_lower = content.count('axonml')

    # Replace
    content = content.replace('AxonML', 'Axon')
    content = content.replace('axonml', 'axon')

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    total = count_axonml + count_axonml_lower
    if total > 0:
        print(f"Updated {file_path}: {total} replacements")

def main():
    """Main function."""
    root = Path(".")

    for file_path in FILES_TO_UPDATE:
        replace_in_file(root / file_path)

    print("\nDone! All references updated from AxonML -> Axon")

if __name__ == "__main__":
    main()
