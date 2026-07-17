def set_disks(run_command: function):              
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