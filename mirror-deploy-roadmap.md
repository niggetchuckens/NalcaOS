# NalcaOS Package Repository & Build Infrastructure

This document outlines the complete workflow for establishing a secure, high-performance pacman package repository, scaling from local homelab testing to a production-ready distribution infrastructure.

---

## 1. Context: The PHX Mirror Model

When analyzing high-performance distributions like CachyOS, you'll encounter geographically designated mirrors such as **PHX** (Phoenix, Arizona). In a distribution's architecture, these Tier-1 mirrors handle massive, optimized package trees (e.g., x86-64-v3/v4 binaries) and sync directly from the main build servers via push synchronizations (like `rsync` over SSH). 

Replicating this model for a custom distribution requires a highly efficient web server, strict caching rules, and a clean build environment.

---

## 2. Hosting the Repository with Nginx

Serving a pacman repository requires specific caching headers. Package files (`.pkg.tar.zst`) are immutable and should be cached aggressively, while database files (`.db` and `.files`) must never be cached so client machines always see the latest updates instantly.

### Directory Setup
Ensure the Nginx `http` user has read access to the repository directory.

```bash
sudo mkdir -p /srv/http/nalcaos
sudo chown -R $USER:http /srv/http/nalcaos
sudo chmod -R 755 /srv/http/nalcaos
```

### Nginx Configuration (`/etc/nginx/sites-available/nalcaos.conf`)
```nginx
server {
    listen 80;
    listen [::]:80;
    
    server_name 192.168.1.50 repo.nalcaos.local; 

    root /srv/http;

    autoindex on;
    autoindex_exact_size off;
    autoindex_localtime on;

    location /nalcaos {
        # Rule 1: NEVER cache database files.
        location ~ \.(db|files)(\.tar\.(gz|bz2|xz|zst))?(\.sig)?$ {
            add_header Cache-Control "no-store, no-cache, must-revalidate";
            expires -1;
        }

        # Rule 2: Cache packages aggressively (30 days).
        location ~ \.pkg\.tar\.(xz|zst)(\.sig)?$ {
            add_header Cache-Control "public, max-age=2592000";
        }
    }
}
```

After saving, test and reload Nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 3. GnuPG Package Signing

To ensure the integrity of the distribution, all packages and databases should be cryptographically signed.

### Generate Key & Configure Makepkg
1. Generate the master key: `gpg --full-gen-key` (Select RSA 4096).
2. Find your Key ID: `gpg --list-secret-keys --keyid-format=long`
3. Edit `/etc/makepkg.conf`:

```ini
# Identify the packager
PACKAGER="Hime <your.email@example.com>"

# Add your 16-character GPG Key ID
GPGKEY="YOUR_16_CHAR_KEY_ID"

# Enable signing in the BUILDENV array (remove the '!' in front of 'sign')
BUILDENV=(!distcc color !ccache check sign) 
```

### Export Public Key for Clients
Host the public key on the repository server for easy onboarding:
```bash
gpg --armor --export YOUR_16_CHAR_KEY_ID > /srv/http/nalcaos/nalcaos-key.pub
```

### Client Configuration (`/etc/pacman.conf`)
On the target machines, import the key, sign it locally, and enforce signatures:

```bash
curl -O http://192.168.1.50/nalcaos/nalcaos-key.pub
sudo pacman-key --add nalcaos-key.pub
sudo pacman-key --lsign-key YOUR_16_CHAR_KEY_ID
```

```ini
[nalcaos]
SigLevel = Required DatabaseOptional
Server = http://192.168.1.50/nalcaos
```

---

## 4. Building in a Clean Chroot

To guarantee that `PKGBUILD` files contain all necessary dependencies without relying on the host system's state, always build in a clean chroot.

### Initialize the Chroot
```bash
sudo pacman -S devtools
mkdir ~/chroot
export CHROOT=$HOME/chroot
sudo mkarchroot $CHROOT/root base-devel
```

*(Optional)* If building packages that depend on custom libraries already in your repo, add the `[nalcaos]` repository block to `$CHROOT/root/etc/pacman.conf`.

### Execute the Build
Navigate to your `PKGBUILD` directory and run:
```bash
sudo makechrootpkg -c -r $CHROOT
```

---

## 5. Automation: Deployment Script

This script automates moving newly compiled packages to the Nginx directory, fixing permissions, and securely updating the pacman database.

Save as `/usr/local/bin/deploy-pkg` and make executable (`chmod +x /usr/local/bin/deploy-pkg`).

```bash
#!/bin/bash
# deploy-pkg.sh - Automates NalcaOS repository updates

REPO_DIR="/srv/http/nalcaos"
DB_NAME="nalcaos.db.tar.gz"
DB_PATH="$REPO_DIR/$DB_NAME"

shopt -s nullglob
PACKAGES=(*.pkg.tar.zst)

if [ ${#PACKAGES[@]} -eq 0 ]; then
    echo "Error: No .pkg.tar.zst files found."
    exit 1
fi

echo "Deploying ${#PACKAGES[@]} package(s) to $REPO_DIR..."
TARGET_PKGS=()

for pkg in "${PACKAGES[@]}"; do
    sudo mv "$pkg" "$REPO_DIR/"
    TARGET_PKGS+=("$REPO_DIR/$pkg")
    
    if [ -f "$pkg.sig" ]; then
        sudo mv "$pkg.sig" "$REPO_DIR/"
    fi
done

echo "Updating Nginx permissions..."
sudo chown -R $USER:http "$REPO_DIR"
sudo chmod -R 755 "$REPO_DIR"

echo "Signing and updating repository database..."
repo-add -s -R "$DB_PATH" "${TARGET_PKGS[@]}"

echo "Deployment complete! Run 'pacman -Sy' on clients."
```

### The Final Workflow
1. Navigate to the package directory.
2. Build: `sudo makechrootpkg -c -r ~/chroot`
3. Deploy: `deploy-pkg`