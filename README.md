# NalcaOS

NalcaOS is a custom operating system installation project for Arch Linux. It includes scripts to automate disk partitioning, base system installation, and configuration of a fully functional Linux environment with optimized third-party repositories, multiple desktop environments/window managers, secure boot support, and essential applications out of the box.

## Installation & Usage

You can install NalcaOS directly from an Arch Linux live ISO without needing to manually clone the repository beforehand. Ensure you are connected to the internet, then execute one of the following commands:

### Option 1: Quick Install (One-Liner)

Run the automated installation script directly using `curl`:

```bash
curl -sSL https://minio-api.hime-code.xyz/nalcaos/install.sh | bash
```

### Option 2: Manual Download & Execute

If you prefer to download the installer script and execute it manually:

```bash
curl -sSL https://minio-api.hime-code.xyz/nalcaos/install.sh -o install.sh
chmod +x install.sh
./install.sh
```

### Option 3: Manual Git Clone & Run

If you have cloned the repository manually within an Arch Linux live media:

```bash
python3 main.py
```

The interactive installer will prompt you for your desired username, password, target disk to partition and format, CPU/GPU hardware brands, and your preferred Desktop Environment or Window Manager. Upon completion, the script automatically unmounts the filesystems and reboots your system.

## Project Structure

- `install.sh`: The automated bootstrap shell script. It downloads the required installation packages directly from the custom MinIO server or seamlessly falls back to cloning the GitHub repository if the server is unreachable, executes `main.py`, and cleans up after installation.
- `main.py`: The entrypoint script for the Python installer. It prompts for initial user credentials and launches the automated installation routine.
- `configs/installer.py`: The core installation module containing the OOP `Installer` class. It manages disk partitioning, base system package installation, chroot configuration, third-party mirrors, secure boot signing, and desktop environment deployment.
- `configs/pacman.py`: Helper script executed inside the chroot environment to finalize package updates and configurations.
- `mirrors/`: Contains Python modules to set up third-party repositories such as **BlackArch** and **CachyOS**.
- `binaries/`: Stores pre-compiled binaries (such as `yay` and `PortProton`) for immediate out-of-the-box installation without requiring manual compilation from the AUR during setup.

## Technical Details

### Automated Bootstrapper (`install.sh`)
The bootstrap script makes deploying NalcaOS fast and resilient:
- **Server Fetch with GitHub Fallback**: Attempts to directly fetch the latest installation assets from the custom MinIO API server (`http://minio-api.hime-code.xyz/nalcaos`). If the homelab/server is unreachable, it automatically falls back to installing `git` via `pacman` and cloning the repository from GitHub.
- **Cleanup & Reboot**: On successful execution of `main.py`, it removes temporary staging folders, cleanly unmounts `/mnt`, and reboots into your fresh installation.

### Core Arch Linux Installer (`configs/installer.py`)
The automated installer executes the standard Arch Linux installation steps programmatically:

- `configure_pacman()`: Modifies `/etc/pacman.conf` to enable `Color`, `ParallelDownloads`, `Multilib` support, and the hidden `ILoveCandy` easter egg for an improved visual package management experience.
- `disks()`: Displays available storage devices to the user via `lsblk`. Once chosen, it wipes the drive, creates a 1GB EFI (`fat32`) boot partition and an `ext4` root filesystem using `parted`, and mounts them under `/mnt` and `/mnt/boot`.
- `install_base()`: Prompts for CPU (Intel/AMD) and GPU (Intel/AMD/NVIDIA) manufacturers to install appropriate microcode and graphics drivers alongside `base`, `linux-firmware`, `base-devel`, network tools, and OpenSSH via `pacstrap`. Automatically generates `/mnt/etc/fstab`.
- `arch_chroot()`: Configures the newly installed system inside `arch-chroot`:
  - Sets timezone to `America/Santiago`, syncs the hardware clock, and generates system locales (`en_US.UTF-8`).
  - Sets hostname to `NalcaOS` and sets root and standard user passwords with `wheel` (sudo) privileges.
  - **Third-Party Repositories**: Integrates modules from `mirrors/` to configure the **BlackArch** penetration testing repository and the **CachyOS** performance repository, installing the `linux-cachyos-lts` kernel.
  - **Pre-compiled Software**: Automatically copies over and installs pre-built binaries from `binaries/`, providing the `yay` AUR helper and `PortProton` out of the box.
  - Configures GRUB for UEFI booting and enables necessary system services (`NetworkManager`, `sshd`).
- `setup_secureboot()`: Automates UEFI Secure Boot signing using `sbctl`. Generates Secure Boot keys, attempts to enroll them into UEFI Setup Mode, and digitally signs GRUB and kernel images (`vmlinuz-*`).
- `install_desktop()`: Provides an interactive menu featuring **18 Desktop Environment and Window Manager options**:
  - **Desktop Environments**: KDE Plasma, GNOME, XFCE, Cinnamon, MATE, LXQt, LXDE, Budgie, Deepin, Pantheon, Enlightenment, Trinity, Cosmic.
  - **Window Managers (Wayland & X11)**: Hyprland, Sway, River, Wayfire, Labwc, Niri, Cage, Hikari, i3-wm, bspwm, Awesome, xmonad, qtile, dwm, Openbox, IceWM, Fluxbox, Herbstluftwm, Spectrwm, JWM, dk, StumpWM, or a headless (TTY-only) setup.
  - Dynamically configures and enables the corresponding display manager service (e.g., `sddm`, `gdm`, `lightdm`).

## Planned Features & Roadmap

Check out the additional documentation files in the repository for upcoming initiatives and deployment workflows:
- [`todo.md`](todo.md): Upcoming features and planned system optimizations.
- [`mirror-deploy-roadmap.md`](mirror-deploy-roadmap.md): Roadmap and technical guide for custom mirror server deployments.
- [`nalcaos-calamares-guide.md`](nalcaos-calamares-guide.md): Reference guide for integrating NalcaOS with the Calamares graphical installer framework.
