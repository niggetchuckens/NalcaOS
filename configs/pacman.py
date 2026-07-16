import re


def configure_pacman():
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
    except Exception as e:
        print(f"Warning: Could not configure pacman.conf: {e}")
