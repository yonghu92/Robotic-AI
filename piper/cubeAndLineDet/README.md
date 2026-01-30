# Simple Color Block Detection and 3D Coordinate Extraction

A simple program for color block detection and 3D coordinate extraction using OpenCV library. It uses depth and color information from a depth camera to identify objects, and the extracted 3D coordinates can be used for simple robotic arm grasping tasks.

## Hardware

- [Orbbec Petrel](https://orbbec.com.cn/index/Product/info.html?cate=38&id=28) Aligned depth and RGB images: 640x400 @ 30fps
- [RealSense D435](https://realsenseai.com/stereo-depth-cameras/stereo-depth-camera-d435/) Aligned depth and RGB images: 640x480 @ 30fps

## Software Dependencies

- [pcl-1.10](https://github.com/PointCloudLibrary/pcl) When compiling standalone, you need to specify the on_nurbs compilation option

## Running

```bash
# First launch the camera driver node, using Orbbec Petrel as an example
roslaunch astra_camera dabai_dc1.launch

# Launch the color block detection node
rosrun cubeAndLineDet cube_det
```

After running, three OpenCV image windows will appear. Click on the origin_img image with your mouse to select a color block, then the depth image will automatically calculate the average depth of the color block and return the center coordinates of the bounding box. For example, clicking on the cyan block position in the origin_img image will cause the other two images to automatically find the block position and visualize it:

![""](images/5d87327e-5b16-4d04-a67a-bef4f44bc516.png)

Then click on the purple block position in the origin_img window, and the other two images will automatically find the block position and visualize it:

![""](images/403b1c75-41b5-429e-97c3-ed51550e254b.png)

---

# Single-Color Curve 3D Coordinate Extraction and Fitting

A simple program for single-color curve 3D coordinate extraction and fitting using OpenCV library. It uses depth and color information from a depth camera to identify curves, and the extracted 3D coordinates can be used for simple robotic arm line-following tasks.

## Hardware

- [RealSense D435](https://realsenseai.com/stereo-depth-cameras/stereo-depth-camera-d435/) Aligned depth and RGB images: 640x480 @ 30fps
- [Orbbec Petrel](https://orbbec.com.cn/index/Product/info.html?cate=38&id=28) Aligned depth and RGB images: 640x400 @ 30fps

**Note:** Some Orbbec depth cameras have a mismatch between the camera_info parameters published by their ROS driver node and the actual values. You need to calibrate and manually modify the code to pass the correct K matrix. RealSense does not have this issue.

## Running

```bash
# First launch the camera driver node, using RealSense D435 as an example (this node already has depth-to-RGB alignment)
roslaunch realsense2_camera rs_aligned_depth.launch

# Launch the single-color curve detection node (only publishes 3D point cloud visualization of the curve, no position relationships)
rosrun cubeAndLineDet line_det
```

- After launching, you can see three OpenCV windows. Click on the origin_img image with your mouse to select a single-color curve, then the depth image will automatically calculate the average depth of the curve and return center coordinates. For example, clicking on the orange network cable position in the origin_img image will cause the other two images to automatically find the curve position and visualize it.

- After finding the single-color curve, denoising and fitting are performed on the detection results. The denoising works well, but the fitting effect is poor and needs further optimization (experimental).
