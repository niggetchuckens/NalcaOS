import os
import sys    
import subprocess


class Installer:
    def __init__(self, user: str = None, password: str = None):
        self.user = user or input("Enter your username: ").strip()
        self.password = password or input("Enter your password: ").strip()
        self.working_dir = os.path.dirname(os.path.abspath(__file__))
        self.mirrors_dir = os.path.join(self.working_dir, "mirrors"); sys.path.append(self.mirrors_dir)
        self.binaries_dir = os.path.join(self.working_dir, "..", "binaries", "built")
        print(f"Working directory: {self.working_dir}") 
        
    def run_command(self, command, shell=False):
        try:
            subprocess.run(command, shell=shell, check=True)
        except subprocess.CalledProcessError:
            sys.exit(1)
            
    def configure_pacman(self):
        print("Configuring Pacman (Enabling Colors, Parallel Downloads, ILoveCandy and Multilib)...")
        try:
            with open('/etc/pacman.conf', 'r') as f:
                content = f.read()
                
            content = content.replace('#Color', 'Color')
            content = content.replace('#ParallelDownloads', 'ParallelDownloads')
            if 'ILoveCandy' not in content:
                content = content.replace('Color\n', 'Color\nILoveCandy\n')
    
            if '#[multilib]' in content:
                content = content.replace('#[multilib]\n#Include = /etc/pacman.d/mirrorlist', '[multilib]\nInclude = /etc/pacman.d/mirrorlist')
                            
            with open('/etc/pacman.conf', 'w') as f:
                f.write(content)
                
        except Exception as e:
            print(f"Warning: Could not configure pacman.conf: {e}")
            
    def disks(self):
        print("Available disks:")
        self.run_command("lsblk -d -n -o NAME,SIZE,MODEL | grep -v 'loop'", shell=True)
        disk_input = input("\nEnter the disk to begin with the installation process (e.g., sda, nvme0n1): ").strip()
        if disk_input.startswith("/dev/"):
            disk_input = disk_input[5:]
        disk = "/dev/" + disk_input
        
        if disk[-1].isdigit():
            part1 = disk + "p1"
            part2 = disk + "p2"
        else:
            part1 = disk + "1"
            part2 = disk + "2"
            
        # Formatting the disks
        self.run_command(["parted", "-s", disk, "mklabel", "gpt"])
        self.run_command(["parted", "-s", disk, "mkpart", "EFI", "fat32", "1MiB", "1G"])
        self.run_command(["parted", "-s", disk, "set", "1", "esp", "on"])
        self.run_command(["parted", "-s", disk, "mkpart", "primary", "ext4", "1G", "100%"])
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
        
        while gpu not in ["1", "2", "3"]:
            gpu = input("Enter your GPU brand:\n1) Intel\n2) AMD\n3) NVIDIA\n").strip()
        match gpu:
            case "1":
                gpu = "mesa xf86-video-intel vulkan-intel"
            case "2":
                gpu = "mesa xf86-video-amdgpu vulkan-radeon"
            case "3":
                gpu = "nvidia-dkms nvidia-utils"
        
        pkgs = f"base linux-firmware base-devel git curl wget networkmanager sudo vim nano openssh python {cpu} {gpu} "
        
        print(f"Installing base packages: {pkgs}")
        self.run_command(["pacstrap", "-K", "/mnt"] + pkgs.strip().split())
        self.run_command("genfstab -U /mnt >> /mnt/etc/fstab", shell=True)
        
    def arch_chroot(self):
        # Setting timezone and hardware clock
        self.run_command(["arch-chroot", "/mnt", "ln", "-sf", "/usr/share/zoneinfo/America/Santiago", "/etc/localtime"])
        self.run_command(["arch-chroot", "/mnt", "hwclock", "--systohc"])
        
        # Setting up locales and hostname
        self.run_command(["arch-chroot", "/mnt", "sed", "-i", "s/#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/", "/etc/locale.gen"])
        self.run_command(["arch-chroot", "/mnt", "locale-gen"])
        self.run_command("echo LANG=en_US.UTF-8 > /mnt/etc/locale.conf", shell=True)
        self.run_command("echo KEYMAP=us > /mnt/etc/vconsole.conf", shell=True)
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
        
        except Exception as e:
            print(f"\033[1;31m[!] ERROR: Failed to copy pacman.py: {e}\033[0m", file=sys.stderr)
        
        
        # Setting up bootloader (GRUB)
        try:
            self.run_command(["arch-chroot", "/mnt", "pacman", "-S", "--noconfirm", "grub", "efibootmgr"])
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

        # Remove NOPASSWD from sudoers
        try:
            self.run_command(["arch-chroot", "/mnt", "rm", "/etc/sudoers.d/99-installer-nopasswd"])
        except Exception as e:
            print(f"\033[1;31m[!] ERROR: Failed to remove NOPASSWD from sudoers: {e}\033[0m", file=sys.stderr)

        # Enable services
        self.run_command(["arch-chroot", "/mnt", "systemctl", "enable", "NetworkManager"])
        self.run_command(["arch-chroot", "/mnt", "systemctl", "enable", "sshd"])

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
        self.disks()
        self.install_base()
        self.arch_chroot()
        self.mirrors_setup()
        self.install_desktop()
        print("Installation complete! Reboot your system and remove the installation media.")