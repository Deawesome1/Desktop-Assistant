"""
collect_all_files.py
Recursively collects EVERY file in the entire project tree.

Outputs:
- Prints all file paths to the terminal
- Saves them to: project_files.txt
"""

import os

def collect_files(root):
    file_list = []
    for current_root, dirs, files in os.walk(root):
        for f in files:
            full_path = os.path.join(current_root, f)
            file_list.append(full_path)
    return file_list

def main():
    root = os.path.abspath(os.getcwd())
    print(f"Scanning project root:\n  {root}\n")

    files = collect_files(root)

    print(f"Found {len(files)} files.\n")

    # Print them
    for f in files:
        print(f)

    # Save to file
    output_path = os.path.join(root, "project_files.txt")
    with open(output_path, "w") as out:
        for f in files:
            out.write(f + "\n")

    print(f"\nSaved file list to:\n  {output_path}")

if __name__ == "__main__":
    main()
