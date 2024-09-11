#!/bin/bash
# Example script to output CPU temperature in line protocol format

# Get the CPU temperature and convert to Celsius
cpu_temp=$(cat /sys/class/thermal/thermal_zone0/temp)
cpu_temp=$(echo "$cpu_temp / 1000" | awk '{print $1}') # Convert to Celsius using awk

# Output in line protocol format
echo "cpu_temp,sensor=cpu value=${cpu_temp}"