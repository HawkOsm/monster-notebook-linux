#!/bin/bash
# Feed the NVIDIA dGPU temperature to the tuxedo_abra_fan hwmon driver so
# TUXEDO Control Center can show the GPU fan/temp card.
#
# Skips nvidia-smi entirely while the dGPU is runtime-suspended (polling
# would wake it and hurt battery life); the driver expires the value after
# 15 s, so the GPU card in TCC disappears while the GPU sleeps - which is
# accurate.

ATTR=/sys/devices/platform/abra_fan/gpu_temp
GPU_PCI=/sys/bus/pci/devices/0000:01:00.0

while true; do
    if [[ -w $ATTR ]]; then
        if [[ "$(cat "$GPU_PCI/power/runtime_status" 2>/dev/null)" == "active" ]]; then
            t=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -1)
            [[ $t =~ ^[0-9]+$ ]] && echo "$t" > "$ATTR"
        fi
    fi
    sleep 5
done
