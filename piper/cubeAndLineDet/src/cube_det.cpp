#include <rclcpp/rclcpp.hpp>
#include "opencv2/opencv.hpp"
#include <cv_bridge/cv_bridge.hpp>
#include <iostream>
#include <sensor_msgs/msg/image.hpp>
#include <sensor_msgs/msg/camera_info.hpp>
#include <image_transport/image_transport.hpp>
#include <opencv2/highgui.hpp>
#include <opencv2/imgproc.hpp>
#include <visualization_msgs/msg/marker_array.hpp>
#include <geometry_msgs/msg/point.hpp>
#include <std_msgs/msg/color_rgba.hpp>
#include <memory>

using namespace std::chrono_literals;

class CubeDetector : public rclcpp::Node {
public:
    CubeDetector() : Node("cube_detection_node") {
        // Declare parameters
        this->declare_parameter<std::string>("image_topic_name", "/camera/color/image_raw");
        this->declare_parameter<std::string>("camera_info_topic_name", "/camera/color/camera_info");
        this->declare_parameter<std::string>("depth_topic_name", "/camera/depth/image_raw");
        
        // Get parameters
        std::string image_topic = this->get_parameter("image_topic_name").as_string();
        std::string camera_info_topic = this->get_parameter("camera_info_topic_name").as_string();
        std::string depth_topic = this->get_parameter("depth_topic_name").as_string();
        
        // Create publishers
        marker_pub_ = this->create_publisher<visualization_msgs::msg::MarkerArray>("cube_coordinates", 10);
        
        // Create subscribers
        image_sub_ = this->create_subscription<sensor_msgs::msg::Image>(
            image_topic, 1, std::bind(&CubeDetector::imageCallback, this, std::placeholders::_1));
        info_sub_ = this->create_subscription<sensor_msgs::msg::CameraInfo>(
            camera_info_topic, 1, std::bind(&CubeDetector::cameraInfoCallback, this, std::placeholders::_1));
        // Use QoS that matches camera driver (TRANSIENT_LOCAL durability)
        auto depth_qos = rclcpp::QoS(rclcpp::KeepLast(1))
            .reliability(rclcpp::ReliabilityPolicy::Reliable)
            .durability(rclcpp::DurabilityPolicy::TransientLocal);
        depth_sub_ = this->create_subscription<sensor_msgs::msg::Image>(
            depth_topic, depth_qos, std::bind(&CubeDetector::depthCallback, this, std::placeholders::_1));
        
        // Initialize OpenCV windows
        cv::namedWindow("origin_image", cv::WINDOW_GUI_EXPANDED);
        cv::namedWindow("hsv_image", cv::WINDOW_GUI_EXPANDED);
        cv::namedWindow("depth_image", cv::WINDOW_GUI_EXPANDED);
        // Position windows so they don't overlap
        cv::moveWindow("origin_image", 0, 0);
        cv::moveWindow("hsv_image", 650, 0);
        cv::moveWindow("depth_image", 1300, 0);
        RCLCPP_INFO(this->get_logger(), "Created OpenCV windows: origin_image, hsv_image, depth_image");
        
        // Show placeholder in depth window immediately so it appears
        cv::Mat placeholder = cv::Mat::zeros(480, 640, CV_8UC3);
        cv::putText(placeholder, "Waiting for depth data...", cv::Point(100, 240), 
                   cv::FONT_HERSHEY_SIMPLEX, 0.8, cv::Scalar(255, 255, 255), 2);
        cv::imshow("depth_image", placeholder);
        cv::waitKey(1); // Force window to appear
        cv::setMouseCallback("origin_image", &CubeDetector::onMouseStatic, this);
        
        cv::createTrackbar("hmin", "hsv_image", &hmin, hmin_Max, &CubeDetector::callBackStatic, this);
        cv::createTrackbar("hmax", "hsv_image", &hmax, hmax_Max, &CubeDetector::callBackStatic, this);
        cv::createTrackbar("smin", "hsv_image", &smin, smin_Max, &CubeDetector::callBackStatic, this);
        cv::createTrackbar("smax", "hsv_image", &smax, smax_Max, &CubeDetector::callBackStatic, this);
        cv::createTrackbar("vmin", "hsv_image", &vmin, vmin_Max, &CubeDetector::callBackStatic, this);
        cv::createTrackbar("vmax", "hsv_image", &vmax, vmax_Max, &CubeDetector::callBackStatic, this);
        
        // Create timer for main loop
        timer_ = this->create_wall_timer(33ms, std::bind(&CubeDetector::timerCallback, this));
    }
    
    ~CubeDetector() {
        cv::destroyAllWindows();
    }

private:
    bool camera_info_received_ = false;
    bool image_received_ = false;
    bool depth_received_ = false;
    cv::Mat K_;
    cv::Mat image_;
    cv::Mat depth_;
    cv::Mat bgr_;
    cv::Mat hsv_;
    cv::Mat dst_;
    cv::Mat depth_vis_;
    cv::Point cpoint_;

    int hmin = 0, hmin_Max = 360;
    int hmax = 180, hmax_Max = 180;
    int smin = 0, smin_Max = 255;
    int smax = 255, smax_Max = 255;
    int vmin = 106, vmin_Max = 255;
    int vmax = 255, vmax_Max = 255;

    rclcpp::Publisher<visualization_msgs::msg::MarkerArray>::SharedPtr marker_pub_;
    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr image_sub_;
    rclcpp::Subscription<sensor_msgs::msg::CameraInfo>::SharedPtr info_sub_;
    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr depth_sub_;
    rclcpp::TimerBase::SharedPtr timer_;

    static void onMouseStatic(int event, int x, int y, int flags, void* userdata) {
        CubeDetector* detector = static_cast<CubeDetector*>(userdata);
        detector->onMouse(event, x, y, flags);
    }

    void onMouse(int event, int x, int y, int flags) {
        if (event == cv::EVENT_LBUTTONDOWN && !hsv_.empty()) {
            cv::Vec3b hsv_pixel = hsv_.at<cv::Vec3b>(y, x);
            int h = hsv_pixel[0], s = hsv_pixel[1], v = hsv_pixel[2];
            RCLCPP_INFO(this->get_logger(), "Clicked at (%d, %d) - HSV: (%d, %d, %d)", x, y, h, s, v);
            
            int range = 20;
            hmin = std::max(0, h - range); hmax = std::min(hmax_Max, h + range);
            smin = std::max(0, s - range); smax = std::min(smax_Max, s + range);
            vmin = std::max(0, v - range); vmax = std::min(vmax_Max, v + range);
            
            cv::setTrackbarPos("hmin", "hsv_image", hmin);
            cv::setTrackbarPos("hmax", "hsv_image", hmax);
            cv::setTrackbarPos("smin", "hsv_image", smin);
            cv::setTrackbarPos("smax", "hsv_image", smax);
            cv::setTrackbarPos("vmin", "hsv_image", vmin);
            cv::setTrackbarPos("vmax", "hsv_image", vmax);
            callBack();
        }
    }

    static void callBackStatic(int, void* userdata) {
        CubeDetector* detector = static_cast<CubeDetector*>(userdata);
        detector->callBack();
    }

    void callBack() {
        if (hsv_.empty()) return;
        
        dst_ = cv::Mat::zeros(image_.size(), image_.type());
        cv::Mat mask;
        cv::inRange(hsv_, cv::Scalar(hmin, smin, vmin), cv::Scalar(hmax, smax, vmax), mask);
        
        for (int r = 0; r < bgr_.rows; r++) {
            for (int c = 0; c < bgr_.cols; c++) {
                if (mask.at<uchar>(r, c) == 255) {
                    dst_.at<cv::Vec3b>(r, c) = bgr_.at<cv::Vec3b>(r, c);
                }
            }
        }
        
        cv::Mat gray, binary;
        cv::cvtColor(dst_, gray, cv::COLOR_BGR2GRAY);
        cv::threshold(gray, binary, 127, 255, cv::THRESH_OTSU);
        
        std::vector<std::vector<cv::Point>> contours;
        std::vector<cv::Vec4i> hierarchy;
        cv::findContours(binary, contours, hierarchy, cv::RETR_TREE, cv::CHAIN_APPROX_NONE);
        
        int max_matches = 0;
        cv::Rect best_rect;
        cv::Point center_point;

        for (size_t i = 0; i < contours.size(); i++) {
            cv::Rect rect = cv::boundingRect(contours[i]);
            cv::Mat rect_mask = cv::Mat::zeros(image_.size(), CV_8UC1);
            cv::drawContours(rect_mask, contours, i, cv::Scalar(255), cv::FILLED);
            
            cv::Mat rect_hsv;
            hsv_.copyTo(rect_hsv, rect_mask);
            cv::Mat rect_color_mask;
            cv::inRange(rect_hsv, cv::Scalar(hmin, smin, vmin), cv::Scalar(hmax, smax, vmax), rect_color_mask);
            
            int matches = cv::countNonZero(rect_color_mask(rect));
            if (matches > max_matches) {
                max_matches = matches;
                best_rect = rect;
                center_point = cv::Point(rect.x + rect.width/2, rect.y + rect.height/2);
            }
            cv::rectangle(dst_, rect, cv::Scalar(0, 0, 255), 2);
        }

        if (max_matches > 1000) {
            cv::rectangle(dst_, best_rect, cv::Scalar(0, 255, 0), 3);
            cv::circle(dst_, center_point, 5, cv::Scalar(255, 0, 0), -1);
            RCLCPP_INFO(this->get_logger(), "Best rectangle center at (%d, %d)", center_point.x, center_point.y);
            cpoint_ = center_point;
        }

        if (!dst_.empty()) cv::imshow("hsv_image", dst_);
    }

    void publishCoordinateMarker(float x, float y, float z) {
        visualization_msgs::msg::MarkerArray marker_array;

        visualization_msgs::msg::Marker point_marker;
        point_marker.header.frame_id = "camera_color_optical_frame";
        point_marker.header.stamp = this->now();
        point_marker.ns = "cube_coordinates";
        point_marker.id = 0;
        point_marker.type = visualization_msgs::msg::Marker::SPHERE;
        point_marker.action = visualization_msgs::msg::Marker::ADD;
        point_marker.pose.position.x = x;
        point_marker.pose.position.y = y;
        point_marker.pose.position.z = z;
        point_marker.pose.orientation.w = 1.0;
        point_marker.scale.x = 0.02;
        point_marker.scale.y = 0.02;
        point_marker.scale.z = 0.02;
        point_marker.color.r = 1.0;
        point_marker.color.a = 1.0;
        point_marker.lifetime = rclcpp::Duration::from_seconds(0.1);

        visualization_msgs::msg::Marker text_marker;
        text_marker.header = point_marker.header;
        text_marker.ns = "cube_coordinates";
        text_marker.id = 1;
        text_marker.type = visualization_msgs::msg::Marker::TEXT_VIEW_FACING;
        text_marker.action = visualization_msgs::msg::Marker::ADD;
        text_marker.pose.position.x = x + 0.05;
        text_marker.pose.position.y = y;
        text_marker.pose.position.z = z + 0.05;
        text_marker.pose.orientation.w = 1.0;
        text_marker.scale.z = 0.02;
        text_marker.color.r = 1.0;
        text_marker.color.g = 1.0;
        text_marker.color.b = 1.0;
        text_marker.color.a = 1.0;
        text_marker.text = "X: " + std::to_string(x) + "\nY: " + std::to_string(y) + "\nZ: " + std::to_string(z);
        text_marker.lifetime = rclcpp::Duration::from_seconds(0.1);

        marker_array.markers.push_back(point_marker);
        marker_array.markers.push_back(text_marker);
        marker_pub_->publish(marker_array);
    }

    void depthCallback(const sensor_msgs::msg::Image::ConstSharedPtr msg) {
        int r = 10;
        try {
            cv_bridge::CvImageConstPtr cv_ptr = cv_bridge::toCvShare(msg, "16UC1");
            depth_ = cv_ptr->image.clone();
            if (!depth_.empty()) {
                depth_received_ = true;
                RCLCPP_INFO(this->get_logger(), "DEPTH CALLBACK: Received depth image %dx%d", depth_.cols, depth_.rows);
                
                // Visualize depth image (convert 16-bit to 8-bit for display)
                cv::Mat depth_normalized;
                depth_.convertTo(depth_normalized, CV_8UC1, 255.0 / 8000.0); // Normalize to 0-255, assuming max depth ~8m
                cv::applyColorMap(depth_normalized, depth_vis_, cv::COLORMAP_JET);
                RCLCPP_INFO(this->get_logger(), "DEPTH CALLBACK: Created depth visualization %dx%d", depth_vis_.cols, depth_vis_.rows);
                
                // Draw circle at detection point
                if (cpoint_.x > 0 && cpoint_.y > 0) {
                    cv::circle(depth_vis_, cpoint_, r, cv::Scalar(0, 255, 0), 2);
                }
                
                // Show depth window immediately in callback
                cv::imshow("depth_image", depth_vis_);
                
                cv::Mat mask = cv::Mat::zeros(depth_.size(), CV_8UC1);
                cv::circle(mask, cpoint_, r, cv::Scalar(255), -1);
                
                cv::Mat depth_roi;
                depth_.copyTo(depth_roi, mask);
                
                cv::Mat depth_float;
                depth_roi.convertTo(depth_float, CV_32F);
                depth_float.setTo(std::numeric_limits<float>::quiet_NaN(), depth_roi == 0);
                
                cv::Scalar mean_depth = cv::mean(depth_float, mask);
                
                if (!std::isnan(mean_depth[0])) {
                    RCLCPP_INFO(this->get_logger(), "Depth at (%d,%d): %f mm", cpoint_.x, cpoint_.y, mean_depth[0]);
                    
                    if (camera_info_received_) {
                        float fx = K_.at<float>(0, 0);
                        float fy = K_.at<float>(1, 1);
                        float cx = K_.at<float>(0, 2);
                        float cy = K_.at<float>(1, 2);
                        
                        float depth_m = mean_depth[0] / 1000.0;
                        float X = (cpoint_.x - cx) * depth_m / fx;
                        float Y = (cpoint_.y - cy) * depth_m / fy;
                        float Z = depth_m;
                        
                        RCLCPP_INFO(this->get_logger(), "3D Position: X=%.3fm, Y=%.3fm, Z=%.3fm", X, Y, Z);
                        publishCoordinateMarker(X, Y, Z);
                    }
                }
            }
        } catch (const std::exception& e) {
            RCLCPP_ERROR(this->get_logger(), "Depth callback error: %s", e.what());
        }
    }

    void imageCallback(const sensor_msgs::msg::Image::ConstSharedPtr msg) {
        try {
            cv_bridge::CvImageConstPtr cv_ptr = cv_bridge::toCvShare(msg, "bgr8");
            image_ = cv_ptr->image.clone();
            if (!image_.empty()) {
                image_received_ = true;
                bgr_ = image_.clone();
                cv::cvtColor(bgr_, hsv_, cv::COLOR_BGR2HSV);
            }
        } catch (cv_bridge::Exception &e) {
            RCLCPP_ERROR(this->get_logger(), "Image callback error: %s", e.what());
        }
    }

    void cameraInfoCallback(const sensor_msgs::msg::CameraInfo::ConstSharedPtr msg) {
        if (!camera_info_received_) {
            K_ = cv::Mat(3, 3, CV_32F);
            for (int i = 0; i < 9; ++i) K_.at<float>(i/3, i%3) = msg->k[i];
            camera_info_received_ = true;
            RCLCPP_INFO_STREAM(this->get_logger(), "Camera Intrinsics:\n" << K_);
        }
    }

    void timerCallback() {
        if (image_received_ && !image_.empty()) {
            cv::imshow("origin_image", image_);
            callBack();
        }
        
        // ALWAYS show depth window - no conditions
        static int frame_count = 0;
        frame_count++;
        
        if (depth_received_ && !depth_.empty() && !depth_vis_.empty()) {
            // Show actual depth visualization
            cv::imshow("depth_image", depth_vis_);
            if (frame_count % 30 == 0) {
                RCLCPP_INFO(this->get_logger(), "TIMER: Showing depth_vis_ %dx%d", depth_vis_.cols, depth_vis_.rows);
            }
        } else if (depth_received_ && !depth_.empty()) {
            // Create visualization on the fly if not ready
            cv::Mat depth_normalized;
            depth_.convertTo(depth_normalized, CV_8UC1, 255.0 / 8000.0);
            cv::applyColorMap(depth_normalized, depth_vis_, cv::COLORMAP_JET);
            if (cpoint_.x > 0 && cpoint_.y > 0) {
                cv::circle(depth_vis_, cpoint_, 10, cv::Scalar(0, 255, 0), 2);
            }
            cv::imshow("depth_image", depth_vis_);
            if (frame_count % 30 == 0) {
                RCLCPP_INFO(this->get_logger(), "TIMER: Created and showing depth_vis_ on the fly");
            }
        } else {
            // Show placeholder - ALWAYS show something
            static cv::Mat placeholder;
            static bool initialized = false;
            if (!initialized) {
                placeholder = cv::Mat::zeros(480, 640, CV_8UC3);
                cv::putText(placeholder, "Waiting for depth data...", cv::Point(100, 240), 
                           cv::FONT_HERSHEY_SIMPLEX, 0.8, cv::Scalar(255, 255, 255), 2);
                initialized = true;
                RCLCPP_INFO(this->get_logger(), "TIMER: Created placeholder image");
            }
            cv::imshow("depth_image", placeholder);
            if (frame_count % 30 == 0) {
                RCLCPP_INFO(this->get_logger(), "TIMER: Showing placeholder. depth_received_=%d, depth_.empty()=%d", 
                           depth_received_, depth_.empty());
            }
        }
        
        if (cv::waitKey(1) == 27) {
            rclcpp::shutdown();
        }
    }
};

int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<CubeDetector>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
