# NalcaOS

NalcaOS is a custom operating system installation project. It includes scripts to automate the installation and configuration of a fully functional Linux environment with selected tools, desktop environments, and optimizations out of the box.

## Project Structure

- `installer.py`: The main installation script (written in Python) designed for Arch Linux. It automates disk partitioning, base system installation, user creation, and desktop environment setup.
- `install.sh`: A post-installation shell script for setting up additional software, Flatpaks, and custom applications (such as Proteus, XAMPP, and Cisco tools). *Note: This script currently uses `apt` and appears to be targeted at Debian-based systems.*
- `mirrors/`: Contains Python modules to set up third-party repositories like BlackArch and CachyOS.
- `binaries/`: Stores pre-compiled binaries (e.g., `yay.pkg.tar.zst`) for quick installation without compiling from the AUR during setup.

## Technical Details

### Arch Linux Installer (`installer.py`)

The Python installer automates an Arch Linux installation using a series of defined functions to step through the standard Arch installation guide programmatically:

- `run_command()`: A robust helper function to execute shell commands programmatically and halt the installation if critical errors occur.
- `configure_pacman()`: Enhances the package manager by editing `/etc/pacman.conf` to enable `Color`, `ParallelDownloads`, and the hidden `ILoveCandy` easter egg for a better visual experience during installation.
- `set_disks()`: Asks the user for a target drive (e.g., `sda`, `nvme0n1`). It then completely wipes the drive, creates a 1GB EFI (`fat32`) partition for boot and an `ext4` partition for the rest of the root filesystem using `parted`, and automatically mounts them to `/mnt`.
- `install_base()`: Prompts the user to specify their hardware (Intel/AMD CPU and Intel/AMD/NVIDIA GPU). It then dynamically runs `pacstrap` to install the `base`, `linux-firmware`, `base-devel`, network tools, OpenSSH, and the correct microcode/graphics drivers for the chosen hardware. It also generates the `fstab` file.
- `de_select()`: Provides an interactive menu for the user to choose their preferred Desktop Environment or Window Manager. Options include: KDE Plasma, GNOME, XFCE, Hyprland, Sway, or a headless (TTY-only) setup. It maps the selection to the corresponding Arch packages and display manager service (e.g., `sddm`, `gdm`, `lightdm`).
- `base_config()`: The final overarching setup function that handles the `arch-chroot` stage. It manages:
  - Setting the timezone to `America/Santiago` and synchronizing the hardware clock.
  - Setting the system locales to `en_US.UTF-8` and setting the hostname to `NalcaOS`.
  - Creating a root password and setting up a new standard user with `wheel` (sudo) privileges.
  - **Third-party Repositories**: Invoking the Python modules from the `mirrors/` folder to install the **BlackArch** penetration testing repository and the **CachyOS** repository. It then installs the optimized `linux-cachyos-lts` kernel.
  - **Bootloader**: Installing `grub` and `efibootmgr`, then configuring GRUB for UEFI.
  - **AUR Helper**: Copying over and installing a pre-compiled `yay` package from the local `binaries/` directory so it is available out of the box.
  - **DE Installation**: Finally, it installs the packages selected in `de_select()`, enables the display manager, NetworkManager, and sshd services, unmounts the drives, and reboots.

### Debian-Based Post-Installation (`install.sh`)

This script serves to bootstrap a machine with additional user-space tools, leveraging Flatpaks and direct downloads from a custom Minio server.

- `user_to_sudoers()`: Dynamically grants password-less `sudo` rights to the active user by adding them to `/etc/sudoers.d/`.
- `install_pkgs()`: Uses `apt` to install development basics (btop, git, openssh). It then initializes `flathub` and installs GUI applications through Flatpak (PortProton, VS Code, OnlyOffice).
- `install_proteus()`: Downloads a custom `proteus.tar.gz` archive from the project's server, extracts it, and creates a Linux `.desktop` entry that launches the Windows application via PortProton seamlessly.
- `install_xampp()`: Automatically downloads and performs an unattended, silent installation of XAMPP via a `.run` binary.
- `install_cisco()`: Downloads and installs the Cisco Packet Tracer via a `.deb` package using `apt`.

## Usage

### Running the Arch Linux Installer
To install NalcaOS using the Python installer, boot into an Arch Linux live ISO, ensure you are connected to the internet, and execute:

```bash
python installer.py
```
The script will prompt you for the disk to format, your CPU/GPU manufacturers, your preferred Desktop Environment, and credentials for the new user.

### Post-Installation Apps (Debian-based)
If you are on a Debian-based system (or adapting the script for Arch), you can run the post-installation script to install additional tools and Flatpaks:

```bash
sudo ./install.sh
```

## Planned Features

Check the [`todo.md`](todo.md) file for upcoming features and planned improvements, such as:
- Automatic local XAMPP configuration script.
- Pre-compiling PortProton for system-wide installation.
- Installation of virtualization tools, programming languages, and IDEs.
