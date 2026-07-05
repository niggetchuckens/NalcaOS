import sys
import subprocess
import argparse

def run_command(command, shell=False):
    try:
        result = subprocess.run(command, shell=shell, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.stdout:
            print(result.stdout.decode().strip())
    except subprocess.CalledProcessError as e:
        if e.stderr:
            print(f"Error: {e.stderr.decode().strip()}")
        sys.exit(1)
             
def set_disks():              
    print("Available disks:")
    run_command("lsblk -d -n -o NAME,SIZE,MODEL | grep -v 'loop'", shell=True)
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
    run_command(["parted", "-s", disk, "mklabel", "gpt"])
    run_command(["parted", "-s", disk, "mkpart", "EFI", "fat32", "1MiB", "1G"])
    run_command(["parted", "-s", disk, "set", "1", "esp", "on"])
    run_command(["parted", "-s", disk, "mkpart", "primary", "ext4", "1G", "100%"])
    run_command(["mkfs.fat", "-F32", part1])
    run_command(["mkfs.ext4", "-F", part2])
    
    run_command(["mount", part2, "/mnt"])
    run_command(["mkdir", "-p", "/mnt/boot"])
    run_command(["mount", part1, "/mnt/boot"])
    
    
def install_base(use_cachyos=False):
    if use_cachyos:
        print("Initializing CachyOS repositories...")
        run_command(["python3", "manage_mirrors.py", "setup-live"])
        print("Ranking CachyOS mirrors...")
        run_command(["python3", "manage_mirrors.py", "rank", "--apply", "--top", "5"])

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
    
    if use_cachyos:
        pkgs += "linux-cachyos-lts linux-cachyos-lts-headers cachyos-keyring cachyos-mirrorlist "
    else:
        pkgs += "linux linux-headers "
    
    print(f"Installing base packages: {pkgs}")
    run_command(["pacstrap", "-K", "/mnt"] + pkgs.strip().split())
    run_command("genfstab -U /mnt >> /mnt/etc/fstab", shell=True)

def de_select():
    de = None
    while de not in ["1", "2", "3", "4", "5", "6"]:
        print("\nSelect your Desktop Environment or Window Manager:")
        print("1) KDE Plasma")
        print("2) GNOME")
        print("3) XFCE")
        print("4) Hyprland")
        print("5) Sway")
        print("6) None (TTY only)")
        de = input("Selection (1-6): ").strip()
    
    match de:
        case "1":
            return "plasma sddm konsole dolphin", "sddm"
        case "2":
            return "gnome gdm", "gdm"
        case "3":
            return "xfce4 xfce4-goodies lightdm lightdm-gtk-greeter", "lightdm"
        case "4":
            return "hyprland kitty waybar sddm wofi", "sddm"
        case "5":
            return "sway swaybg swaylock swayidle waybar sddm alacritty dmenu", "sddm"
        case "6":
            return "", None
    

def base_config(user: str, password: str):
    # Setting timezone and hardware clock
    run_command(["arch-chroot", "/mnt", "ln", "-sf", "/usr/share/zoneinfo/America/Santiago", "/etc/localtime"])
    run_command(["arch-chroot", "/mnt", "hwclock", "--systohc"])
    
    # Setting up locales and hostname
    run_command(["arch-chroot", "/mnt", "sed", "-i", "s/#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/", "/etc/locale.gen"])
    run_command(["arch-chroot", "/mnt", "locale-gen"])
    run_command("echo LANG=en_US.UTF-8 > /mnt/etc/locale.conf", shell=True)
    run_command("echo KEYMAP=us > /mnt/etc/vconsole.conf", shell=True)
    run_command("echo NalcaOS > /mnt/etc/hostname", shell=True)
    
    # Setting root password and creating user
    run_command(f"echo 'root:{password}' | arch-chroot /mnt chpasswd", shell=True)
    run_command(["arch-chroot", "/mnt", "useradd", "-m", "-G", "wheel", user])
    run_command(f"echo '{user}:{password}' | arch-chroot /mnt chpasswd", shell=True)
    run_command(["arch-chroot", "/mnt", "sed", "-i", "s/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/", "/etc/sudoers"])
    run_command(["arch-chroot", "/mnt", "sed", "-i", "s/^# %wheel ALL=(ALL) ALL/%wheel ALL=(ALL) ALL/", "/etc/sudoers"])
    
    # Setting up bootloader (GRUB)
    run_command(["arch-chroot", "/mnt", "pacman", "-S", "--noconfirm", "grub", "efibootmgr"])
    run_command(["arch-chroot", "/mnt", "grub-install", "--target=x86_64-efi", "--efi-directory=/boot", "--bootloader-id=GRUB"])
    run_command(["arch-chroot", "/mnt", "grub-mkconfig", "-o", "/boot/grub/grub.cfg"])
    
    # Install yay
    # Give NOPASSWD temporarily so yay can install dependencies non-interactively
    run_command("echo '%wheel ALL=(ALL) NOPASSWD: ALL' > /mnt/etc/sudoers.d/99-installer-nopasswd", shell=True)
    run_command(["arch-chroot", "/mnt", "chmod", "440", "/etc/sudoers.d/99-installer-nopasswd"])
    
    run_command(["arch-chroot", "/mnt", "su", "-", user, "-c", "git clone https://aur.archlinux.org/yay.git ~/yay"])
    run_command(["arch-chroot", "/mnt", "su", "-", user, "-c", "cd ~/yay && makepkg -si --noconfirm"])
    run_command(["arch-chroot", "/mnt", "su", "-", user, "-c", "rm -rf ~/yay"])
    
    run_command("rm /mnt/etc/sudoers.d/99-installer-nopasswd", shell=True)
    
    # Install BlackArch repo
    run_command("arch-chroot /mnt bash -c 'curl -sO https://blackarch.org/strap.sh && chmod +x strap.sh && ./strap.sh && rm strap.sh'", shell=True)
    
    # Install DE
    de_pkgs, dm_service = de_select()
    if de_pkgs:
        print(f"\nInstalling Desktop Environment / Window Manager...")
        run_command(["arch-chroot", "/mnt", "pacman", "-S", "--noconfirm", f"{de_pkgs}"])    

    # Enable services
    run_command(["arch-chroot", "/mnt", "systemctl", "enable", dm_service])
    run_command(["arch-chroot", "/mnt", "systemctl", "enable", "NetworkManager"])
    run_command(["arch-chroot", "/mnt", "systemctl", "enable", "sshd"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NalcaOS Base Installer")
    parser.add_argument("--cachyos", action="store_true", help="Setup CachyOS repos and install CachyOS LTS kernel")
    args = parser.parse_args()
    
    set_disks()
    install_base(use_cachyos=args.cachyos)
    base_config(
        user=input("\nEnter a username for the new user: ").strip(), 
        password=input("Enter a password for the new user: ").strip()
    )
    
    print("\nInstallation Complete!")
    run_command("umount -R /mnt")
    run_command("reboot")