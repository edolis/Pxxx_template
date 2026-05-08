#!/usr/bin/env python3
import os
import re
import sys
import subprocess
from datetime import datetime

def find_main_cpp():
    """Find the source file that contains 'app_main' (ESP‑IDF entry point)."""
    candidate_extensions = ['.cpp', '.c']
    for root, _, files in os.walk("."):
        for file in files:
            if any(file.endswith(ext) for ext in candidate_extensions):
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'app_main' in content:
                            return full_path
                except:
                    continue
    return None

def read_version_h():
    """Read all FW_* macro values from the generated version.h."""
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
    """Parse main/CMakeLists.txt to extract REQUIRES list."""
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
    components = [c.strip() for c in components if c.strip()]
    return components

def get_submodule_version(submodule_path):
    """Return git describe for a submodule (relative path)."""
    try:
        output = subprocess.check_output(
            ['git', '-C', submodule_path, 'describe', '--tags', '--long', '--dirty', '--always'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return output
    except:
        return "unknown"

def get_submodule_versions(required_components):
    """Return dict {component_name: version} for components that are submodules."""
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
    for comp in required_components:
        if comp in submodule_paths:
            path = submodule_paths[comp]
            if os.path.isdir(path):
                versions[comp] = get_submodule_version(path)
    return versions

def ensure_comment_block(content):
    """If no /** ... */ comment block exists, create a default one and insert at top."""
    if re.search(r'/\*\*.*?\*/', content, re.DOTALL):
        return content
    default_block = """/**
 * @file
 * @brief
 *
 * @author
 * @version
 * @date
 * @submodules-start
 * @submodules-end
 */"""
    return default_block + '\n\n' + content

def update_comment_block(content, version_str):
    """Update @version and @date in the top comment block."""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = content.splitlines()
    new_lines = []
    in_comment = False
    for line in lines:
        if line.strip().startswith('/**'):
            in_comment = True
        if in_comment:
            if '@version' in line:
                indent = line[:line.find('@version')]
                if 'GIT_VERSION:' in line:
                    new_line = indent + '@version GIT_VERSION: ' + version_str
                else:
                    new_line = indent + '@version ' + version_str
                line = new_line
            elif '@date' in line:
                indent = line[:line.find('@date')]
                line = indent + '@date ' + today
        new_lines.append(line)
        if in_comment and line.strip().endswith('*/'):
            in_comment = False
    return '\n'.join(new_lines)

def update_submodule_comment(content, submodule_versions):
    """Replace content between @submodules-start and @submodules-end markers."""
    start_marker = "@submodules-start"
    end_marker = "@submodules-end"
    lines = content.splitlines()
    start_line_idx = -1
    for i, line in enumerate(lines):
        if start_marker in line:
            start_line_idx = i
            break
    if start_line_idx == -1:
        return content
    end_line_idx = -1
    for i in range(start_line_idx + 1, len(lines)):
        if end_marker in lines[i]:
            end_line_idx = i
            break
    if end_line_idx == -1:
        return content
    indent = re.match(r'^(\s*)', lines[start_line_idx]).group(1)
    new_block = []
    new_block.append(lines[start_line_idx])
    if submodule_versions:
        max_len = max(len(name) for name in submodule_versions.keys())
        for name, ver in sorted(submodule_versions.items()):
            new_block.append(f"{indent} *   {name:<{max_len}} : {ver}")
    else:
        new_block.append(f"{indent} *   (none)")
    new_block.append(lines[end_line_idx])
    new_lines = lines[:start_line_idx] + new_block + lines[end_line_idx+1:]
    return '\n'.join(new_lines)

def update_main_file(filepath, values, submodule_versions):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Ensure comment block exists
    content = ensure_comment_block(content)

    # Update version and date
    content = update_comment_block(content, values["GIT_VERSION"])

    # Update submodule list
    content = update_submodule_comment(content, submodule_versions)

    # Update GIT_fwInfo struct (if present)
    for field, new_value in values.items():
        pattern = rf'^(\s*static\s+constexpr\s+const\s+char\s*\*\s+{field}\s*=\s*")[^"]*(";?)'
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    # Write back only if changed
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("INFO: Updated", filepath)

def main():
    main_file = find_main_cpp()
    if not main_file:
        print("ERROR: Could not find a source file containing 'app_main'.")
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