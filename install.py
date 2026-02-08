import os
import sys
import subprocess

def run_command(command):
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(result.stdout.decode())
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr.decode()}")
        sys.exit(1)
             
def install_packages():
    pkgs = (
        "btop python3-virtualenv openssh-server openssh-client flatpak"
        "git curl wget unzip"
            )
    flat_pkgs = (
        "ru.linux_gaming.PortProton com.visualstudio.code org.onlyoffice.desktopeditors"
        ""
        )
    
    flatpak_cfg = run_command("sudo flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo")
        
        
def setup_proteus():
    print("Setting up Apps...")
    run_command("cd ~")
    run_command("curl minio.niggetchuckens.online/api/v1/buckets/nalcaos/objects/download?prefix=proteus.tar.gz -o proteus.tar.gz")
    run_command("tar -xzf proteus.tar.gz")
    run_command("rm proteus.tar.gz")
    run_command("mv proteus ~/.local/share/applications/proteus")
    run_command("touch ~/.local/share/applications/proteus.desktop && chmod +x ~/.local/share/applications/proteus.desktop")
    # get the user's home directory
    home_dir = os.path.expanduser("/home")
    # create the .local/share/applications directory if it doesn't exist
    os.makedirs(os.path.join(home_dir, ".local/share/applications"), exist_ok=True)
    # create the desktop entry for Proteus dinamically
    run_command(f"echo '[Desktop Entry]\nName=Proteus\nExec=flatpak run ru.linux_gaming.PortProton \"{home_dir}/proteus/BIN/ISIS.EXE\"\nType=Application\nCategories=Development\nStartupNotify=true' > ~/.local/share/applications/proteus.desktop")


def main():
    print("Installing dependencies...")
    
    print("Setting up the application...")
    # Add any additional setup steps here, such as creating config files or directories
    
    print("Installation complete!")