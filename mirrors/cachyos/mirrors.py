#!/usr/bin/env python3
# manage_mirrors.py - setup CachyOS mirrors and install initial packages

import os
import sys
import subprocess
import tempfile
import glob
import hashlib

def err(msg):
    print(f"\033[1;31m[-] ERROR: {msg}\033[0m", file=sys.stderr)
    sys.exit(1337)

def msg_print(msg):
    print(f"\033[1;32m[+] {msg}\033[0m")

def check_priv():
    if os.geteuid() != 0:
        err("you must be root")

def get_cpu_isa():
    try:
        output = subprocess.check_output(['/lib/ld-linux-x86-64.so.2', '--help']).decode()
        if 'x86-64-v4 (supported, searched)' in output:
            return 'v4'
        if 'x86-64-v3 (supported, searched)' in output:
            return 'v3'
    except Exception:
        pass
    return ''

def calculate_sha256(filepath):
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"\033[1;31m[!] WARNING: Failed to calculate SHA256 for {filepath}: {e}\033[0m", file=sys.stderr)
        return None

def get_official_hash(pkg_name):
    try:
        output = subprocess.check_output(['pacman', '-Si', pkg_name]).decode()
        for line in output.splitlines():
            if 'SHA-256 Sum' in line:
                return line.split(':', 1)[1].strip()
    except Exception:
        pass
    return None

def setup_keyring():
    msg_print("Setting up CachyOS keyring...")
    subprocess.run(['pacman-key', '--recv-keys', 'F3B607488DB35A47', '--keyserver', 'keyserver.ubuntu.com'], check=False)
    subprocess.run(['pacman-key', '--lsign-key', 'F3B607488DB35A47'], check=False)

def install_cachyos_packages():
    msg_print("Adding temporary CachyOS repo to fetch keyrings and mirrorlists...")
    conf_path = "/etc/pacman.conf"
    with open(conf_path, 'r') as f:
        original_conf = f.read()

    if '[cachyos]' not in original_conf:
        with open(conf_path, 'a') as f:
            f.write("\n[cachyos]\nServer = https://mirror.cachyos.org/repo/x86_64/cachyos\n")

    subprocess.run(['pacman', '-Sy'], check=False)
    
    with tempfile.TemporaryDirectory() as pkg_cache_dir:
        packages = ['cachyos-keyring', 'cachyos-mirrorlist', 'cachyos-v3-mirrorlist', 'cachyos-v4-mirrorlist']
        subprocess.run(['pacman', '-Sw', '--noconfirm', '--cachedir', pkg_cache_dir] + packages, check=False)
        
        downloaded_pkgs = glob.glob(os.path.join(pkg_cache_dir, "*.pkg.tar.zst"))
        if not downloaded_pkgs:
            msg_print("No packages were downloaded. Attempting direct installation instead.")
            subprocess.run(['pacman', '-S', '--noconfirm'] + packages, check=False)
        else:
            for pkg in downloaded_pkgs:
                pkg_name = os.path.basename(pkg).split('-20')[0].split('-1')[0] 
                for p in packages:
                    if pkg.split('/')[-1].startswith(p + '-'):
                        pkg_name = p
                        break
                        
                hash_val = calculate_sha256(pkg)
                official_hash = get_official_hash(pkg_name)
                
                if hash_val:
                    msg_print(f"Downloaded {os.path.basename(pkg)}")
                    msg_print(f"Calculated SHA256: {hash_val}")
                    if official_hash:
                        msg_print(f"Official SHA256:   {official_hash}")
                        if hash_val == official_hash:
                            msg_print("\033[1;32m[+] Checksum MATCHED successfully!\033[0m")
                        else:
                            err(f"Checksum MISMATCH for {pkg_name}! Aborting.")
                    else:
                        msg_print("Could not retrieve official hash for comparison.")
            
            subprocess.run(['pacman', '-U', '--noconfirm'] + downloaded_pkgs, check=False)

    with open(conf_path, 'w') as f:
        f.write(original_conf)

def append_cachyos_repos():
    msg_print("Appending CachyOS repos to pacman.conf...")
    isa = get_cpu_isa()
    repos = []

    if isa == 'v4':
        repos.extend([
            "[cachyos-v4]",
            "Include = /etc/pacman.d/cachyos-v4-mirrorlist",
            "[cachyos-core-v4]",
            "Include = /etc/pacman.d/cachyos-v4-mirrorlist",
            "[cachyos-extra-v4]",
            "Include = /etc/pacman.d/cachyos-v4-mirrorlist"
        ])
    elif isa == 'v3':
        repos.extend([
            "[cachyos-v3]",
            "Include = /etc/pacman.d/cachyos-v3-mirrorlist",
            "[cachyos-core-v3]",
            "Include = /etc/pacman.d/cachyos-v3-mirrorlist",
            "[cachyos-extra-v3]",
            "Include = /etc/pacman.d/cachyos-v3-mirrorlist"
        ])

    repos.extend([
        "[cachyos]",
        "Include = /etc/pacman.d/cachyos-mirrorlist"
    ])

    conf_path = "/etc/pacman.conf"
    with open(conf_path, 'r') as f:
        content = f.read()

    if '[cachyos]' in content:
        msg_print("CachyOS repos already seem present in pacman.conf, skipping append.")
        return

    with open(conf_path, 'a') as f:
        f.write("\n" + "\n".join(repos) + "\n")

    msg_print("CachyOS repos appended successfully.")

def update_pacman():
    msg_print("Updating package databases...")
    subprocess.run(['pacman', '-Syy'], check=False)
    msg_print("Upgrading system packages using CachyOS repos...")
    subprocess.run(['pacman', '-Su', '--noconfirm'], check=False)

def main():
    check_priv()
    setup_keyring()
    install_cachyos_packages()
    append_cachyos_repos()
    # update_pacman()
    msg_print("CachyOS mirrors setup complete!")

if __name__ == "__main__":
    main()