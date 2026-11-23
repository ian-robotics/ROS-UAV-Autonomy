#!/usr/bin/env python3
import os
import socket
import time
import sys
import termios
import tty
import select

CAMERA_IP = os.environ.get("GIMBAL_CAMERA_IP", "127.0.0.1")
UDP_PORT = 5000
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def calculate_checksum(cmd):
    crc = 0
    for char in cmd:
        crc += ord(char)
    return f"{crc & 0xFF:02X}"

def send(cmd):
    checksum = calculate_checksum(cmd)
    full_cmd = cmd + checksum
    sock.sendto(full_cmd.encode(), (CAMERA_IP, UDP_PORT))

def set_speed(yaw, pitch):
    """Set the gimbal speed."""
    if yaw != 0:
        if yaw < 0:
            hex_val = f"{(256 + yaw):02X}"
        else:
            hex_val = f"{yaw:02X}"
        send(f"#TPUG2wGSY{hex_val}")
    
    if pitch != 0:
        if pitch < 0:
            hex_val = f"{(256 + pitch):02X}"
        else:
            hex_val = f"{pitch:02X}"
        send(f"#TPUG2wGSP{hex_val}")

# Save terminal settings.
old_settings = termios.tcgetattr(sys.stdin)

try:
    tty.setraw(sys.stdin.fileno())
    
    print("\r================================")
    print("\r      Live Camera Controls")
    print("\r================================")
    print("\rMove: W↑ S↓ A← D→")
    print("\rControls: C to center, Space to stop")
    # Photo and recording controls were removed.
    print("\rZoom: + in, - out")
    print("\rQuit: Q")
    print("\r================================\n")
    print("\rReady...")
    
    while True:
        if select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1)
            
            # Handle uppercase and lowercase keys.
            key_lower = key.lower()
            
            if key_lower == 'q':
                break
            elif key_lower == 'w':
                set_speed(0, 60)
                print("\r↑ Up        ", end="")
            elif key_lower == 's':
                set_speed(0, -60)
                print("\r↓ Down        ", end="")
            elif key_lower == 'a':
                set_speed(-70, 0)
                print("\r← Left        ", end="")
            elif key_lower == 'd':
                set_speed(70, 0)
                print("\r→ Right        ", end="")
            elif key == ' ':
                send("#TPUG2wGSY00")
                send("#TPUG2wGSP00")
                print("\r■ Stop        ", end="")
            elif key_lower == 'c':
                send("#TPUG2wPTZ05")
                print("\r◎ Center        ", end="")
            # Photo and recording shortcuts were removed.
            elif key == '+' or key == '=':  # + and = both zoom in.
                send("#TPUD2wDZM0A")
                print("\r🔍+ Zoom in      ", end="")
            elif key == '-' or key == '_':  # - and _ both zoom out.
                send("#TPUD2wDZM0B")
                print("\r🔍- Zoom out      ", end="")
            elif key == '1':
                send("#TPUD2wDZM01")
                print("\r🔍 1x        ", end="")
            elif key == '2':
                send("#TPUD2wDZM02")
                print("\r🔍 2x        ", end="")
            elif key == '3':
                send("#TPUD2wDZM03")
                print("\r🔍 3x        ", end="")
            elif key == '4':
                send("#TPUD2wDZM04")
                print("\r🔍 4x        ", end="")
            
            sys.stdout.flush()
            
        time.sleep(0.05)

finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    send("#TPUG2wGSY00")
    send("#TPUG2wGSP00")
    sock.close()
    print("\n\nControls closed")
