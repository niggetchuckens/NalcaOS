#!/bin/bash

USER_HOME=/home/$USER
WORKING_DIR=/home/$USER/Downloads

user_to_sudoers(){
    su -c "echo '$USER ALL=(ALL:ALL) ALL' > /etc/sudoers.d/$USER && \
    chmod 440 /etc/sudoers.d/$USER"
}

install_pkgs(){
    echo "Installing needed packages..."
    apt install btop python3-virtualenv openssh-server openssh-client flatpak git curl wget unzip -y

    echo "Setting up flatpak repo..."
    flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

    echo "Installing flatpak apps..."
    flatpak install ru.linux_gaming.PortProton com.visualstudio.code org.onlyoffice.desktopeditors
}

install_proteus(){    
    cd ~
    curl minio-api.niggetchuckens.online/nalcaos/proteus.tar.gz -o $WORKING_DIR/proteus.tar.gz
    tar -xzf $WORKING_DIR/proteus.tar.gz
    rm $WORKING_DIR/proteus.tar.gz
    mv $WORKING_DIR/proteus $USER_HOME/.local/share/applications/proteus
    touch $USER_HOME/.local/share/applications/proteus.desktop
    chmod +x $USER_HOME/.local/share/applications/proteus.desktop

    echo '[Desktop Entry]\n
    Name=Proteus\n
    Exec=flatpak run ru.linux_gaming.PortProton "/home/'$USER'/proteus/BIN/ISIS.EXE\"\n
    Type=Application\nCategories=Development\n
    StartupNotify=true' > ~/.local/share/applications/proteus.desktop
}

install_xampp(){
    curl minio-api.niggetchuckens.online/nalcaos/xampp.run -o $WORKING_DIR/xampp.run
    chmod +x $WORKING_DIR/xampp.run
    sudo $WORKING_DIR/xampp.run --mode unattended
    rm $WORKING_DIR/xampp.run
}

install_cisco(){
    curl minio-api.niggetchuckens.online/nalcaos/CISCO.deb -o $WORKING_DIR/cisco.deb
    sudo apt install $WORKING_DIR/cisco.deb -y
    rm $WORKING_DIR/cisco.deb
}

if [[ $EUID -e 0  ]]; then
    # Debian apps
    install_pkgs

    # Custom apps
    install_proteus
    install_xampp
    install_cisco
    exit 1
fi

user_to_sudoers()
echo "Run script as sudo!"