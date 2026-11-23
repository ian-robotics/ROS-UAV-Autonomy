#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import time
from dataclasses import dataclass, field
from typing import Optional, Dict

import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GLib, GstRtspServer


@dataclass
class StreamSpec:
    name: str
    topic: str
    mountpoint: str
    width: Optional[int] = None
    height: Optional[int] = None
    framerate: int = 20
    bitrate: int = 1500  # kbps
    format: str = "BGR"  # internal appsrc caps format
    # runtime fields
    appsrc = None
    initiated: bool = False
    frame_count: int = 0
    last_shape = None
    lock: threading.Lock = field(default_factory=threading.Lock)


class ImageRtspServer(object):
    def __init__(self):
        rospy.init_node('image_rtsp_server')

        # Init GStreamer
        Gst.init(None)

        self.bridge = CvBridge()
        self.server = GstRtspServer.RTSPServer()

        # Read private parameters first, then fall back to global parameters.
        port = rospy.get_param('~port', None)
        if port is None:
            port = rospy.get_param('port', 8554)
        self.server.props.service = str(port)
        self.mounts = self.server.get_mount_points()

        # Load streams param (private first, then global)
        streams_param = rospy.get_param('~streams', None)
        if streams_param is None:
            streams_param = rospy.get_param('streams', {})
        if not isinstance(streams_param, dict) or not streams_param:
            rospy.logerr('~streams The ~streams parameter is missing or invalid. Expected a dictionary.')
            raise SystemExit(1)

        self.streams: Dict[str, StreamSpec] = {}
        for key, cfg in streams_param.items():
            try:
                spec = StreamSpec(
                    name=key,
                    topic=str(cfg.get('source', cfg.get('topic', ''))),
                    mountpoint=str(cfg.get('mountpoint', f'/{key}')),
                    width=cfg.get('width'),
                    height=cfg.get('height'),
                    framerate=int(cfg.get('framerate', 20)),
                    bitrate=int(cfg.get('bitrate', 1500)),
                    format=str(cfg.get('format', 'BGR')).upper(),
                )
            except Exception as e:
                rospy.logerr(f'Failed to parse stream configuration {key}: {e}')
                raise

            if not spec.topic:
                rospy.logerr(f'Stream {key} is missing the topic or source parameter')
                raise SystemExit(1)

            self.streams[key] = spec

        # Start GLib mainloop for RTSP server
        self.mainloop = GLib.MainLoop()
        self.mainloop_thread = threading.Thread(target=self.mainloop.run, name='glib-mainloop', daemon=True)
        self.mainloop_thread.start()

        # Attach server
        self.server.attach(None)
        rospy.loginfo(f'RTSP RTSP server listening on port: {port}')

        # Subscribers per stream
        for key, spec in self.streams.items():
            rospy.Subscriber(spec.topic, Image, self._make_img_cb(spec), queue_size=1, buff_size=2**24)
            rospy.loginfo(f'Subscribed to image topic: {spec.topic} -> rtsp://0.0.0.0:{port}{spec.mountpoint}')

    def _make_img_cb(self, spec: StreamSpec):
        def cb(msg: Image):
            try:
                # Convert to BGR
                cv_img = self._to_bgr(spec, msg)
                h, w = cv_img.shape[:2]

                # First frame: create RTSP media and mount
                if not spec.initiated:
                    with spec.lock:
                        if not spec.initiated:
                            # Fill width/height if missing
                            spec.width = spec.width or w
                            spec.height = spec.height or h
                            self._create_mount(spec)
                            spec.initiated = True

                # Drop frames until appsrc is available (no client yet)
                if spec.appsrc is None:
                    return

                # If resolution changed after init, skip (or extend to recreate)
                if (spec.width, spec.height) != (w, h):
                    # Ignore resolution changes to keep the current stream running.
                    return

                data = cv_img.tobytes()
                buf = Gst.Buffer.new_allocate(None, len(data), None)
                buf.fill(0, data)

                duration = int(1e9 / max(1, spec.framerate))
                buf.duration = duration
                spec.frame_count += 1
                # Let appsrc assign timestamps automatically with do-timestamp.

                ret = spec.appsrc.emit('push-buffer', buf)
                if ret != Gst.FlowReturn.OK:
                    rospy.logwarn_throttle(5.0, f'[{spec.name}] push-buffer returned {ret}')
            except Exception as e:
                rospy.logwarn_throttle(2.0, f'[{spec.name}] Failed to process image: {e}')
        return cb

    def _to_bgr(self, spec: StreamSpec, msg: Image):
        # Prefer BGR to reduce work for the encoder.
        if msg.encoding.lower() in ('bgr8', 'bgr'):  # already BGR
            return self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        elif msg.encoding.lower() in ('rgb8', 'rgb'):
            img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='rgb8')
            return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        elif msg.encoding.lower() in ('mono8', '8uc1', 'mono16'):
            # Convert grayscale to BGR for encoder compatibility with yuv420p.
            img = self.bridge.imgmsg_to_cv2(msg)
            if len(img.shape) == 2:
                return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            return img
        else:
            # Fall back to BGR8
            return self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

    def _create_mount(self, spec: StreamSpec):
        # Build pipeline string
        caps = f"video/x-raw,format={spec.format},width={spec.width},height={spec.height},framerate={spec.framerate}/1"
        # x264enc measures bitrate in kbps. A config interval of 1 sends SPS and PPS periodically so clients can join midstream.
        launch_str = (
            f"appsrc name=src_{spec.name} is-live=true block=true do-timestamp=true format=GST_FORMAT_TIME caps=\"{caps}\" ! "
            f"videoconvert ! x264enc tune=zerolatency speed-preset=ultrafast bitrate={spec.bitrate} key-int-max={max(1, spec.framerate*2)} ! "
            f"rtph264pay name=pay0 pt=96 config-interval=1"
        )

        factory = GstRtspServer.RTSPMediaFactory()
        factory.set_launch(launch_str)
        factory.set_shared(True)

        def on_configure(factory, media, user_data):
            try:
                element = media.get_element()
                appsrc = element.get_child_by_name(f"src_{spec.name}")
                if appsrc is None:
                    rospy.logwarn(f'[{spec.name}] Could not find appsrc')
                    return
                appsrc.set_property('format', Gst.Format.TIME)
                appsrc.set_property('is-live', True)
                appsrc.set_property('block', True)
                appsrc.set_property('do-timestamp', True)
                spec.appsrc = appsrc
                rospy.loginfo(f'[{spec.name}] RTSP RTSP media configured and awaiting clients: {spec.mountpoint}')
            except Exception as e:
                rospy.logwarn(f'[{spec.name}] Failed to configure media: {e}')

        factory.connect('media-configure', on_configure, None)

        self.mounts.add_factory(spec.mountpoint, factory)
        rospy.loginfo(f'Mounted stream: rtsp://0.0.0.0:{self.server.props.service}{spec.mountpoint} ({spec.width}x{spec.height}@{spec.framerate}, {spec.bitrate}kbps)')

    def spin(self):
        rospy.loginfo('Image RTSP Server started. Press Ctrl+C to exit.')
        try:
            rospy.spin()
        finally:
            # Attempt a clean shutdown. The RTSP server exits with the main process.
            try:
                self.mainloop.quit()
            except Exception:
                pass


if __name__ == '__main__':
    ImageRtspServer().spin()
