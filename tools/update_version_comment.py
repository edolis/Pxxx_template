#!/usr/bin/env python3
import os
import re
import sys

def find_main_cpp():
    """Find main.cpp that contains the GIT_fwInfo struct."""
    candidates = ["main/main.cpp", "src/main.cpp", "main.cpp"]
    for rel in candidates:
        if os.path.isfile(rel):
            with open(rel, 'r', encoding='utf-8') as f:
                if 'GIT_fwInfo' in f.read():
                    return rel
    for root, _, files in os.walk("."):
        for f in files:
            if f == "main.cpp":
                full = os.path.join(root, f)
                with open(full, 'r', encoding='utf-8') as fp:
                    if 'GIT_fwInfo' in fp.read():
                        return full
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

def update_main_cpp(filepath, values):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    for field, new_value in values.items():
        # Robust pattern: matches any whitespace between tokens, allows optional 'constexpr'
        pattern = rf'(static\s+constexpr\s+const\s+char\s*\*\s+{field}\s*=\s*")[^"]*(";)'
        replacement = rf'\g<1>{new_value}\g<2>'
        content = re.sub(pattern, replacement, content)

    if content == original:
        print("WARNING: No placeholders replaced. Check the struct formatting.")
        # Show first few lines around the struct for debugging
        lines = original.splitlines()
        for i, line in enumerate(lines):
            if "GIT_fwInfo" in line:
                for j in range(i, min(i+10, len(lines))):
                    print("  " + lines[j])
                break
    else:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("INFO: Updated placeholders in", filepath)
        for field, val in values.items():
            print(f"  {field} = {val}")

def main():
    main_cpp = find_main_cpp()
    if not main_cpp:
        print("ERROR: Could not find main.cpp containing GIT_fwInfo.")
        sys.exit(1)
    print("Found main.cpp:", main_cpp)

    values = read_version_h()
    print("Read values from version.h:", values)

    update_main_cpp(main_cpp, values)

if __name__ == "__main__":
    main()