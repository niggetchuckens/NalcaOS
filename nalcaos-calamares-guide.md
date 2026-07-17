# NalcaOS Calamares Live ISO Integration Guide

Welcome to the definitive guide on integrating the **Calamares** graphical installer into your NalcaOS Live ISO. Calamares is a modular, distribution-agnostic installer framework used by many major Linux distributions (such as Manjaro, EndeavourOS, Debian Live, and KDE Neon). 

This guide will walk you through the architecture, configuration, branding, and integration steps to provide a premium graphical installation experience for NalcaOS users.

---

## 1. Prerequisites and Live ISO Base

Before you configure Calamares, you must have a functioning Live ISO build system. Depending on what NalcaOS is based on, you will use different tools:

*   **Arch Linux Base:** `archiso`
*   **Debian/Ubuntu Base:** `live-build` or `casper`
*   **Fedora/RedHat Base:** `livecd-creator`

Your live environment **must** include the following for Calamares to launch:
*   A Desktop Environment (DE) or Window Manager (e.g., KDE Plasma, XFCE, GNOME)
*   **Qt5/Qt6 libraries** (Calamares is built on Qt)
*   **Polkit** (for privilege escalation)
*   **KPMcore** (KDE Partition Manager core, required for the partitioning module)
*   **Python 3** (many Calamares modules are Python scripts)
*   **sudo** or a similar privilege escalation tool

> [!IMPORTANT]
> The `calamares` package should be installed *within* the Live ISO environment, not on the host building the ISO. Ensure your build scripts include `calamares` and its dependencies in the target package list.

---

## 2. Calamares Architecture and Structure

Calamares configuration is driven by YAML and `.conf` files. Its primary files are located in `/etc/calamares/` inside the Live ISO.

| Directory / File | Purpose |
| :--- | :--- |
| `/etc/calamares/settings.conf` | The master configuration file. Controls the module sequence. |
| `/etc/calamares/branding/` | Contains the branding files, logos, stylesheets, and slideshows. |
| `/etc/calamares/modules/` | Contains specific `.conf` files for individual modules (e.g., partitioning, users). |

> [!TIP]
> Never directly edit the default files in `/usr/share/calamares/`. Always copy them to `/etc/calamares/` and modify them there. Calamares reads from `/etc/calamares/` first.

---

## 3. The Master Configuration: `settings.conf`

The `settings.conf` file dictates the flow of the installer. It contains a `sequence` array which is divided into `show` (UI screens) and `exec` (backend tasks).

```yaml
# /etc/calamares/settings.conf

modules-search: [ local ]

instances:
- id:       default
  module:   packages
  config:   packages.conf

sequence:
- show:
  - welcome
  - locale
  - keyboard
  - partition
  - users
  - summary
- exec:
  - partition
  - mount
  - unpackfs    # Extracts the root filesystem image (SquashFS)
  - machineid
  - fstab
  - locale
  - keyboard
  - localecfg
  - users
  - displaymanager
  - networkcfg
  - hwclock
  - initcpiocfg
  - initcpio
  - grubcfg
  - bootloader
  - packages
  - umount
- show:
  - finished

branding: nalcaos

prompt-install: true
dont-chroot: false
```

> [!CAUTION]
> Ensure `dont-chroot` is set to `false` for standard installations. If it is `true`, Calamares operates in OEM mode and will make changes to the host (the Live USB) instead of the target disk.

---

## 4. Branding NalcaOS

A premium installer needs excellent branding. Create a directory named `/etc/calamares/branding/nalcaos/`. In `settings.conf`, we already set `branding: nalcaos`.

### `branding.desc`
This file defines strings, images, and window behaviors.

```yaml
# /etc/calamares/branding/nalcaos/branding.desc
---
componentName:  nalcaos

strings:
    productName:         NalcaOS
    shortProductName:    NalcaOS
    version:             1.0 (Genesis)
    shortVersion:        1.0
    versionedName:       NalcaOS 1.0
    shortVersionedName:  NalcaOS 1.0
    bootloaderEntryName: NalcaOS

images:
    productLogo:         "logo.png"
    productIcon:         "icon.png"
    productWelcome:      "welcome.png"

style:
   sidebarBackground:    "#1A1B26"
   sidebarText:          "#A9B1D6"
   sidebarTextSelect:    "#7AA2F7"

slideshow:               "show.qml"
```

### Custom Styling (`stylesheet.qss`)
You can use a Qt StyleSheet to theme the Calamares UI to match your DE. Place a `stylesheet.qss` in your branding folder to apply deep visual changes (like dark mode, rounded corners, or custom fonts).

---

## 5. Configuring Essential Modules

Modules dictate the heavy lifting. Create configuration files in `/etc/calamares/modules/`.

### Partitioning (`partition.conf`)
Controls disk wiping, manual partitioning, and default filesystems.
```yaml
# /etc/calamares/modules/partition.conf
efiSystemPartition:     "/boot/efi"
userSwapChoices:        [none, small, suspend, file]
drawNestedPartitions:   false
alwaysShowPartitionLabels: true
defaultFileSystemType:  "ext4"
```

### File Extraction (`unpackfs.conf`)
This is how the Live ISO transfers the OS to the target disk. It unpacks the SquashFS image containing the root filesystem.
```yaml
# /etc/calamares/modules/unpackfs.conf
unpack:
    -   source: ../image.squashfs
        sourcefs: squashfs
        destination: ""
```

### Users (`users.conf`)
Configures whether a root account is enabled or if `sudo` is the default.
```yaml
# /etc/calamares/modules/users.conf
defaultGroups:
    - wheel
    - video
    - audio
    - network
    - lp
    - input
autologinGroup:  autologin
doAutologin:     false
sudoersGroup:    wheel
setRootPassword: false # Highly recommended to use sudo for the user instead
```

### Packages (`packages.conf`)
Allows you to install or remove packages at the end of the installation process (useful for removing live-cd specific packages from the installed system).
```yaml
# /etc/calamares/modules/packages.conf
backend: pacman # or apt, dnf, etc.

operations:
  - try_remove:
    - calamares
    - arch-install-scripts
    - mkinitcpio-archiso
```

---

## 6. Testing and Debugging

Do not test your Live ISO on your primary physical machine.

1.  **Virtual Machines**: Use **VirtualBox**, **virt-manager (KVM/QEMU)**, or **VMware**.
2.  **EFI Support**: Always enable EFI/UEFI booting in your VM settings. Most modern users will install NalcaOS on an EFI system, and you need to ensure the bootloader module works.
3.  **Debug Mode**: If Calamares fails or crashes inside the Live ISO, open a terminal and run:
    ```bash
    sudo calamares -d
    ```
    This outputs verbose debug information. It will tell you exactly which module failed and why (e.g., missing dependencies, malformed YAML, or script errors).

> [!NOTE]
> Calamares modules are executed sequentially. If a step like `fstab` fails, the installation halts there. Reviewing the terminal output from `-d` is crucial for fixing the exact step that failed.

---

## Next Steps for NalcaOS

1.  Review the default configuration files available in the [Calamares GitHub Repository](https://github.com/calamares/calamares/tree/calamares/src/modules) to see all possible options for each module.
2.  Design a beautiful set of QML slides for your `slideshow` to educate users about NalcaOS features while the system unpacks.
3.  Test edge cases: dual booting alongside Windows, encrypted disks (LUKS), and offline installations.
