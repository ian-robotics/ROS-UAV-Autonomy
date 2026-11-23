# RC Gimbal Bridge

This ROS package connects RTSP camera feeds, ROS image topics, and camera gimbal controls.

| Launch file | Purpose |
| --- | --- |
| `rtsp_camera_relay.launch` | Publish one RTSP camera feed as a ROS image topic. |
| `rtsp_dual_camera_relay.launch` | Publish separate RGB and thermal camera feeds. |
| `rtsp_topics_server.launch` | Serve ROS image topics over RTSP. |
| `rtsp_dual_to_qgc.launch` | Relay and serve both feeds for a ground-station client. |
| `rc_channel_monitor.launch` | Monitor channels from the RC input topic. |
| `rc_to_udp_gimbal.launch` | Convert RC input to UDP gimbal commands. |

The C++ relay reads RTSP over TCP using OpenCV with the FFmpeg backend. The Python server uses GStreamer RTSP Server and reads its stream configuration from `config/rtsp_topics.yaml`. For keyboard control, use the Tk interface or the console controller.

If a stream fails to open, verify that the client can reach the configured RTSP host and mount point. If the server is reachable but the image is blank, check that the corresponding ROS image topic is publishing.

Pass the appropriate RTSP URLs and camera address as launch arguments for your setup. The console controller reads the camera address from `GIMBAL_CAMERA_IP`.
