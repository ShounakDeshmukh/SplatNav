from __future__ import annotations

import math

import rclpy
from geometry_msgs.msg import PoseStamped, TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node


class SpinRobotNode(Node):
    def __init__(self) -> None:
        super().__init__('spin_robot_node')
        self.declare_parameter('cmd_vel_topic', '/j100/cmd_vel')
        self.declare_parameter('odom_topic', '/j100/platform/odom/filtered')
        self.declare_parameter('nbv_topic', '/gaussmi/nbv_pose')
        self.declare_parameter('mode', 'spin')
        self.declare_parameter('linear_x', 0.0)
        self.declare_parameter('angular_z', 0.6)
        self.declare_parameter('max_linear_x', 0.45)
        self.declare_parameter('max_angular_z', 1.0)
        self.declare_parameter('yaw_gain', 1.8)
        self.declare_parameter('dist_gain', 0.6)
        self.declare_parameter('goal_tolerance', 0.35)
        self.declare_parameter('period_sec', 0.1)

        self._cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self._odom_topic = self.get_parameter('odom_topic').value
        self._nbv_topic = self.get_parameter('nbv_topic').value
        self._mode = str(self.get_parameter('mode').value).strip().lower()
        self._linear_x = float(self.get_parameter('linear_x').value)
        self._angular_z = float(self.get_parameter('angular_z').value)
        self._max_linear_x = float(self.get_parameter('max_linear_x').value)
        self._max_angular_z = float(self.get_parameter('max_angular_z').value)
        self._yaw_gain = float(self.get_parameter('yaw_gain').value)
        self._dist_gain = float(self.get_parameter('dist_gain').value)
        self._goal_tolerance = float(self.get_parameter('goal_tolerance').value)
        period_sec = float(self.get_parameter('period_sec').value)

        self._publisher = self.create_publisher(TwistStamped, self._cmd_vel_topic, 10)
        self._odom_sub = self.create_subscription(Odometry, self._odom_topic, self._on_odom, 10)
        self._nbv_sub = self.create_subscription(PoseStamped, self._nbv_topic, self._on_nbv, 10)
        self._timer = self.create_timer(period_sec, self._publish_cmd_vel)

        self._latest_odom: Odometry | None = None
        self._latest_nbv: PoseStamped | None = None

        self.get_logger().info(
            f'Publishing commands to {self._cmd_vel_topic} in mode={self._mode} '
            f'(odom={self._odom_topic}, nbv={self._nbv_topic})'
        )

    def _on_odom(self, msg: Odometry) -> None:
        self._latest_odom = msg

    def _on_nbv(self, msg: PoseStamped) -> None:
        self._latest_nbv = msg

    def _publish_cmd_vel(self) -> None:
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'

        linear_x = self._linear_x
        angular_z = self._angular_z

        if self._mode in {'nbv', 'chase', 'active'}:
            target = self._latest_nbv
            odom = self._latest_odom
            if target is not None and odom is not None:
                linear_x, angular_z = self._compute_nav_cmd(odom, target)
            else:
                linear_x = 0.0
                angular_z = self._angular_z

        msg.twist.linear.x = linear_x
        msg.twist.angular.z = angular_z
        self._publisher.publish(msg)

    def _compute_nav_cmd(self, odom: Odometry, target: PoseStamped) -> tuple[float, float]:
        dx = float(target.pose.position.x - odom.pose.pose.position.x)
        dy = float(target.pose.position.y - odom.pose.pose.position.y)
        distance = math.hypot(dx, dy)

        current_yaw = _yaw_from_quaternion(
            odom.pose.pose.orientation.x,
            odom.pose.pose.orientation.y,
            odom.pose.pose.orientation.z,
            odom.pose.pose.orientation.w,
        )
        target_yaw = math.atan2(dy, dx)
        yaw_error = _normalize_angle(target_yaw - current_yaw)

        if distance < self._goal_tolerance:
            return 0.0, 0.0

        angular_z = max(-self._max_angular_z, min(self._max_angular_z, self._yaw_gain * yaw_error))

        # Slow down if the robot is not facing the target yet.
        heading_scale = max(0.0, math.cos(yaw_error))
        linear_x = self._dist_gain * distance * heading_scale
        linear_x = max(0.0, min(self._max_linear_x, linear_x))
        return linear_x, angular_z


def _normalize_angle(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


def _yaw_from_quaternion(x: float, y: float, z: float, w: float) -> float:
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def main() -> None:
    rclpy.init()
    node = SpinRobotNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
