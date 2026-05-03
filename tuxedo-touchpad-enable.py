#!/usr/bin/env python3
import fcntl, ctypes, struct, time, sys

def _IOC(direction, type_, nr, size):
    return (direction << 30) | (size << 16) | (type_ << 8) | nr

ptr_size = ctypes.sizeof(ctypes.c_void_p)
W_CL_TOUCHPAD_SW = _IOC(1, 0xEE, 0x14, ptr_size)

for _ in range(5):
    try:
        fd = open("/dev/tuxedo_io", "rb+", buffering=0)
        buf = ctypes.create_string_buffer(struct.pack("i", 1) + b"\x00" * 4)
        fcntl.ioctl(fd, W_CL_TOUCHPAD_SW, buf)
        fd.close()
        print("touchpad enabled")
        sys.exit(0)
    except Exception as e:
        time.sleep(1)

print("failed to enable touchpad")
sys.exit(1)
