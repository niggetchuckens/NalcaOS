#!/usr/bin/env python3
"""
Antigravity CLI - Python Bootstrapper Script (Linux Only)

Downloads, staging-verifies, and installs the Antigravity CLI flat native build.
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from urllib.error import URLError, HTTPError

DOWNLOAD_BASE_URL = "https://antigravity-cli-auto-updater-974169037036.us-central1.run.app"
DEFAULT_TARGET_DIR = os.path.expanduser("~/.local/bin")
STAGING_DIR = os.path.expanduser("~/.cache/antigravity/staging")

def print_err(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def main():
    parser = argparse.ArgumentParser(
        description="Antigravity CLI Bootstrapper Script (Linux)",
        add_help=False
    )
    parser.add_argument("-d", "--dir", dest="custom_dir", help="Specify a custom directory to install the binary")
    parser.add_argument("-h", "--help", action="store_true", help="Display this help menu")
    
    args, unknown = parser.parse_known_args()
    
    if args.help:
        parser.print_help()
        sys.exit(0)
        
    if unknown:
        print_err(f"[ERROR] Unknown parameter: {unknown[0]}")
        parser.print_help()
        sys.exit(1)
        
    target_dir = args.custom_dir if args.custom_dir else DEFAULT_TARGET_DIR
    binary_path = os.path.join(target_dir, "agy")
    
    # Pre-existence Check
    if os.path.isfile(binary_path):
        print(f"Notice: 'agy' is already installed at {binary_path}.")
        print("The Antigravity CLI automatically self-updates in the background during regular runs.")
        print("")
        print("If you want to perform a fresh installation, delete the binary first:")
        print(f"  rm \"{binary_path}\"")
        sys.exit(0)
        
    print("⠋ Detecting system environment...")
    
    # Detect Platform (Linux Only)
    sys_os = platform.system()
    if sys_os != "Linux":
        print_err(f"Fatal: Unsupported operating system: {sys_os}. This script is for Linux only.")
        sys.exit(1)
        
    machine = platform.machine().lower()
    if machine in ["x86_64", "amd64"]:
        arch_name = "amd64"
    elif machine in ["aarch64", "arm64"]:
        arch_name = "arm64"
    else:
        print_err(f"Fatal: Unsupported architecture: {machine}. Antigravity CLI currently supports 64-bit Linux.")
        sys.exit(1)
        
    # musl libc detection on Linux
    musl_detected = False
    if os.path.isfile("/lib/libc.musl-x86_64.so.1") or os.path.isfile("/lib/libc.musl-aarch64.so.1"):
        musl_detected = True
    else:
        try:
            ldd_out = subprocess.check_output(["ldd", "/bin/ls"], stderr=subprocess.STDOUT, text=True)
            if "musl" in ldd_out:
                musl_detected = True
        except Exception:
            pass
    
    if musl_detected:
        plat_suffix = f"linux_{arch_name}_musl"
    else:
        plat_suffix = f"linux_{arch_name}"
        
    print(f"✓ Platform detected: {plat_suffix}")
    
    print("⠋ Querying release repository...")
    manifest_url = f"{DOWNLOAD_BASE_URL}/manifests/{plat_suffix}.json"
    
    try:
        req = urllib.request.Request(manifest_url)
        with urllib.request.urlopen(req) as response:
            manifest_json = json.loads(response.read().decode('utf-8'))
    except (URLError, HTTPError, ValueError) as e:
        print_err("Fatal: Could not connect to the release server to download the manifest. Please check your internet connection or firewall settings.")
        sys.exit(1)
        
    version = manifest_json.get("version")
    url = manifest_json.get("url")
    sha512 = manifest_json.get("sha512")
    
    if not url or not sha512:
        print_err("Fatal: Failed to parse release manifest. The manifest may be corrupted or malformed.")
        sys.exit(1)
        
    print(f"✓ Latest available version: {version}")
    
    # Download & SHA512 Checksum Verification
    try:
        os.makedirs(STAGING_DIR, exist_ok=True)
    except OSError:
        print_err(f"Error: Failed to create staging directory at {STAGING_DIR}. Please check your home directory write permissions.")
        sys.exit(1)
        
    is_tar_gz = "tar.gz" in url
    
    if is_tar_gz:
        staging_payload = os.path.join(STAGING_DIR, "agy.tar.gz")
        extracted_binary = os.path.join(STAGING_DIR, "antigravity")
    else:
        staging_payload = os.path.join(STAGING_DIR, "agy")
        extracted_binary = staging_payload
        
    # Cleanup block via try/finally
    try:
        print("⠋ Downloading release package...")
        try:
            urllib.request.urlretrieve(url, staging_payload)
        except (URLError, HTTPError) as e:
            print_err(f"Fatal: Failed to download release package from {url}. Please check your internet connection or firewall settings.")
            sys.exit(1)
            
        # Compute SHA512 Checksum
        actual_hash = hashlib.sha512()
        try:
            with open(staging_payload, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    actual_hash.update(chunk)
            actual_hash_hex = actual_hash.hexdigest()
        except OSError:
            actual_hash_hex = ""
            
        if actual_hash_hex != sha512:
            print_err("Security Halt: The downloaded payload checksum does not match the manifest. The file may be corrupted or compromised. Installation aborted.")
            sys.exit(1)
            
        print("✓ Download complete and checksum verified.")
        
        # Direct Binary Extraction & Write Permission Validation
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError:
            print_err(f"Write Error: Permission denied when attempting to create {target_dir}. Please re-run the installer using the '--dir' flag to specify a writable custom directory.")
            sys.exit(1)
            
        if is_tar_gz:
            print("⠋ Extracting binary from archive...")
            try:
                with tarfile.open(staging_payload, "r:gz") as tar:
                    tar.extract("antigravity", path=STAGING_DIR)
            except Exception:
                print_err("Extraction Error: Failed to extract binary from archive.")
                sys.exit(1)
        else:
            print("⠋ Copying binary directly to destination...")
            
        try:
            shutil.copy2(extracted_binary, binary_path)
        except OSError:
            print_err(f"Write Error: Permission denied when attempting to write binary to {binary_path}. Please re-run the installer using the '--dir' flag to specify a writable custom directory.")
            sys.exit(1)
            
        # Ensure Executable Permission Bit
        try:
            os.chmod(binary_path, 0o755)
        except OSError:
            print_err(f"Warning: Could not set executable permission bit on {binary_path}. You may need to ensure the partition supports execution.")
            
        # Native Setup Handoff
        print("⠋ Configuring shell environment...")
        
        setup_cmd = [binary_path, "install"]
        if args.custom_dir:
            setup_cmd.extend(["--dir", args.custom_dir])
            
        subprocess.run(setup_cmd, check=False)

    finally:
        # Robust cleanup
        if staging_payload and os.path.exists(staging_payload):
            try:
                os.remove(staging_payload)
            except OSError:
                pass
        if extracted_binary and os.path.exists(extracted_binary) and extracted_binary != staging_payload:
            try:
                os.remove(extracted_binary)
            except OSError:
                pass

if __name__ == "__main__":
    main()
