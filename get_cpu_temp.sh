#!/bin/bash
# Example script to output CPU temperature in line protocol format

# Get the CPU temperature and convert to Celsius
cpu_temp=$(cat /sys/class/thermal/thermal_zone0/temp)
cpu_temp=$(echo "scale=1; $cpu_temp / 1000" | bc) # Correct division using bc

# Output in line protocol format
echo "cpu_temp,sensor=cpu value=${cpu_temp}"