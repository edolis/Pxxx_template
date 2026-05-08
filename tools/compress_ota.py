#!/usr/bin/env python3
import os
import re
import sys
import subprocess
import shutil

def get_version_from_header(version_h_path):
    """Read FW_GIT_VERSION from version.h."""
    if not os.path.isfile(version_h_path):
        return None
    with open(version_h_path, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^#define\s+FW_GIT_VERSION\s+"(.*)"', line)
            if m:
                return m.group(1)
    return None

def main():
    if len(sys.argv) < 4:
        print("Usage: compress_ota.py <project_name> <firmware_bin> <shared_folder>")
        sys.exit(1)

    project_name = sys.argv[1]
    fw_bin = sys.argv[2]
    shared_folder = sys.argv[3]

    # Find version.h
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    version_h = os.path.join(project_root, "build", "main", "version.h")

    version = get_version_from_header(version_h)
    if not version:
        print("WARNING: Could not read version from version.h, using default")
        version = "v0.0.0-0"

    # Sanitize version for filename
    safe_version = re.sub(r'[/\\]', '_', version)
    compressed_fw = f"{project_name}_{safe_version}.bin.lz4"

    # Find lz4
    lz4_path = shutil.which("lz4")
    if not lz4_path:
        print("ERROR: lz4 not found in PATH")
        sys.exit(1)

    # Compress
    cmd = [lz4_path, "-9", "--no-frame-crc", "-f", fw_bin, compressed_fw]
    print(f"Compressing: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    # Copy to shared folder using shutil.copy2 (works on Windows and Unix)
    dest_path = os.path.join(shared_folder, compressed_fw)
    print(f"Copying {compressed_fw} to {dest_path}")
    try:
        shutil.copy2(compressed_fw, dest_path)
        print("Copy successful.")
    except Exception as e:
        print(f"ERROR copying file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()