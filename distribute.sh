#!/bin/bash

# Source and destination directories
SOURCE_DIR="/Users/nielsdonninger/Git Repositories/carwash-touchscreen"
DEST_DIR="/Users/nielsdonninger/Git Repositories/carwash-touchscreen-dist"

# Create the destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Copy all files to the destination directory, excluding 'env' directory
rsync -av --progress --exclude 'env' --exclude 'distribute.sh' "$SOURCE_DIR"/* "$DEST_DIR"

# Initialize Pyarmor project in the destination directory
pyarmor gen -O "$DEST_DIR/obf"

# Obfuscate Python files in the destination directory, excluding 'env' directory
find "$DEST_DIR" -type f -name "*.py" ! -path "*/env/*" | while read -r file; do
    # Create a temporary obfuscation directory
    obf_dir="$(dirname "$file")/obf"
    mkdir -p "$obf_dir"
    
    # Obfuscate the file
    pyarmor gen -i "$file" -O "$obf_dir"
    
    # Move the obfuscated file back and handle potential conflicts
    obf_file="$obf_dir/$(basename "$file")"
    if [ -f "$obf_file" ]; then
        mv -f "$obf_file" "$file"
    fi
    
    # Clean up temporary obfuscation directory
    rm -rf "$obf_dir"
done

echo "Project copied and Python files obfuscated successfully."