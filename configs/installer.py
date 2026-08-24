import os
import re
import sys    
import subprocess


class Installer:
    def __init__(self, user: str = None, password: str = None):
        self.user = user or input("Enter your username: ").strip()
        self.password = password or input("Enter your password: ").strip()
        self.working_dir = os.path.dirname(os.path.abspath(__file__))
        self.mirrors_dir = os.path.join(self.working_dir, "mirrors"); sys.path.append(self.mirrors_dir)
        self.binaries_dir = os.path.join(self.working_dir, "..", "binaries", "built", "apps")
        print(f"Working directory: {self.working_dir}") 
        
    def run_command(self, command, shell=False):
        try:
            subprocess.run(command, shell=shell, check=True)
        except subprocess.CalledProcessError as e:
            print(f"\033[1;31m[!] Command failed: {command}\033[0m", file=sys.stderr)
            print(f"\033[1;31m[!] Return code: {e.returncode}\033[0m", file=sys.stderr)
            sys.exit(1)

    def detect_environment(self):
        try:
            with open("/sys/class/dmi/id/product_name", "r") as f:
                product = f.read().strip().lower()
            if "kvm" in product or "qemu" in product:
                return "qemu"
            elif "virtualbox" in product:
                return "virtualbox"
            elif "vmware" in product:
                return "vmware"
            else:
                return "physical"
        except FileNotFoundError:
            return "unknown"

    def select_environment(self):
        detected = self.detect_environment()
        vm_options = {
            "1": ("Physical machine", False, "physical"),
            "2": ("Virtual machine (QEMU/KVM)", True, "qemu"),
            "3": ("Virtual machine (VirtualBox)", True, "virtualbox"),
            "4": ("Virtual machine (VMware)", True, "vmware"),
            "5": ("Virtual machine (Other)", True, "other")
        }

        detected_key = None
        for key, value in vm_options.items():
            if value[2] == detected:
                detected_key = key
                break

        print("\nSelect your environment:")
        for key, value in vm_options.items():
            marker = " (detected)" if key == detected_key else ""
            print(f"{key}) {value[0]}{marker}")

        choice = ""
        while choice not in vm_options:
            default = f" [{detected_key}]" if detected_key else ""
            choice = input(f"Selection (1-5){default}: ").strip()
            if not choice and detected_key:
                choice = detected_key

        selected = vm_options[choice]
        self.is_vm = selected[1]
        self.vm_type = selected[2]
        env_name = "Virtual Machine" if self.is_vm else "Physical Machine"
        print(f"Environment set to: {env_name} ({self.vm_type})")

    def cleanup_mounts(self):
        mounts = ["/mnt/boot", "/mnt"]
        for mount in mounts:
            try:
                result = subprocess.run(["mountpoint", "-q", mount], capture_output=True)
                if result.returncode == 0:
                    print(f"Unmounting {mount}...")
                    subprocess.run(["umount", "-R", mount], check=False)
            except Exception:
                pass
            
    def configure_pacman(self):
        print("Configuring Pacman (Enabling Colors, Parallel Downloads, ILoveCandy and Multilib)...")
        try:
            with open('/etc/pacman.conf', 'r') as f:
                content = f.read()
                
            content = content.replace('#Color', 'Color')
            content = content.replace('#ParallelDownloads', 'ParallelDownloads')
            if 'ILoveCandy' not in content:
                content = content.replace('Color\n', 'Color\nILoveCandy\n')
    
            content = re.sub(
                r'#\s*\[multilib\]\n#\s*Include\s*=\s*/etc/pacman\.d/mirrorlist',
                '[multilib]\nInclude = /etc/pacman.d/mirrorlist',
                content
            )

            with open('/etc/pacman.conf', 'w') as f:
                f.write(content)

            subprocess.run(["pacman", "-Sy", "--noconfirm"], check=False)

        except Exception as e:
            print(f"Warning: Could not configure pacman.conf: {e}")

    def setup_initial_mirrors(self):
        print("Setting up reliable mirrors for installation...")
        try:
            subprocess.run(["pacman", "-S", "--noconfirm", "reflector"], check=False)
            
            subprocess.run([
                "reflector",
                "--latest", "10",
                "--protocol", "https",
                "--sort", "rate",
                "--save", "/etc/pacman.d/mirrorlist"
            ], check=False)
            
            subprocess.run(["pacman", "-Syy", "--noconfirm"], check=False)
            print("Mirrors updated successfully.")
        except Exception as e:
            print(f"Warning: Could not setup mirrors with reflector: {e}")
            print("Falling back to default mirrors...")
            
    def disks(self):
        self.cleanup_mounts()
        print("Available disks:")
        self.run_command("lsblk -d -n -o NAME,SIZE,MODEL | grep -v 'loop'", shell=True)
        disk_input = input("\nEnter the disk to begin with the installation process (e.g., sda, vda, nvme0n1): ").strip()
        if disk_input.startswith("/dev/"):
            disk_input = disk_input[5:]
        self.disk = "/dev/" + disk_input
        
        if self.disk[-1].isdigit():
            part1 = self.disk + "p1"
            part2 = self.disk + "p2"
        else:
            part1 = self.disk + "1"
            part2 = self.disk + "2"
            
        # Formatting the disks
        self.run_command(["parted", "-s", self.disk, "mklabel", "gpt"])
        self.run_command(["parted", "-s", self.disk, "mkpart", "EFI", "fat32", "1MiB", "1G"])
        self.run_command(["parted", "-s", self.disk, "set", "1", "esp", "on"])
        self.run_command(["parted", "-s", self.disk, "mkpart", "primary", "ext4", "1G", "100%"])
        self.run_command(["mkfs.fat", "-F32", part1])
        self.run_command(["mkfs.ext4", "-F", part2])
        
        self.run_command(["mount", part2, "/mnt"])
        self.run_command(["mkdir", "-p", "/mnt/boot"])
        self.run_command(["mount", part1, "/mnt/boot"])
        
    def mirrors_setup(self):
        try:
            import mirrors.blackarch.strap as blackarch
            blackarch.nalca_install()
        except ImportError as e:
            print(f"\033[1;31m[!] ERROR: Failed to import BlackArch setup: {e}\033[0m", file=sys.stderr)
            
        try:
            import mirrors.cachyos.mirrors as cachyos
            cachyos.nalca_install()
        except ImportError as e:
            print(f"\033[1;31m[!] ERROR: Failed to import CachyOS setup: {e}\033[0m", file=sys.stderr)
    
    def install_base(self):
        cpu, gpu = None, None
        
        while cpu not in ["1", "2"]:
            cpu = input("Enter your CPU brand:\n1) Intel\n2) AMD\n").strip()
        match cpu:
            case "1":
                cpu = "intel-ucode"
            case "2":
                cpu = "amd-ucode"
        
        while gpu not in ["1", "2", "3", "4"]:
            gpu = input("Enter your GPU brand:\n1) Intel\n2) AMD\n3) NVIDIA\n4) Virtual/Generic (for VMs)\n").strip()
        match gpu:
            case "1":
                gpu = "mesa xf86-video-intel vulkan-intel"
            case "2":
                gpu = "mesa xf86-video-amdgpu vulkan-radeon"
            case "3":
                gpu = "nvidia-dkms nvidia-utils"
            case "4":
                gpu = "mesa"
        
        if self.is_vm:
            pkgs = f"base base-devel git curl wget networkmanager sudo vim nano openssh python {cpu} {gpu} "
        else:
            pkgs = f"base linux-firmware base-devel git curl wget networkmanager sudo vim nano openssh python {cpu} {gpu} "
        
        print(f"Installing base packages: {pkgs}")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.run_command(["pacstrap", "-K", "/mnt"] + pkgs.strip().split())
                break
            except SystemExit:
                if attempt < max_retries - 1:
                    print(f"\nRetrying installation (attempt {attempt + 2}/{max_retries})...")
                    self.setup_initial_mirrors()
                else:
                    print("\nFailed to install packages after multiple attempts.")
                    sys.exit(1)
        self.run_command("genfstab -U /mnt >> /mnt/etc/fstab", shell=True)
        
    def arch_chroot(self):
        # Setting timezone and hardware clock
        self.run_command(["arch-chroot", "/mnt", "ln", "-sf", "/usr/share/zoneinfo/America/Santiago", "/etc/localtime"])
        self.run_command(["arch-chroot", "/mnt", "hwclock", "--systohc"])
        
        # Setting up locales and hostname
        self.run_command(["arch-chroot", "/mnt", "sed", "-i", f"s/#{self.locale} UTF-8/{self.locale} UTF-8/", "/etc/locale.gen"])
        self.run_command(["arch-chroot", "/mnt", "locale-gen"])
        self.run_command(f"echo LANG={self.locale} > /mnt/etc/locale.conf", shell=True)
        self.run_command(f"echo KEYMAP={self.keymap} > /mnt/etc/vconsole.conf", shell=True)
        self.run_command("echo NalcaOS > /mnt/etc/hostname", shell=True)
        
        # Setting root password and creating user
        self.run_command(f"echo 'root:{self.password}' | arch-chroot /mnt chpasswd", shell=True)
        self.run_command(["arch-chroot", "/mnt", "useradd", "-m", "-G", "wheel", self.user])
        self.run_command(f"echo '{self.user}:{self.password}' | arch-chroot /mnt chpasswd", shell=True)
        self.run_command(["arch-chroot", "/mnt", "sed", "-i", "s/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/", "/etc/sudoers"])
        self.run_command(["arch-chroot", "/mnt", "sed", "-i", "s/^# %wheel ALL=(ALL) ALL/%wheel ALL=(ALL) ALL/", "/etc/sudoers"])
        
        # Give NOPASSWD temporarily so blackarch, cachy-mirrors and yay can install dependencies non-interactively
        self.run_command("echo '%wheel ALL=(ALL) NOPASSWD: ALL' > /mnt/etc/sudoers.d/99-installer-nopasswd", shell=True)
        self.run_command(["arch-chroot", "/mnt", "chmod", "440", "/etc/sudoers.d/99-installer-nopasswd"])
        
        # this section goes as try-except to avoid breaking the installer if the process fails, allowing the user to continue with the installation.
        
        # Install BlackArch repo
        try:
            import mirrors.blackarch.strap as blackarch
            blackarch.nalca_install(user = self.user)
        except ImportError as e:
            print(f"\033[1;31m[!] ERROR: Failed to import BlackArch setup: {e}\033[0m", file=sys.stderr)
            
        # Install CachyOS repo and LTS kernel
        try:
            import mirrors.cachyos.mirrors as cachyos
            cachyos.nalca_install(user = self.user)
            self.run_command(["arch-chroot", "/mnt", "pacman", "-S", "--noconfirm", "linux-cachyos-lts", "linux-cachyos-lts-headers"])
            
        except ImportError as e:
            print(f"\033[1;31m[!] ERROR: Failed to import CachyOS setup: {e}\033[0m", file=sys.stderr)

        
        # Adding multilib support to pacman.conf
        try:   
            self.run_command(["cp", os.path.join(self.working_dir, "pacman.py"), os.path.join("/mnt", "home", self.user, "pacman.py")])
            
        except Exception as e:
            print(f"\033[1;31m[!] ERROR: Failed to copy pacman.py: {e}\033[0m", file=sys.stderr)

        try:
            self.run_command(["arch-chroot", "/mnt", "python3", f"/home/{self.user}/pacman.py"])
            self.run_command(["arch-chroot", "/mnt", "pacman", "-Syu", "--noconfirm"])
            self.run_command(["arch-chroot", "/mnt", "rm", f"/home/{self.user}/pacman.py"])
        except Exception as e:
            print(f"\033[1;31m[!] ERROR: Failed to run pacman.py: {e}\033[0m", file=sys.stderr)
        
        
        # Setting up bootloader (GRUB)
        try:
            self.run_command(["arch-chroot", "/mnt", "pacman", "-S", "--noconfirm", "grub", "efibootmgr"])
            if self.is_vm:
                # For VMs, try UEFI first, fallback to BIOS if it fails
                try:
                    self.run_command(["arch-chroot", "/mnt", "grub-install", "--target=x86_64-efi", "--efi-directory=/boot", "--bootloader-id=GRUB"])
                except SystemExit:
                    print("UEFI boot failed, trying BIOS/legacy mode...")
                    self.run_command(["arch-chroot", "/mnt", "grub-install", "--target=i386-pc", self.disk])
            else:
                self.run_command(["arch-chroot", "/mnt", "grub-install", "--target=x86_64-efi", "--efi-directory=/boot", "--bootloader-id=GRUB"])
            self.run_command(["arch-chroot", "/mnt", "grub-mkconfig", "-o", "/boot/grub/grub.cfg"])
        except Exception as e:
            print(f"\033[1;31m[!] ERROR: Failed to install GRUB: {e}\033[0m", file=sys.stderr)
        
        # Install yay
        try:
            yay_path = os.path.abspath(os.path.join(self.binaries_dir, "yay.pkg.tar.zst"))
            dest_path = os.path.join("/mnt", "home", self.user, "yay.pkg.tar.zst")
            os.makedirs(os.path.join("/mnt", "home", self.user), exist_ok=True)
            
            self.run_command(["cp", yay_path, dest_path])
            self.run_command(["arch-chroot", "/mnt", "pacman", "-U", "--noconfirm", dest_path.replace("/mnt", "")])
            self.run_command(["arch-chroot", "/mnt", "rm", dest_path.replace("/mnt", "")])
        except Exception as e:
            print(f"\033[1;31m[!] ERROR: Failed to install yay: {e}\033[0m", file=sys.stderr)

        # Install PortProton
        try:
            portproton_path = os.path.abspath(os.path.join(self.binaries_dir, "portproton.pkg.tar.zst"))
            dest_path = os.path.join("/mnt", "home", self.user, "portproton.pkg.tar.zst")
            os.makedirs(os.path.join("/mnt", "home", self.user), exist_ok=True)
            
            self.run_command(["cp", portproton_path, dest_path])
            self.run_command(["arch-chroot", "/mnt", "pacman", "-U", "--noconfirm", dest_path.replace("/mnt", "")])
            self.run_command(["arch-chroot", "/mnt", "rm", dest_path.replace("/mnt", "")])
        except Exception as e:
            print(f"\033[1;31m[!] ERROR: Failed to install PortProton: {e}\033[0m", file=sys.stderr)

        # Install simplexampp
        try:
            pkg_path = os.path.abspath(os.path.join(self.binaries_dir, "simplexampp.pkg.tar.zst"))
            dest_path = os.path.join("/mnt", "home", self.user, "simplexampp.pkg.tar.zst")
            self.run_command(["cp", pkg_path, dest_path])
            self.run_command(["arch-chroot", "/mnt", "pacman", "-U", "--noconfirm", dest_path.replace("/mnt", "")])
            self.run_command(["arch-chroot", "/mnt", "rm", dest_path.replace("/mnt", "")])
        except Exception as e:
            print(f"\033[1;31m[!] ERROR: Failed to install simplexampp: {e}\033[0m", file=sys.stderr)

        # Remove NOPASSWD from sudoers
        try:
            self.run_command(["arch-chroot", "/mnt", "rm", "/etc/sudoers.d/99-installer-nopasswd"])
        except Exception as e:
            print(f"\033[1;31m[!] ERROR: Failed to remove NOPASSWD from sudoers: {e}\033[0m", file=sys.stderr)

        # Enable services
        self.run_command(["arch-chroot", "/mnt", "systemctl", "enable", "NetworkManager"])
        self.run_command(["arch-chroot", "/mnt", "systemctl", "enable", "sshd"])

    def setup_secureboot(self):
        print("Setting up Secure Boot...")
        try:
            self.run_command(["arch-chroot", "/mnt", "pacman", "-S", "--noconfirm", "sbctl"])
            self.run_command(["arch-chroot", "/mnt", "sbctl", "create-keys"])
            
            try:
                self.run_command(["arch-chroot", "/mnt", "sbctl", "enroll-keys", "-m"])
            except Exception as e:
                print(f"Warning: Could not enroll keys (system might not be in Setup Mode): {e}")
                
            # Sign the bootloader
            try:
                self.run_command(["arch-chroot", "/mnt", "sbctl", "sign", "-s", "/boot/EFI/GRUB/grubx64.efi"])
            except Exception as e:
                print(f"Warning: Could not sign GRUB: {e}")
                
            # Sign the kernel
            try:
                run_command(["arch-chroot", "/mnt", "bash", "-c", "for kernel in /boot/vmlinuz-*; do sbctl sign -s \"$kernel\"; done"])
            except Exception as e:
                print(f"Warning: Could not sign kernel(s): {e}")
                
            # Verify status
            run_command(["arch-chroot", "/mnt", "sbctl", "status"])
            print("Secure Boot setup completed.")
            
        except Exception as e:
            print(f"\033[1;31m[!] ERROR: Failed to setup secure boot: {e}\033[0m", file=sys.stderr)


    def select_keyboard(self):
        keyboards = {
            "1": ("Español", "es", "es_ES.UTF-8"),
            "2": ("Latinoamericano", "latam", "es_LA.UTF-8"),
            "3": ("Inglés USA", "us", "en_US.UTF-8")
        }

        print("\nSelect your keyboard layout:")
        for key, value in keyboards.items():
            print(f"{key}) {value[0]}")

        choice = ""
        while choice not in keyboards:
            choice = input("Selection (1-3): ").strip()

        selected = keyboards[choice]
        self.keymap = selected[1]
        self.locale = selected[2]
        print(f"Keyboard set to: {selected[0]} ({self.keymap})")

    def install_desktop(self):
        kde_plasma = ["plasma", "sddm", "konsole", "dolphin"]
        gnome = ["gnome", "gdm"]
        xfce = ["xfce4", "xfce4-goodies", "lightdm", "lightdm-gtk-greeter"]
        cinnamon = ["cinnamon", "nemo", "lightdm", "lightdm-gtk-greeter"]
        mate = ["mate", "mate-extra", "lightdm", "lightdm-gtk-greeter"]
        lxqt = ["lxqt", "sddm"]
        lxde = ["lxde", "lxdm"]
        budgie = ["budgie-desktop", "lightdm", "lightdm-gtk-greeter"]
        deepin = ["deepin", "deepin-extra", "lightdm", "lightdm-gtk-greeter"]
        pantheon = ["pantheon", "lightdm", "pantheon-lightdm-greeter"]
        enlightenment = ["enlightenment", "terminology", "lightdm", "lightdm-gtk-greeter"]
        trinity = ["tde-meta", "tdm"]
        cosmic = ["cosmic-session", "cosmic-greeter"]

        hyprland = ["hyprland", "kitty", "waybar", "sddm", "wofi", "rofi", "swaybg"]
        sway = ["sway", "swaybg", "swaylock", "swayidle", "waybar", "sddm", "alacritty", "dmenu"]
        river = ["river", "foot", "waybar", "swaybg", "wofi"]
        wayfire = ["wayfire", "wayfire-plugins-extra", "alacritty", "wofi", "waybar"]
        labwc = ["labwc", "foot", "waybar", "swaybg", "wofi"]
        niri = ["niri", "waybar", "alacritty", "fuzzel"]
        cage = ["cage", "alacritty"]
        hikari = ["hikari", "alacritty", "waybar"]

        i3 = ["i3-wm", "i3status", "i3lock", "dmenu", "alacritty", "lightdm", "lightdm-gtk-greeter"]
        bspwm = ["bspwm", "sxhkd", "polybar", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
        awesome = ["awesome", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
        xmonad = ["xmonad", "xmonad-contrib", "xmobar", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
        qtile = ["qtile", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
        dwm = ["dwm", "dmenu", "st", "lightdm", "lightdm-gtk-greeter"]
        openbox = ["openbox", "obconf", "tint2", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
        icewm = ["icewm", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
        fluxbox = ["fluxbox", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
        herbstluftwm = ["herbstluftwm", "dmenu", "alacritty", "lightdm", "lightdm-gtk-greeter"]
        spectrwm = ["spectrwm", "dmenu", "alacritty", "lightdm", "lightdm-gtk-greeter"]
        jwm = ["jwm", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
        dk = ["dk", "sxhkd", "polybar", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
        stumpwm = ["stumpwm", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]

        desktops = {
            "1": ("KDE Plasma", kde_plasma, "sddm"),
            "2": ("GNOME", gnome, "gdm"),
            "3": ("XFCE", xfce, "lightdm"),
            "4": ("Cinnamon", cinnamon, "lightdm"),
            "5": ("MATE", mate, "lightdm"),
            "6": ("LXQt", lxqt, "sddm"),
            "7": ("LXDE", lxde, "lxdm"),
            "8": ("Budgie", budgie, "lightdm"),
            "9": ("Deepin", deepin, "lightdm"),
            "10": ("Hyprland", hyprland, "sddm"),
            "11": ("Sway", sway, "sddm"),
            "12": ("i3-wm", i3, "lightdm"),
            "13": ("bspwm", bspwm, "lightdm"),
            "14": ("Awesome", awesome, "lightdm"),
            "15": ("xmonad", xmonad, "lightdm"),
            "16": ("qtile", qtile, "lightdm"),
            "17": ("dwm", dwm, "lightdm"),
            "18": ("None (TTY only)", None, None)
        }

        def de_select():
            de = None
            options = list(desktops.keys())
            
            while de not in options:
                print("\nSelect your Desktop Environment or Window Manager:")
                for key, value in desktops.items():
                    print(f"{key}) {value[0]}")
                de = input(f"Selection (1-{len(options)}): ").strip()
            
            selected_de = desktops[de]
            if selected_de[1] is None:
                return None, None
            
            return " ".join(selected_de[1]), selected_de[2]

        try:
            desktop_packages, display_manager = de_select()
            self.run_command(["arch-chroot", "/mnt", "pacman", "-S", "--noconfirm"] + desktop_packages.split())
            if display_manager:
                self.run_command(["arch-chroot", "/mnt", "systemctl", "enable", display_manager])
        except Exception as e:
            print(f"\033[1;31m[!] ERROR: Failed to install desktop environment: {e}\033[0m", file=sys.stderr)

    def run(self):
        self.configure_pacman()
        self.select_environment()
        self.setup_initial_mirrors()
        self.disks()
        self.install_base()
        self.select_keyboard()
        self.arch_chroot()
        self.mirrors_setup()
        self.install_desktop()
        print("Installation complete! Reboot your system and remove the installation media.")