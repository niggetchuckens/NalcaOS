# Pre-Compiling Binaries for NalcaOS Installer

When attempting to include pre-compiled binaries (like AUR packages) for the NalcaOS installer, you might encounter "command not found", "file not found", or "missing dependencies" errors. This typically happens for a few reasons:

1. The package file hasn't been built yet.
2. The compiled package has a version string in its name (e.g., `portproton-1.7.3-1-x86_64.pkg.tar.zst`), but the installer script expects a generic name (e.g., `portproton.pkg.tar.zst`).
3. The package requires 32-bit libraries, but the `multilib` repository is not enabled.
4. You are using `yay -S file.pkg.tar.zst` instead of `pacman -U file.pkg.tar.zst` (or `yay -U`).

## How to Pre-Compile a PKGBUILD

Follow these steps to properly build and prepare any PKGBUILD for the `installer.py` script.

### 1. Build the Package
Navigate to the directory containing the `PKGBUILD` and run `makepkg`:
```bash
cd binaries/to-build/*
# Use -s to sync dependencies and -c to clean up leftover files after building
makepkg -sc
```
*Note: Do not run `makepkg` as `root` (e.g., with `sudo`), as it will refuse to run.*

### 2. Rename the Package
By default, `makepkg` outputs a file containing the package name, version, and architecture (for example, `portproton-1.7.3-1-x86_64.pkg.tar.zst`). 
However, `installer.py` is hardcoded to look for a specific file name. You must rename it to match what the installer expects:
```bash
mv portproton-*.pkg.tar.zst portproton.pkg.tar.zst
```

### 3. Move to the `built` Directory
The `installer.py` script expects pre-compiled binaries to be located in the `binaries/built/` directory. Move the renamed file there:
```bash
mkdir -p ../../built
mv portproton.pkg.tar.zst ../../built/
```

### Summary of Commands
For `PortProton`, the full workflow looks like this:
```bash
cd binaries/to-build/PortProton_PKGBUILD
makepkg -sc
mv portproton-*.pkg.tar.zst portproton.pkg.tar.zst
mkdir -p ../../built
mv portproton.pkg.tar.zst ../../built/
```

## Adding New Pre-compiled Binaries
If you want to add completely new binaries to be installed automatically:
1. Create a folder in `binaries/to-build/` and place the `PKGBUILD` there.
2. Compile it using the steps above.
3. Place the final `.pkg.tar.zst` in `binaries/built/`.
4. Update `installer.py` to copy and install your new binary, mimicking the existing process for PortProton.

---

### Troubleshooting common issues

#### 1. "More binaries are needed" or missing dependencies when installing via `pacman -U`
If you attempt to install the package and it complains about missing dependencies (like `lib32-libgl` or `vulkan-driver`), this is because `PortProton` relies heavily on 32-bit libraries. 
**Solution**: Ensure that the `[multilib]` repository is enabled in `/etc/pacman.conf` and that you have run `pacman -Sy` to update the repository databases. (Note: `installer.py` has now been updated to automatically enable this on the installed system).

#### 2. "Target not found" when using `yay`
If you attempt to install the `.pkg.tar.zst` file directly using `yay -S portproton.pkg.tar.zst`, it will fail because `-S` tells `yay` to look up a package name, not a local file.
**Solution**: To install a local package file, you must use the `-U` flag instead. You can do this with `yay -U portproton.pkg.tar.zst` or `sudo pacman -U portproton.pkg.tar.zst`.
