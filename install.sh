#!/bin/bash
mkdir -pv nalcaos && cd nalcaos

URL="http://minio-api.hime-code.xyz/nalcaos"
FILES=$(curl -sS $URL)

echo "Downloading needed packages..."

echo "$FILES" | grep -oP '(?<=<Key>).*?(?=</Key>)' | while read -r ITEM; do
    echo "Downloading $ITEM..."
    curl -sS --create-dirs "$URL/$ITEM" -o "$ITEM" 
done

python3 main.py