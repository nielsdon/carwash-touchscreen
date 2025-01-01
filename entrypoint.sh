#!/bin/sh

# Ensure framebuffer and input devices have the correct permissions
#if [ -e /dev/fb0 ]; then
    # chmod g+rw /dev/fb0 || echo "Failed to change permissions for /dev/fb0"
#fi

#if ls /dev/input/event* 1> /dev/null 2>&1; then
    # chmod g+rw /dev/input/event* || echo "Failed to change permissions for input devices"
#fi

# Check if 'video' group exists and add root if possible
#if getent group video > /dev/null 2>&1; then
    #echo "Group 'video' already exists"
#else
    # addgroup --gid 44 video || echo "Failed to create group 'video'"
#fi

# usermod -aG video root || echo "Failed to add 'root' to 'video' group"

# Start the application
# exec python3 -d /app/main.py
exec sh