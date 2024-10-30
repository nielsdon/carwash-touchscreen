#!/bin/bash

# Wait until eth0 is up
while ! ip link show eth0 | grep "state UP"; do
  echo "Waiting for network interface to be up..."
  sleep 5
done

# Network is up, proceed with the rest of the script
echo "Network is up, continuing with updates..."

# Loop until GitHub is reachable
while ! curl -s https://github.com > /dev/null; do
    echo "Waiting for GitHub to become available..."
    sleep 5  # Wait for 5 seconds before trying again
done
echo "GitHub is available!"

# Set the project and branch variables
project='carwash-touchscreen'

CONFIG_FILE="config.ini"

# Check if testMode is True
TEST_MODE=$(grep -E '^testMode=True' "$CONFIG_FILE")

if [ "$TEST_MODE" ]; then
  # Set the branch variable to 'develop'
  branch="develop"
  unset KIVY_NO_FILELOG  # Disable file logging
  unset KIVY_NO_CONSOLELOG  # Enable console logging
  unset KIVY_LOG_LEVEL  # Set log level to debug (all messages will be shown)
  curl -L -o archive.tar.gz https://github.com/nielsdon/${project}/archive/refs/heads/${branch}.tar.gz
  tar -xvf archive.tar.gz --strip-components=1 
  pip install --upgrade pip 
  pip install -r requirements.txt
else
  # Set the branch variable to some default value or leave it empty
  branch="main"  # or set to "" if you prefer
  export KIVY_NO_FILELOG=1  # Disable file logging
  export KIVY_NO_CONSOLELOG=1  # Disable console logging
  export KIVY_LOG_LEVEL=error  # Set log level to error (only error messages will be shown)
  curl -sS -L -o archive.tar.gz https://github.com/nielsdon/${project}/archive/refs/heads/${branch}.tar.gz
  tar -xvf archive.tar.gz --strip-components=1 > /dev/null 2>&1
  pip install --upgrade pip > /dev/null 2>&1
  pip install -r requirements.txt > /dev/null 2>&1
fi

# Clean up
rm archive.tar.gz

# ensure correct permissions are set
chmod a+x *.sh