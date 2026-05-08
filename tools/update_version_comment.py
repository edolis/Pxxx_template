#!/usr/bin/env python3
import os
import re
import sys
import subprocess
from datetime import datetime

def get_git_author():
    """Retrieve Git user name and email, or fallback."""
    try:
        name = subprocess.check_output(['git', 'config', 'user.name'], stderr=subprocess.DEVNULL).decode().strip()
        email = subprocess.check_output(['git', 'config', 'user.email'], stderr=subprocess.DEVNULL).decode().strip()
        if name and email:
            return f"{name} ({email})"
        elif name:
            return name
    except:
        pass
    # Fallback to environment or default
    name = os.environ.get('GIT_AUTHOR_NAME', 'Unknown')
    email = os.environ.get('GIT_AUTHOR_EMAIL', '')
    if email:
        return f"{name} ({email})"
    return name

def find_main_cpp():
    """Find source file containing 'app_main' (ESP‑IDF entry point)."""
    common = ["main/main.cpp", "main/main.c", "src/main.cpp", "src/main.c", "main.cpp", "main.c"]
    for path in common:
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                if 'app_main' in f.read():
                    return path
    for root, _, files in os.walk("."):
        if root.startswith((".\\components", "components")):
            continue
        for file in files:
            if file.endswith(('.cpp', '.c')):
                full = os.path.join(root, file)
                try:
                    with open(full, 'r', encoding='utf-8') as f:
                        if 'app_main' in f.read():
                            return full
                except:
                    continue
    return None

def read_version_h():
    version_h = os.path.join("build", "main", "version.h")
    if not os.path.isfile(version_h):
        for root, _, files in os.walk("build"):
            if "version.h" in files and "main" in root:
                version_h = os.path.join(root, "version.h")
                break
    if not os.path.isfile(version_h):
        print("ERROR: version.h not found. Run 'idf.py reconfigure' first.")
        sys.exit(1)
    macros = {}
    with open(version_h, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^#define\s+FW_(\w+)\s+"(.*)"', line)
            if m:
                macros[m.group(1)] = m.group(2)
    return {
        "GIT_VERSION": macros.get("GIT_VERSION", "v0.0.0-0"),
        "GIT_TAG":     macros.get("GIT_TAG", "untagged"),
        "GIT_HASH":    macros.get("GIT_HASH", "g0000000"),
        "FULL_HASH":   macros.get("FULL_HASH", "0"*40),
        "BUILD_ID":    macros.get("BUILD_ID", "P00000000-000000-0000000")
    }

def get_required_components():
    cmake_file = "main/CMakeLists.txt"
    if not os.path.isfile(cmake_file):
        return []
    with open(cmake_file, 'r', encoding='utf-8') as f:
        content = f.read()
    matches = re.findall(r'REQUIRES\s+([^\n]+)', content)
    if not matches:
        return []
    req_line = matches[0]
    req_line = re.sub(r'\\\s*\n', ' ', req_line)
    components = req_line.split()
    return [c.strip() for c in components if c.strip()]

def get_submodule_version(path):
    try:
        out = subprocess.check_output(
            ['git', '-C', path, 'describe', '--tags', '--long', '--dirty', '--always'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return out
    except:
        return "unknown"

def get_submodule_versions(required):
    if not os.path.isfile('.gitmodules'):
        return {}
    submodule_paths = {}
    with open('.gitmodules', 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'\s*path\s*=\s*(.+)', line)
            if m:
                path = m.group(1).strip()
                name = os.path.basename(path)
                submodule_paths[name] = path
    versions = {}
    for comp in required:
        if comp in submodule_paths:
            p = submodule_paths[comp]
            if os.path.isdir(p):
                versions[comp] = get_submodule_version(p)
    return versions

def extract_file_and_brief(content):
    """Extract @file and @brief lines from existing comment block (if any)."""
    file_line = ""
    brief_line = ""
    comment_match = re.search(r'/\*\*.*?\*/', content, re.DOTALL)
    if comment_match:
        comment = comment_match.group(0)
        lines = comment.splitlines()
        for line in lines:
            if '@file' in line:
                file_line = line.strip()
            elif '@brief' in line:
                brief_line = line.strip()
                break  # assume brief is after file and before other tags
    return file_line, brief_line

def rebuild_comment_block(values, submodule_versions, existing_file, existing_brief):
    """Build a clean comment block with fixed order."""
    today = datetime.now().strftime("%Y-%m-%d")
    version_str = values["GIT_VERSION"]
    author = get_git_author()

    # Use existing @file and @brief if present, else defaults
    if not existing_file:
        existing_file = " * @file "
    if not existing_brief:
        existing_brief = " * @brief "

    # Construct block
    lines = []
    lines.append("/**")
    lines.append(existing_file)
    lines.append(existing_brief)
    lines.append(" *")
    lines.append(f" * @author {author}")
    lines.append(f" * @version GIT_VERSION: {version_str}")
    lines.append(f" * @date {today}")
    lines.append(" * @submodules-start")
    if submodule_versions:
        max_len = max(len(name) for name in submodule_versions.keys())
        for name, ver in sorted(submodule_versions.items()):
            lines.append(f" *   {name:<{max_len}} : {ver}")
    else:
        lines.append(" *   (none)")
    lines.append(" * @submodules-end")
    lines.append(" */")
    return '\n'.join(lines)

def update_main_file(filepath, values, submodule_versions):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract existing @file and @brief
    file_line, brief_line = extract_file_and_brief(content)

    # Build a completely new comment block
    new_comment = rebuild_comment_block(values, submodule_versions, file_line, brief_line)

    # Replace the old comment block (the first /** ... */) with the new one
    content = re.sub(r'/\*\*.*?\*/', new_comment, content, flags=re.DOTALL, count=1)

    # Update GIT_fwInfo struct
    for field, new_value in values.items():
        pattern = rf'^(\s*static\s+constexpr\s+const\s+char\s*\*\s+{field}\s*=\s*")[^"]*(";?)'
        replacement = rf'\g<1>{new_value}\g<2>'
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("INFO: Updated", filepath)

def main():
    main_file = find_main_cpp()
    if not main_file:
        print("ERROR: Could not find source file containing 'app_main'.")
        sys.exit(1)
    print("Found main source file:", main_file)

    values = read_version_h()
    print("Read values from version.h:", values)

    req_components = get_required_components()
    print("Required components:", req_components)

    submodule_versions = get_submodule_versions(req_components)
    if submodule_versions:
        print("Submodule versions:", submodule_versions)

    update_main_file(main_file, values, submodule_versions)

if __name__ == "__main__":
    main()