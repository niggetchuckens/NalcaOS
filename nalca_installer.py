import sys
import subprocess
import argparse
from unittest import case

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
    disk = "/dev/" + input("\nEnter the disk to begin with the installation process: ").strip()
    if not "nvme" in disk:
        part1 = disk + "1"
        part2 = disk + "2"
    else:
        part1 = disk + "p1"
        part2 = disk + "p2"
        
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
    
    pkgs = f"base linux-firmware base-devel git networkmanager sudo {cpu} {gpu} "
    
    if use_cachyos:
        pkgs += "linux-cachyos-lts linux-cachyos-lts-headers cachyos-keyring cachyos-mirrorlist "
    else:
        pkgs += "linux linux-headers "
    
    print(f"Installing base packages: {pkgs}")
    run_command(["pacstrap", "-K", "/mnt"] + pkgs.strip().split())
    run_command(["genfstab", "-U", "/mnt", ">>", "/mnt/etc/fstab"])

def base_config(user: str, password: str):
    # Setting timezone and hardware clock
    run_command(["arch-chroot", "/mnt", "ln", "-sf", "/usr/share/zoneinfo/America/Santiago", "/etc/localtime"])
    run_command(["arch-chroot", "/mnt", "hwclock", "--systohc"])
    
    # Setting up locales and hostname
    run_command(["arch-chroot", "/mnt", "sed", "-i", "s/#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/", "/etc/locale.gen"])
    run_command(["arch-chroot", "/mnt", "locale-gen"])
    run_command(["arch-chroot", "/mnt", "echo", "LANG=en_US.UTF-8", ">", "/etc/locale.conf"])
    run_command(["arch-chroot", "/mnt", "echo", "KEYMAP=us", ">", "/etc/vconsole.conf"])
    run_command(["arch-chroot", "/mnt", "echo", "NalcaOS", ">", "/etc/hostname"])
    
    # Setting root password and creating user
    run_command(["arch-chroot", "/mnt", "echo -e '", f"root:{password}" "', | chpasswd"])
    run_command(["arch-chroot", "/mnt", "useradd", "-m", "-G", "wheel", user])
    run_command(["arch-chroot", "/mnt", "echo -e '", f"{user}:{password}" "', | chpasswd"])
    run_command(["arch-chroot", "/mnt", "sed", "-i", "s/# %wheel ALL=(ALL) ALL/%wheel ALL=(ALL) ALL/", "/etc/sudoers"])
    
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NalcaOS Base Installer")
    parser.add_argument("--cachyos", action="store_true", help="Setup CachyOS repos and install CachyOS LTS kernel")
    args = parser.parse_args()
    
    install_base(use_cachyos=args.cachyos)