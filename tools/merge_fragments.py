import os
import sys
import json
import hashlib

print("=" * 60)
print("MERGE_FRAGMENTS.PY IS RUNNING")
print("=" * 60)

# -------------------------------------------------------------
# Find project root
# -------------------------------------------------------------
def find_project_root(start_path):
    path = os.path.abspath(start_path)
    while True:
        if os.path.exists(os.path.join(path, "CMakeLists.txt")) or \
           os.path.exists(os.path.join(path, ".vscode")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return start_path
        path = parent

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = find_project_root(SCRIPT_DIR)

FRAGMENTS_DIR = os.path.join(PROJECT_ROOT, "sdkconfig_fragments")
PROFILES_DIR = os.path.join(PROJECT_ROOT, "profiles")
OUTPUT = os.path.join(PROJECT_ROOT, "sdkconfig.defaults")
VSCODE_SETTINGS = os.path.join(PROJECT_ROOT, ".vscode", "settings.json")
SDKCONFIG_PATH = os.path.join(PROJECT_ROOT, "sdkconfig")

# -------------------------------------------------------------
def compute_hash(content_lines):
    content_str = "".join(content_lines).encode("utf-8")
    return hashlib.md5(content_str).hexdigest()

def get_existing_hash():
    if not os.path.exists(OUTPUT):
        return None
    with open(OUTPUT, "r") as f:
        existing_content = f.readlines()
    return compute_hash(existing_content)

# -------------------------------------------------------------
def get_active_profile():
    env_profile = os.environ.get("ESP_IDF_ACTIVE_PROFILE")
    if env_profile:
        print(f"Using profile from environment: {env_profile}")
        return env_profile
    if os.path.exists(VSCODE_SETTINGS):
        try:
            with open(VSCODE_SETTINGS, "r") as f:
                settings = json.load(f)
            profile = settings.get("idf.activeProfile")
            if profile:
                return profile
        except Exception as e:
            print(f"Warning: could not read {VSCODE_SETTINGS}: {e}")
    print("No active profile found. Using 'debug' as default.")
    return "debug"

def get_profile_target(profile_name):
    config_path = os.path.join(PROJECT_ROOT, "esp_idf_project_configuration.json")
    if not os.path.exists(config_path):
        return None
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        profile_cfg = config.get(profile_name, {})
        return profile_cfg.get("idfTarget")
    except Exception as e:
        print(f"Warning: could not read {config_path}: {e}")
        return None

# -------------------------------------------------------------
def main():
    active_profile = get_active_profile()
    profile_file = os.path.join(PROFILES_DIR, f"{active_profile}.conf")
    if not os.path.exists(profile_file):
        print(f"Error: profile file '{profile_file}' not found.")
        sys.exit(1)

    with open(profile_file, "r") as f:
        fragment_names = [
            line.strip() for line in f
            if line.strip() and not line.startswith("#")
        ]

    target = get_profile_target(active_profile)
    if target:
        target_frag = f"target_{target}.conf"
        if os.path.exists(os.path.join(FRAGMENTS_DIR, target_frag)):
            fragment_names.append(target_frag)
            print(f"Auto-included target fragment: {target_frag}")

    # Build new content from fragments
    new_content = []
    for fname in fragment_names:
        frag_path = os.path.join(FRAGMENTS_DIR, fname)
        if os.path.exists(frag_path):
            with open(frag_path, "r") as frag:
                new_content.extend(frag.readlines())
                new_content.append("\n")
        else:
            print(f"Warning: fragment '{fname}' not found in {FRAGMENTS_DIR}")

    # Compare with existing sdkconfig.defaults (if any)
    old_hash = get_existing_hash()
    new_hash = compute_hash(new_content)

    if old_hash == new_hash:
        print("No change in effective configuration. Nothing to do.")
        return

    # Write new sdkconfig.defaults
    with open(OUTPUT, "w") as out:
        out.writelines(new_content)
    print(f"Generated {OUTPUT} using profile '{active_profile}' with {len(fragment_names)} fragments.")

    # Delete sdkconfig to force full reconfiguration
    if os.path.exists(SDKCONFIG_PATH):
        try:
            os.remove(SDKCONFIG_PATH)
            print(f"Deleted {SDKCONFIG_PATH} because configuration changed.")
        except Exception as e:
            print(f"Warning: could not delete {SDKCONFIG_PATH}: {e}")
    else:
        print(f"No existing sdkconfig found at {SDKCONFIG_PATH}")

if __name__ == "__main__":
    main()