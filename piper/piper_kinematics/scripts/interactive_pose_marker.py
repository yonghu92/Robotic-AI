#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from interactive_markers.interactive_marker_server import InteractiveMarkerServer
from visualization_msgs.msg import InteractiveMarker, InteractiveMarkerControl
from visualization_msgs.msg import InteractiveMarkerFeedback
from geometry_msgs.msg import PoseStamped, Point, Quaternion
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped

class InteractivePoseMarker(Node):
    def __init__(self):
        super().__init__('interactive_pose_marker')
        
        # 参数
        self.declare_parameter('marker_name', 'target_pose')
        self.declare_parameter('reference_frame', 'base_link')
        self.declare_parameter('initial_position', [0.5, 0.0, 0.5])
        self.declare_parameter('marker_scale', 0.2)
        self.declare_parameter('pose_topic', '/target_pose')
        
        self.marker_name = self.get_parameter('marker_name').get_parameter_value().string_value
        self.reference_frame = self.get_parameter('reference_frame').get_parameter_value().string_value
        self.initial_position = self.get_parameter('initial_position').get_parameter_value().double_array_value
        self.marker_scale = self.get_parameter('marker_scale').get_parameter_value().double_value
        self.pose_topic = self.get_parameter('pose_topic').get_parameter_value().string_value
        
        # 创建交互标记服务器
        self.server = InteractiveMarkerServer(self, "interactive_marker")
        
        # 创建位姿发布者
        self.pose_pub = self.create_publisher(PoseStamped, self.pose_topic, 10)
        
        # 创建TF广播器
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # 初始化标记
        self.create_marker()
        
        self.get_logger().info(f"Interactive pose marker '{self.marker_name}' is ready in frame '{self.reference_frame}'")
    
    def create_marker(self):
        """创建一个6自由度交互式标记"""
        # 创建交互标记
        int_marker = InteractiveMarker()
        int_marker.header.frame_id = self.reference_frame
        int_marker.header.stamp = self.get_clock().now().to_msg()
        int_marker.name = self.marker_name
        int_marker.description = f"{self.marker_name} (6DOF Control)"
        int_marker.pose.position.x = float(self.initial_position[0])
        int_marker.pose.position.y = float(self.initial_position[1])
        int_marker.pose.position.z = float(self.initial_position[2])
        int_marker.pose.orientation.w = 1.0
        int_marker.scale = float(self.marker_scale)

        # 添加6自由度控制
        self.add_6dof_control(int_marker)
        
        # 添加到服务器 (ROS2 API: feedback_callback is a keyword argument)
        self.server.insert(int_marker, feedback_callback=self.marker_feedback_cb)
        self.server.applyChanges()
    
    def add_6dof_control(self, int_marker):
        """为标记添加6自由度控制"""
        # 旋转控制
        for axis in ['x', 'y', 'z']:
            control = self.make_arrow_control(axis, mode=InteractiveMarkerControl.ROTATE_AXIS)
            int_marker.controls.append(control)
        
        # 平移控制
        for axis in ['x', 'y', 'z']:
            control = self.make_arrow_control(axis, mode=InteractiveMarkerControl.MOVE_AXIS)
            int_marker.controls.append(control)
    
    def make_arrow_control(self, axis, mode):
        """创建箭头控制"""
        control = InteractiveMarkerControl()
        
        if axis == 'x':
            control.orientation.w = 0.7071
            control.orientation.x = 0.7071
            control.orientation.y = 0.0
            control.orientation.z = 0.0
            control.name = f"rotate_{axis}" if mode == InteractiveMarkerControl.ROTATE_AXIS else f"move_{axis}"
        elif axis == 'y':
            control.orientation.w = 0.7071
            control.orientation.x = 0.0
            control.orientation.y = 0.0
            control.orientation.z = 0.7071
            control.name = f"rotate_{axis}" if mode == InteractiveMarkerControl.ROTATE_AXIS else f"move_{axis}"
        elif axis == 'z':
            control.orientation.w = 0.7071
            control.orientation.x = 0.0
            control.orientation.y = 0.7071
            control.orientation.z = 0.0
            control.name = f"rotate_{axis}" if mode == InteractiveMarkerControl.ROTATE_AXIS else f"move_{axis}"
        
        control.interaction_mode = mode
        control.always_visible = True
        return control
    
    def marker_feedback_cb(self, feedback):
        """标记移动时的回调函数"""
        # 发布位姿
        pose_msg = PoseStamped()
        pose_msg.header = feedback.header
        pose_msg.pose = feedback.pose
        self.pose_pub.publish(pose_msg)
        
        # 发布TF - ROS2方式
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = feedback.header.frame_id
        t.child_frame_id = feedback.marker_name
        t.transform.translation.x = feedback.pose.position.x
        t.transform.translation.y = feedback.pose.position.y
        t.transform.translation.z = feedback.pose.position.z
        t.transform.rotation = feedback.pose.orientation
        self.tf_broadcaster.sendTransform(t)

def main(args=None):
    rclpy.init(args=args)
    node = InteractivePoseMarker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass  # Ignore if already shut down

if __name__ == '__main__':
    main()