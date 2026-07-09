# Building PortProton for Arch Linux

To build an Arch Linux package (`.pkg.tar.zst` or `.pkg.tar.xz`) for PortProton, you will need the **`PortProton_PKGBUILD`** repository from Castro-Fidel. This repository contains the `PKGBUILD` file which tells Arch's package manager how to download, compile, and package the software.

Here is the step-by-step process to build the package:

### Step 1: Install Git and Base-Devel
Ensure you have `git` and the base development tools required to build Arch packages:
```bash
sudo pacman -S --needed git base-devel
```

### Step 2: Clone the PKGBUILD repository

### Step 3: Enter the cloned directory

### Step 4: Build the package
Use the `makepkg` command to build the package. 

- To **build the package and install it immediately** along with any missing dependencies, run:
  ```bash
  makepkg -si
  ```
- To **only build the package** (to create the `.pkg.tar.zst` / `.pkg.tar.xz` file so you can distribute or install it later manually), run:
  ```bash
  makepkg -sc
  ```

*(Note: Arch Linux builds `.pkg.tar.zst` by default for better compression speed, but it functions exactly the same as the older `.pkg.tar.xz` format).*

### Step 5 (Optional): Install the generated package manually
If you used `makepkg -sc` in step 4 and just want to install the resulting package file manually later, you can do so with pacman:
```bash
sudo pacman -U *.pkg.tar.zst
```
