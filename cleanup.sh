#!/bin/bash

# Step 1: Save currently installed packages
pip freeze > installed_packages.txt

# Step 2: Generate new requirements based on project imports
pipreqs . --force

# Step 3: Find unused packages
comm -23 <(sort installed_packages.txt) <(sort ./requirements.txt) > unused_packages.txt

# Step 4: Uninstall unused packages
pip uninstall -r unused_packages.txt -y

# Cleanup
rm installed_packages.txt unused_packages.txt