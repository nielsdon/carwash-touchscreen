#!/bin/bash

# Check if vendor:product ID is passed as an argument
if [ $# -ne 1 ]; then
  echo "Usage: $0 <vendor_id:product_id>"
  exit 1
fi

# Split the input parameter into vendor and product ID
IFS=':' read -r VENDOR_ID PRODUCT_ID <<< "$1"

# Find the matching event device
for event in /dev/input/event*; do
    # Skip if udevadm fails (e.g., incompatible device)
    if ! udevadm info --query=all --name=$event >/dev/null 2>&1; then
        continue
    fi
    
    # Check for matching vendor and product ID
    if udevadm info --query=all --name=$event | grep -q "ID_VENDOR_ID=$VENDOR_ID" && \
       udevadm info --query=all --name=$event | grep -q "ID_MODEL_ID=$PRODUCT_ID"; then
        echo $event
        exit 0
    fi
done

echo "No matching device found."
exit 1