def install_base(run_command: function):
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
    run_command(["pacstrap", "-K", "/mnt"] + pkgs.strip().split())
    run_command("genfstab -U /mnt >> /mnt/etc/fstab", shell=True)
