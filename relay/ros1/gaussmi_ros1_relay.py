#!/usr/bin/env python3

from __future__ import annotations

import argparse
import pathlib
import socket
import sys
import threading
from typing import Optional

import rospy
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import Image


RELAY_ROOT = pathlib.Path("/relay")
if RELAY_ROOT.exists() and str(RELAY_ROOT) not in sys.path:
    sys.path.insert(0, str(RELAY_ROOT))

from protocol import recv_frame, send_frame  # noqa: E402


class Ros1GaussmiRelay:
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self._sock: Optional[socket.socket] = None
        self._sock_lock = threading.Lock()
        self._running = True
        self._connected = threading.Event()

        self._pub_rgb = rospy.Publisher("/camera/bgr", Image, queue_size=10)
        self._pub_depth = rospy.Publisher("/camera/depth", Image, queue_size=10)
        self._pub_pose = rospy.Publisher("/camera/pose", PoseStamped, queue_size=10)

        self._sub_nbv = rospy.Subscriber("/gaussmi/nbv_pose", PoseStamped, self._on_nbv_pose, queue_size=10)

        self._server_thread = threading.Thread(target=self._serve, daemon=True)
        self._server_thread.start()

    def _serve(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self._host, self._port))
        server.listen(1)
        rospy.loginfo("ROS 1 relay listening on %s:%d", self._host, self._port)

        while self._running and not rospy.is_shutdown():
            try:
                conn, addr = server.accept()
            except OSError:
                break

            rospy.loginfo("ROS 1 relay connected from %s:%d", *addr)
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with self._sock_lock:
                self._sock = conn
                self._connected.set()

            try:
                self._recv_loop(conn)
            finally:
                with self._sock_lock:
                    if self._sock is conn:
                        self._sock = None
                        self._connected.clear()
                try:
                    conn.close()
                except OSError:
                    pass

        try:
            server.close()
        except OSError:
            pass

    def _recv_loop(self, conn: socket.socket) -> None:
        while self._running and not rospy.is_shutdown():
            frame = recv_frame(conn)
            if frame is None:
                rospy.logwarn("ROS 1 relay socket closed")
                return
            meta, payload = frame
            stream = meta.get("stream")
            if stream == "rgb":
                self._pub_rgb.publish(_image_from_meta(meta, payload))
            elif stream == "depth":
                self._pub_depth.publish(_image_from_meta(meta, payload))
            elif stream == "pose":
                self._pub_pose.publish(_pose_from_meta(meta))
            else:
                rospy.logwarn("ROS 1 relay received unknown stream %s", stream)

    def _send(self, meta, payload: bytes = b"") -> None:
        with self._sock_lock:
            sock = self._sock
        if sock is None:
            return
        try:
            send_frame(sock, meta, payload)
        except OSError as exc:
            rospy.logwarn("ROS 1 relay send failed: %s", exc)

    def _on_nbv_pose(self, msg: PoseStamped) -> None:
        self._send(_pose_meta("nbv", msg))

    def shutdown(self) -> None:
        self._running = False
        with self._sock_lock:
            sock = self._sock
            self._sock = None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass


def _stamp_meta(stamp) -> dict:
    return {"sec": int(stamp.secs), "nsec": int(stamp.nsecs)}


def _image_meta(stream: str, msg: Image) -> dict:
    return {
        "stream": stream,
        "kind": "image",
        "stamp": _stamp_meta(msg.header.stamp),
        "frame_id": msg.header.frame_id,
        "height": int(msg.height),
        "width": int(msg.width),
        "encoding": msg.encoding,
        "is_bigendian": int(msg.is_bigendian),
        "step": int(msg.step),
        "data_len": int(len(msg.data)),
    }


def _pose_meta(stream: str, msg: PoseStamped) -> dict:
    return {
        "stream": stream,
        "kind": "pose",
        "stamp": _stamp_meta(msg.header.stamp),
        "frame_id": msg.header.frame_id,
        "position": {
            "x": float(msg.pose.position.x),
            "y": float(msg.pose.position.y),
            "z": float(msg.pose.position.z),
        },
        "orientation": {
            "x": float(msg.pose.orientation.x),
            "y": float(msg.pose.orientation.y),
            "z": float(msg.pose.orientation.z),
            "w": float(msg.pose.orientation.w),
        },
    }


def _image_from_meta(meta: dict, payload: bytes) -> Image:
    msg = Image()
    msg.header.stamp.secs = int(meta["stamp"]["sec"])
    msg.header.stamp.nsecs = int(meta["stamp"]["nsec"])
    msg.header.frame_id = meta.get("frame_id", "")
    msg.height = int(meta["height"])
    msg.width = int(meta["width"])
    msg.encoding = meta["encoding"]
    msg.is_bigendian = int(meta["is_bigendian"])
    msg.step = int(meta["step"])
    msg.data = payload
    return msg


def _pose_from_meta(meta: dict) -> PoseStamped:
    msg = PoseStamped()
    msg.header.stamp.secs = int(meta["stamp"]["sec"])
    msg.header.stamp.nsecs = int(meta["stamp"]["nsec"])
    msg.header.frame_id = meta.get("frame_id", "")
    msg.pose.position.x = float(meta["position"]["x"])
    msg.pose.position.y = float(meta["position"]["y"])
    msg.pose.position.z = float(meta["position"]["z"])
    msg.pose.orientation.x = float(meta["orientation"]["x"])
    msg.pose.orientation.y = float(meta["orientation"]["y"])
    msg.pose.orientation.z = float(meta["orientation"]["z"])
    msg.pose.orientation.w = float(meta["orientation"]["w"])
    return msg


def main() -> None:
    parser = argparse.ArgumentParser(description="GauSS-MI ROS 1 relay")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50051)
    args = parser.parse_args()

    rospy.init_node("gaussmi_ros1_relay", anonymous=False)
    relay = Ros1GaussmiRelay(args.host, args.port)
    rospy.on_shutdown(relay.shutdown)
    rospy.loginfo("ROS 1 relay ready; waiting for ROS 2 relay connection")
    rospy.spin()


if __name__ == "__main__":
    main()
