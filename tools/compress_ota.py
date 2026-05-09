#!/usr/bin/env python3
import os
import re
import sys
import lz4.block   # requires lz4 library installed

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

    # --- version handling (same as before) ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    version_h = os.path.join(project_root, "build", "main", "version.h")
    version = get_version_from_header(version_h)
    if not version:
        print("WARNING: Could not read version from version.h, using default v0.0.0-0")
        version = "v0.0.0-0"

    safe_version = re.sub(r'[/\\]', '_', version)
    compressed_fw = f"{project_name}_{safe_version}.bin.lz4"

    # --- compression parameters (must match ESP expectations) ---
    CHUNK_SIZE = 4096            # 4 KB
    DICT_SIZE = 16 * 1024        # 16 KB rolling dictionary

    dest_path = os.path.join(shared_folder, compressed_fw)
    print(f"Compressing {fw_bin} -> {dest_path} (raw LZ4 with dictionary)")

    total_chunks = 0
    total_original = 0
    total_compressed = 0
    history = b""                # rolling dictionary buffer

    try:
        with open(fw_bin, "rb") as f_in, open(dest_path, "wb") as f_out:
            while True:
                chunk = f_in.read(CHUNK_SIZE)
                if not chunk:
                    break

                # Compress using dictionary (store_size=False -> no internal size header)
                compressed_chunk = lz4.block.compress(
                    chunk,
                    mode='high_compression',
                    store_size=False,
                    compression=9,
                    dict=history
                )

                total_chunks += 1
                total_original += len(chunk)
                total_compressed += len(compressed_chunk)

                # Write 4‑byte little‑endian size header, then data
                f_out.write(len(compressed_chunk).to_bytes(4, byteorder='little'))
                f_out.write(compressed_chunk)

                # Update rolling dictionary (keep last DICT_SIZE bytes of input)
                history = (history + chunk)[-DICT_SIZE:]

        print(f"✅ Compressed successfully: {dest_path}")
        print(f"   Chunks: {total_chunks}, Original: {total_original} B, Compressed: {total_compressed} B "
              f"({total_compressed/total_original:.2%})")

    except Exception as e:
        print(f"❌ Compression failed: {e}")
        sys.exit(1)

    print("Done.")

if __name__ == "__main__":
    main()