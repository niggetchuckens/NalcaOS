def base_config(run_command: function, user: str, password: str):
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
    
    # Give NOPASSWD temporarily so blackarch, cachy-mirrors and yay can install dependencies non-interactively
    run_command("echo '%wheel ALL=(ALL) NOPASSWD: ALL' > /mnt/etc/sudoers.d/99-installer-nopasswd", shell=True)
    run_command(["arch-chroot", "/mnt", "chmod", "440", "/etc/sudoers.d/99-installer-nopasswd"])
    
    # Install BlackArch repo
    try:
        import mirrors.blackarch.strap as blackarch
        blackarch.nalca_install()
    except ImportError as e:
        print(f"\033[1;31m[!] ERROR: Failed to import BlackArch setup: {e}\033[0m", file=sys.stderr)
        
    # Install CachyOS repo and LTS kernel
    try:
        import mirrors.cachyos.mirrors as cachyos
        cachyos.nalca_install()
        run_command(["arch-chroot", "/mnt", "pacman", "-S", "--noconfirm", "linux-cachyos-lts", "linux-cachyos-lts-headers"])
        
    except ImportError as e:
        print(f"\033[1;31m[!] ERROR: Failed to import CachyOS setup: {e}\033[0m", file=sys.stderr)

    
    # Setting up bootloader (GRUB)
    run_command(["arch-chroot", "/mnt", "pacman", "-S", "--noconfirm", "grub", "efibootmgr"])
    run_command(["arch-chroot", "/mnt", "grub-install", "--target=x86_64-efi", "--efi-directory=/boot", "--bootloader-id=GRUB"])
    run_command(["arch-chroot", "/mnt", "grub-mkconfig", "-o", "/boot/grub/grub.cfg"])
    
    # Install yay
    yay_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "binaries", "built", "yay.pkg.tar.zst"))
    dest_path = os.path.join("/mnt", "home", user, "yay.pkg.tar.zst")
    os.makedirs(os.path.join("/mnt", "home", user), exist_ok=True)
    
    run_command(["cp", yay_path, dest_path])
    
    run_command(["arch-chroot", "/mnt", "pacman", "-U", "--noconfirm", dest_path.replace("/mnt", "")])
    run_command(["arch-chroot", "/mnt", "rm", dest_path.replace("/mnt", "")])
    
    # Install PortProton
    # portproton_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "binaries", "built", "portproton.pkg.tar.zst"))
    # dest_path = os.path.join("/mnt", "home", user, "portproton.pkg.tar.zst")
    # os.makedirs(os.path.join("/mnt", "home", user), exist_ok=True)
    
    # run_command(["cp", portproton_path, dest_path])
    # run_command(["arch-chroot", "/mnt", "pacman", "-U", "--noconfirm", dest_path.replace("/mnt", "")])
    # run_command(["arch-chroot", "/mnt", "rm", dest_path.replace("/mnt", "")])
    
    # Remove NOPASSWD from sudoers
    run_command(["arch-chroot", "/mnt", "rm", "/etc/sudoers.d/99-installer-nopasswd"])
    
    # Install DE
    de_pkgs, dm_service = de_select()
    if de_pkgs is not None and dm_service is not None:
        print(f"\nInstalling Desktop Environment / Window Manager...")
        run_command(["arch-chroot", "/mnt", "pacman", "-S", "--noconfirm", de_pkgs.strip().split()])
        run_command(["arch-chroot", "/mnt", "systemctl", "enable", dm_service])
    
    # Enable services
    run_command(["arch-chroot", "/mnt", "systemctl", "enable", "NetworkManager"])
    run_command(["arch-chroot", "/mnt", "systemctl", "enable", "sshd"])
