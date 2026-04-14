from __future__ import annotations

import rclpy
from geometry_msgs.msg import TwistStamped
from rclpy.node import Node


class SpinRobotNode(Node):
    def __init__(self) -> None:
        super().__init__('spin_robot_node')
        self.declare_parameter('cmd_vel_topic', '/j100/cmd_vel')
        self.declare_parameter('linear_x', 0.0)
        self.declare_parameter('angular_z', 0.6)
        self.declare_parameter('period_sec', 0.1)

        self._cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self._linear_x = float(self.get_parameter('linear_x').value)
        self._angular_z = float(self.get_parameter('angular_z').value)
        period_sec = float(self.get_parameter('period_sec').value)

        self._publisher = self.create_publisher(TwistStamped, self._cmd_vel_topic, 10)
        self._timer = self.create_timer(period_sec, self._publish_cmd_vel)

        self.get_logger().info(
            f'Publishing spin commands to {self._cmd_vel_topic} '
            f'(linear_x={self._linear_x:.3f}, angular_z={self._angular_z:.3f})'
        )

    def _publish_cmd_vel(self) -> None:
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.twist.linear.x = self._linear_x
        msg.twist.angular.z = self._angular_z
        self._publisher.publish(msg)


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
