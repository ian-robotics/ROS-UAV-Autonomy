#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import tkinter as tk
import rospy


def calculate_checksum(cmd: str) -> str:
    return f"{sum(ord(c) for c in cmd) & 0xFF:02X}"


class GimbalKeyboardGUI:
    def __init__(self):
        rospy.init_node('gimbal_keyboard_gui')
        self.camera_ip = rospy.get_param('~camera_ip', '127.0.0.1')
        self.udp_port = rospy.get_param('~port', 5000)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.root = tk.Tk()
        self.root.title('Gimbal Keyboard Controls')
        self.root.geometry('480x320')

        info = (
            'W/S: Pitch ±60\n'
            'A/D: Yaw ±70\n'
            'Space: Stop\n'
            'C: Center\n'
            '+ / -: Zoom   1–4: Select zoom level\n'
            '\n'
            f'Destination: {self.camera_ip}:{self.udp_port}'
        )
        self.label = tk.Label(self.root, text=info, justify='left')
        self.label.pack(padx=12, pady=12, anchor='w')

        self.status_var = tk.StringVar(value='Ready')
        self.status = tk.Label(self.root, textvariable=self.status_var, fg='green')
        self.status.pack(padx=12, pady=6, anchor='w')

        self.root.bind('<KeyPress>', self.on_key)
        self.root.bind('<KeyRelease>', self.on_key_release)
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)

        rospy.loginfo('gimbal_keyboard_gui started. Focus this window to use shortcuts.')

    def send(self, cmd: str):
        full = cmd + calculate_checksum(cmd)
        try:
            self.sock.sendto(full.encode(), (self.camera_ip, self.udp_port))
        except Exception as e:
            rospy.logwarn_throttle(1.0, f'Send failed: {e}')

    @staticmethod
    def to_hex_signed(v: int) -> str:
        if v < 0:
            v = 256 + v
        return f"{int(v) & 0xFF:02X}"

    def set_speed(self, yaw: int, pitch: int):
        if yaw != 0:
            self.send('#TPUG2wGSY' + self.to_hex_signed(yaw))
        if pitch != 0:
            self.send('#TPUG2wGSP' + self.to_hex_signed(pitch))

    def on_key(self, event):
        k = event.keysym.lower()
        if k == 'w':
            self.set_speed(0, 60)
            self.status_var.set('Up')
        elif k == 's':
            self.set_speed(0, -60)
            self.status_var.set('Down')
        elif k == 'a':
            self.set_speed(-70, 0)
            self.status_var.set('Left')
        elif k == 'd':
            self.set_speed(70, 0)
            self.status_var.set('Right')
        elif k == 'space':
            self.send('#TPUG2wGSY00')
            self.send('#TPUG2wGSP00')
            self.status_var.set('Stop')
        elif k == 'c':
            self.send('#TPUG2wPTZ05')
            self.status_var.set('Center')
        # Photo and recording controls were removed.
        elif k in ('plus', 'equal'):  # + or =
            self.send('#TPUD2wDZM0A')
            self.status_var.set('Zoom in')
        elif k in ('minus', 'underscore'):
            self.send('#TPUD2wDZM0B')
            self.status_var.set('Zoom out')
        elif k == '1':
            self.send('#TPUD2wDZM01')
            self.status_var.set('1x')
        elif k == '2':
            self.send('#TPUD2wDZM02')
            self.status_var.set('2x')
        elif k == '3':
            self.send('#TPUD2wDZM03')
            self.status_var.set('3x')
        elif k == '4':
            self.send('#TPUD2wDZM04')
            self.status_var.set('4x')

    def on_key_release(self, event):
        # Stop both axes when a movement key is released.
        if event.keysym.lower() in ('w', 's', 'a', 'd'):
            self.send('#TPUG2wGSY00')
            self.send('#TPUG2wGSP00')
            self.status_var.set('Stop')

    def on_close(self):
        try:
            self.send('#TPUG2wGSY00')
            self.send('#TPUG2wGSP00')
            self.sock.close()
        except Exception:
            pass
        self.root.destroy()
        rospy.signal_shutdown('UI closed')

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = GimbalKeyboardGUI()
    app.run()
