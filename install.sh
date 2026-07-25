#!/bin/bash
URL="http://minio-api.hime-code.xyz/nalcaos"

echo "Downloading needed packages..."
if FILES=$(curl -sS $URL); then
    mkdir -pv nalcaos && cd nalcaos
    echo "$FILES" | grep -oP '(?<=<Key>).*?(?=</Key>)' | while read -r ITEM; do
        echo "Downloading $ITEM..."
        curl -sS --create-dirs "$URL/$ITEM" -o "$ITEM" 
    done
else
    pacman -Sy --noconfirm git
    git clone https://github.com/niggetchuckens/nalcaos
    cd nalcaos 
fi
python3 main.py && rm -rf nalcaos && umount -R /mnt && reboot now