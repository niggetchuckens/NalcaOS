# Building PortProton for Arch Linux

To build an Arch Linux package (`.pkg.tar.zst` or `.pkg.tar.xz`) for PortProton, you will need the **`PortProton_PKGBUILD`** repository from Castro-Fidel. This repository contains the `PKGBUILD` file which tells Arch's package manager how to download, compile, and package the software.

Here is the step-by-step process to build the package:

### Step 1: Install Git and Base-Devel
Ensure you have `git` and the base development tools required to build Arch packages:
```bash
sudo pacman -S --needed git base-devel
```

### Step 2: Enable the `multilib` repository
The PortProton PKGBUILD requires several 32-bit (`lib32-*`) dependencies. These packages are found in the `multilib` repository, which needs to be enabled in Arch Linux.

Open `/etc/pacman.conf` in your preferred text editor with `sudo` (e.g., `sudo nano /etc/pacman.conf`) and ensure the following two lines are uncommented (remove the `#` at the beginning):
```ini
[multilib]
Include = /etc/pacman.d/mirrorlist
```
After making changes, update your system databases:
```bash
sudo pacman -Sy
```

### Step 3: Enter the PKGBUILD directory
Navigate to the directory where your PKGBUILD is located:
```bash
cd /home/hime/code/nalcaos/binaries/to-build/PortProton_PKGBUILD
```

### Step 4: Build the package with dependencies
To compile the package and automatically resolve and install all missing dependencies, run:
```bash
makepkg -s
```
*(Note: The `-s` or `--syncdeps` flag tells `makepkg` to automatically use `pacman` to install any missing dependencies listed in the PKGBUILD file. It will prompt you for your `sudo` password to install those dependencies).*

- To **build the package and install it immediately** once the build finishes successfully, you can add the `-i` flag:
  ```bash
  makepkg -si
  ```
- To **only build the package** and clean up leftover build files, run:
  ```bash
  makepkg -sc
  ```

*(Note: Arch Linux builds `.pkg.tar.zst` by default for better compression speed, but it functions exactly the same as the older `.pkg.tar.xz` format).*

### Step 5 (Optional): Install the generated package manually
If you used `makepkg -sc` or `makepkg -s` in step 4 and just want to install the resulting package file manually later, you can do so with pacman:
```bash
sudo pacman -U *.pkg.tar.zst
```
