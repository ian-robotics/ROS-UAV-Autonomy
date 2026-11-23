# ROS Robotics Software Integration

> To comply with my former employer’s confidentiality requirements, some sensitive content has been removed or replaced in this version.

The project integrates camera capture, video streaming, object detection, and node monitoring in a ROS 1 environment.

| Component | Role |
| --- | --- |
| `camera_rtsp` | Publishes camera feeds and ROS images as RTSP streams using GStreamer. |
| `rc_gimbal_bridge` | Converts RTSP feeds to ROS image topics, serves image topics over RTSP, and integrates a camera gimbal. |
| `yolov8_ros` | Detects objects and publishes bounding boxes and annotated images. |
| `check_ros_nodes` | Monitors ROS node availability and reports status changes. |

The software stack includes ROS Noetic, C++, Python, GStreamer, OpenCV, and YOLOv8.
