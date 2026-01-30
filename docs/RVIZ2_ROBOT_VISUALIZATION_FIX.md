# Fix: Robot Not Showing in RViz2

## ✅ What's Working:
- robot_state_publisher is running ✓
- /robot_description topic exists ✓
- /joint_states topic exists ✓

## 🔧 Steps to See Robot in RViz2:

### Step 1: Check Fixed Frame

In RViz2:
1. Look at **"Global Options"** in the left panel
2. Find **"Fixed Frame"** dropdown
3. Try these in order:
   - `base_link` (most common)
   - `base_footprint`
   - `world`

**If Fixed Frame shows "No tf data" or is red:**
- The frame name is wrong
- Try the options above

### Step 2: Add RobotModel Display

1. Click **"Add"** button (bottom left)
2. Select **"RobotModel"** from the list
3. Click **"OK"**
4. **Make sure the checkbox is checked** (enabled)

### Step 3: Configure RobotModel Display

In the RobotModel display settings:
- **Robot Description**: Should be `/robot_description` (default)
- **TF Prefix**: Leave empty
- **Visual Enabled**: ✓ (checked)
- **Collision Enabled**: Can be unchecked for now

### Step 4: Check TF Tree

```bash
# In a terminal, check TF frames
ros2 run tf2_ros tf2_echo base_link link1
# Or
ros2 run tf2_tools view_frames
# This creates frames.pdf showing the TF tree
```

### Step 5: Verify Robot Description

```bash
# Check if robot_description has content
ros2 param get /robot_state_publisher robot_description | head -20
```

Should show XML content starting with `<?xml version="1.0"?>`

## Common Issues:

### Issue: "No tf data" in Fixed Frame
**Solution:** 
- Check which frames exist: `ros2 run tf2_ros tf2_echo base_link link1`
- Try different Fixed Frame values

### Issue: RobotModel display shows "No tf data"
**Solution:**
- Make sure Fixed Frame matches a frame in the URDF
- Check TF is being published: `ros2 topic echo /tf`

### Issue: Robot appears but is in wrong position
**Solution:**
- Check Fixed Frame is correct
- Reset view: View → Reset

### Issue: Robot appears but no joints visible
**Solution:**
- Check joint_states is being published: `ros2 topic echo /joint_states`
- Robot might be in default/home position (all joints at 0)

## Quick Test:

1. **In RViz2:**
   - Fixed Frame: `base_link`
   - Add RobotModel display
   - Enable it (checkbox checked)

2. **If still not visible:**
   ```bash
   # Check what frames exist
   ros2 run tf2_tools view_frames
   # Open frames.pdf to see available frames
   ```

3. **Try different Fixed Frame:**
   - `base_footprint` (if URDF has it)
   - `world` (if published)

## Expected Result:

You should see:
- Robot arm model (all links and joints)
- Robot in default/home position
- Interactive marker (if that's running too)
