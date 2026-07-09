#!/usr/bin/env python3
# strap.py - setup BlackArch Linux keyring and install initial packages

import os
import sys
import tempfile
import urllib.request
import subprocess
import shutil
import hashlib

def get_latest_version():
    try:
        response = urllib.request.urlopen('https://blackarch.org/strap.sh', timeout=8)
        content_bytes = response.read()
        
        # Verify SHA1 sum to prevent MITM
        expected_sha1 = "00688950aaf5e5804d2abebb8d3d3ea1d28525ed"
        actual_sha1 = hashlib.sha1(content_bytes).hexdigest()
        
        if actual_sha1 != expected_sha1:
            print(f"\033[1;31m[-] ERROR: MITM Protection! strap.sh SHA1 mismatch.\033[0m", file=sys.stderr)
            print(f"\033[1;31m    Expected: {expected_sha1}\033[0m", file=sys.stderr)
            print(f"\033[1;31m    Got:      {actual_sha1}\033[0m", file=sys.stderr)
            sys.exit(1337)
            
        content = content_bytes.decode('utf-8')
        for line in content.splitlines():
            if line.startswith('VERSION='):
                return line.split('=')[1].strip().strip('"').strip("'")
    except SystemExit:
        raise
    except Exception:
        print("\033[1;31m[!] WARNING: Could not fetch the latest version from blackarch.org. Falling back to 20251011\033[0m", file=sys.stderr)
    return "20251011"

VERSION = get_latest_version()
MIRROR_F = "blackarch-mirrorlist"

def err(msg):
    print(f"\033[1;31m[-] ERROR: {msg}\033[0m", file=sys.stderr)
    sys.exit(1337)

def warn(msg):
    print(f"\033[1;31m[!] WARNING: {msg}\033[0m", file=sys.stderr)

def msg_print(msg):
    print(f"\033[1;32m[+] {msg}\033[0m")

def check_priv():
    if os.geteuid() != 0:
        err("you must be root")

def check_internet():
    try:
        urllib.request.urlopen('https://blackarch.org/', timeout=8)
    except Exception:
        err("You don't have an Internet connection!")

def calculate_sha256(filepath):
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        warn(f"Failed to calculate SHA256 for {filepath}: {e}")
        return None

def fetch_keyring():
    keyring_url = f"https://www.blackarch.org/keyring/blackarch-keyring-{VERSION}.tar.gz"
    sig_url = f"https://www.blackarch.org/keyring/blackarch-keyring-{VERSION}.tar.gz.sig"
    try:
        urllib.request.urlretrieve(keyring_url, f"blackarch-keyring-{VERSION}.tar.gz")
        urllib.request.urlretrieve(sig_url, f"blackarch-keyring-{VERSION}.tar.gz.sig")
        
        keyring_file = f"blackarch-keyring-{VERSION}.tar.gz"
        hash_val = calculate_sha256(keyring_file)
        if hash_val:
            msg_print(f"Downloaded {keyring_file}")
            msg_print(f"SHA256 Checksum: {hash_val}")
            
    except Exception as e:
        err(f"Failed to fetch keyring: {e}")

def verify_keyring():
    key = "4345771566D76038C7FEB43863EC0ADBEA87E4E3"
    servers = [
        "keyserver.ubuntu.com",
        "hkps://keyserver.ubuntu.com:443",
        "hkp://pgp.mit.edu:80"
    ]
    success = False
    for server in servers:
        if subprocess.run(['gpg', '--keyserver', server, '--recv-keys', key], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            success = True
            break
            
    if not success:
        err("could not verify the key. Please check: https://blackarch.org/faq.html")
        
    if subprocess.run(['gpg', '--keyserver-options', 'no-auto-key-retrieve',
                       '--with-fingerprint', f"blackarch-keyring-{VERSION}.tar.gz.sig"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        err("invalid keyring signature. please stop by https://matrix.to/#/#BlackArch:matrix.org")

def delete_signature():
    sig_file = f"blackarch-keyring-{VERSION}.tar.gz.sig"
    if os.path.exists(sig_file):
        os.remove(sig_file)

def check_pacman_gnupg():
    subprocess.run(['pacman-key', '--init'], check=False)

def install_keyring():
    keyring_file = f"blackarch-keyring-{VERSION}.tar.gz"
    keyring_dir = "/usr/share/pacman/keyrings/"
    os.makedirs(keyring_dir, exist_ok=True)
    subprocess.run(['tar', 'xfz', keyring_file, '--strip-components=1', '-C', keyring_dir], check=True)
    subprocess.run(['pacman-key', '--populate'], check=False)

def get_mirror():
    mirror_p = "/etc/pacman.d"
    mirror_r = "https://blackarch.org"
    msg_print("fetching new mirror list...")
    try:
        urllib.request.urlretrieve(f"{mirror_r}/{MIRROR_F}", f"{mirror_p}/{MIRROR_F}")
    except Exception:
        err(f"we couldn't fetch the mirror list from: {mirror_r}/{MIRROR_F}")
    msg_print(f"you can change the default mirror under {mirror_p}/{MIRROR_F}")

def update_pacman_conf():
    conf_path = "/etc/pacman.conf"
    
    if os.path.exists(conf_path):
        with open(conf_path, 'r') as f:
            lines = f.readlines()
        
        with open(conf_path, 'w') as f:
            skip_next = False
            for line in lines:
                if skip_next:
                    skip_next = False
                    continue
                if 'blackarch' in line:
                    skip_next = True
                    continue
                f.write(line)
        
        with open(conf_path, 'a') as f:
            f.write("\n[blackarch]\n")
            f.write(f"Include = /etc/pacman.d/{MIRROR_F}\n")

def pacman_update():
    if subprocess.run(['pacman', '-Syy']).returncode == 0:
        return
    warn("Synchronizing pacman has failed. Please try manually: pacman -Syy")

def pacman_upgrade():
    subprocess.run(['pacman', '-Syyu', '--noconfirm'], check=False)

def blackarch_setup():
    msg_print('installing blackarch keyring...')
    check_priv()
    
    old_umask = os.umask(0o022)
    try:
        with tempfile.TemporaryDirectory(prefix="blackarch_strap.") as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                check_internet()
                fetch_keyring()
                #verify_keyring()
                delete_signature()
                check_pacman_gnupg()
                install_keyring()
            finally:
                os.chdir(old_cwd)
                
        print()
        msg_print('keyring installed successfully')
        
        conf_path = "/etc/pacman.conf"
        has_blackarch = False
        if os.path.exists(conf_path):
            with open(conf_path, 'r') as f:
                if '[blackarch]' in f.read():
                    has_blackarch = True
                    
        if not has_blackarch:
            msg_print('configuring pacman')
            get_mirror()
            msg_print('updating pacman.conf')
            update_pacman_conf()
            
        msg_print('updating package databases')
        pacman_update()
    finally:
        os.umask(old_umask)
        
    msg_print('installing blackarch-mirrorlist package')
    subprocess.run(['pacman', '-S', '--noconfirm', 'blackarch-mirrorlist'], check=False)
    
    pacnew_file = "/etc/pacman.d/blackarch-mirrorlist.pacnew"
    mirror_file = "/etc/pacman.d/blackarch-mirrorlist"
    if os.path.exists(pacnew_file):
        shutil.move(pacnew_file, mirror_file)
        
    msg_print('BlackArch repository is ready!')
    msg_print('You can install `blackarch-officials` metapackage with the most popular tools using the command below:')
    msg_print('sudo pacman -S --needed blackarch-officials')

def nalca_install(root="/mnt", user: str = ""):
    msg_print(f"Installing BlackArch mirrors into target {root} via arch-chroot...")
    script_path = os.path.abspath(__file__)
    dest_path = os.path.join(root, "home", user, "strap.py")
    os.makedirs(os.path.join(root, "home", user), exist_ok=True)
    shutil.copy2(script_path, dest_path)
    subprocess.run(["arch-chroot", root, f"/home/{user}/strap.py"], check=True)
    try:
        os.remove(dest_path)
    except OSError:
        pass
    msg_print("BlackArch setup completed successfully.")

if __name__ == '__main__':
    blackarch_setup()