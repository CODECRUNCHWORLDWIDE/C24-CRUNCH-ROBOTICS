# Exercise 1 — Calibrate a Camera

**Goal:** Turn a camera from a picture-taker into a measurement device. You'll collect checkerboard views from a real USB camera (or your Gz Sim camera), run OpenCV's calibration, recover the intrinsic matrix `K` and the distortion coefficients, **read the reprojection error as a quality metric**, and undistort an image so straight lines come out straight. By the end you can map any pixel to a ray you trust.

**Estimated time:** 55 minutes. Guided.

---

## Setup

You need:

- A **checkerboard target**: print a 9×6 *inner-corner* checkerboard (10×7 squares) on flat paper or stiff card, or use a textured calibration plane in Gz Sim. **Measure the square size in meters** — calibration needs it for metric scale. A typical printed board has 25 mm (0.025 m) squares.
- A camera publishing images. On a real robot that's your USB camera; in sim it's the Gz Sim camera plugin publishing `/camera/image_raw`.
- OpenCV: `pip install opencv-python numpy`.

```bash
ros2 topic list | grep camera
# /camera/camera_info
# /camera/image_raw
```

If you're calibrating a real USB webcam directly (no ROS), you can grab frames with `cv2.VideoCapture(0)`.

---

## Step 1 — Collect varied views

Capture **15–20 images** of the checkerboard, and make them *varied*: tilt the board left, right, up, down; move it near and far; put it in different parts of the frame (corners, not just the center). This variety is what constrains the distortion — all-frontal, all-centered views give a poor calibration no matter how many you take.

Save them to `calib_imgs/`. A quick grabber for a real camera:

```python
import cv2, os
os.makedirs("calib_imgs", exist_ok=True)
cap = cv2.VideoCapture(0)
i = 0
print("press SPACE to capture, q to quit")
while True:
    ok, frame = cap.read()
    if not ok:
        break
    cv2.imshow("capture", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord(" "):
        cv2.imwrite(f"calib_imgs/{i:02d}.png", frame)
        print("saved", i); i += 1
    elif key == ord("q"):
        break
cap.release(); cv2.destroyAllWindows()
```

For Gz Sim, subscribe to `/camera/image_raw`, convert with `cv_bridge`, and save frames while you move the board (or move the camera around a static board) in the world.

---

## Step 2 — Detect and refine corners, then calibrate

Save this as `calibrate.py`. It is complete and runnable — point it at your `calib_imgs/`.

```python
#!/usr/bin/env python3
import glob
import cv2
import numpy as np

BOARD = (9, 6)            # INNER corners (one less than squares in each direction)
SQUARE_M = 0.025          # your measured square size, in meters

# 3D coordinates of the board's inner corners (flat grid, Z=0).
objp = np.zeros((BOARD[0] * BOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:BOARD[0], 0:BOARD[1]].T.reshape(-1, 2) * SQUARE_M

objpoints, imgpoints = [], []
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

paths = sorted(glob.glob("calib_imgs/*.png"))
gray = None
used = 0
for path in paths:
    img = cv2.imread(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    found, corners = cv2.findChessboardCorners(gray, BOARD, None)
    if found:
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        objpoints.append(objp)
        imgpoints.append(corners)
        used += 1
    else:
        print(f"  no board found in {path} (skipped)")

print(f"using {used}/{len(paths)} views")
ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
    objpoints, imgpoints, gray.shape[::-1], None, None)

print("K =\n", np.round(K, 2))
print("distortion =", np.round(dist.ravel(), 4))

# --- Reprojection error: the quality metric ---
total_err, total_pts = 0.0, 0
for i in range(len(objpoints)):
    proj, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], K, dist)
    total_err += cv2.norm(imgpoints[i], proj, cv2.NORM_L2) ** 2
    total_pts += len(proj)
mean_px = float(np.sqrt(total_err / total_pts))
band = "GOOD (<0.5px)" if mean_px < 0.5 else (
    "OK (0.5-1.0px)" if mean_px < 1.0 else "BAD (>1.0px) — recollect")
print(f"mean reprojection error: {mean_px:.3f} px  ->  {band}")

np.savez("camera_calib.npz", K=K, dist=dist)
```

```bash
python3 calibrate.py
```

You're looking for the **"the geometry closed" promise**:

```
using 17/18 views
K =
 [[612.34   0.   318.91]
  [  0.   611.82 241.18]
  [  0.     0.     1.  ]]
distortion = [ 0.041 -0.118  0.001  0.000  0.052]
mean reprojection error: 0.27 px  ->  GOOD (<0.5px)
```

---

## Step 3 — Read your K and sanity-check it

Look at the recovered `K` and ask whether it's *physically sensible*:

- `fx` and `fy` should be close to each other (square pixels) — within a few percent. A big gap means a bad calibration.
- `cx, cy` should be *near* the image center (e.g. ~320, 240 for a 640×480 image) but not exactly — a few pixels off is normal and correct.
- The distortion `k1` tells you the lens character: negative = barrel (wide-angle bow), near zero = a well-corrected lens.

If `cx` came out at, say, 90 instead of ~320, your calibration is wrong — usually too few views or a board detected in only one region of the frame.

---

## Step 4 — Undistort and apply the straight-line test

```python
import cv2, numpy as np
data = np.load("camera_calib.npz")
K, dist = data["K"], data["dist"]

img = cv2.imread("calib_imgs/00.png")
undist = cv2.undistort(img, K, dist)
cv2.imwrite("undistorted.png", undist)
```

Now the **acceptance test from Lecture 1 §3**: point the camera at something with a long straight edge (a doorframe, a table edge, the checkerboard's own border), undistort, and confirm the edge is *straight* in the undistorted image. If a wide-angle lens bowed the doorframe and undistortion straightened it, your distortion coefficients are right. If it's still bowed, recalibrate with more varied views.

---

## Step 5 — Back-project a pixel to a ray

Prove `K` does what Lecture 1 §2.1 says: turn a pixel into a ray.

```python
import numpy as np
def pixel_to_ray(K, x, y):
    ray = np.linalg.inv(K) @ np.array([x, y, 1.0])
    return ray / np.linalg.norm(ray)

print("ray through image center:", pixel_to_ray(K, K[0,2], K[1,2]))   # ~ (0,0,1)
print("ray through top-left:   ", pixel_to_ray(K, 0, 0))
```

The ray through the principal point `(cx, cy)` should be almost exactly `(0, 0, 1)` — straight down the optical axis. A pixel in the corner gives a ray tilted away from the axis. This is the operation that turns a Week 13 detection into a 3D direction the robot can act on.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `calibrate.py` runs on 15+ views and prints `K`, the distortion coefficients, and a reprojection error.
- [ ] The mean reprojection error is **< 0.5 px** (GOOD) — or you can explain what's wrong and how you'd fix it if it's higher.
- [ ] `K`'s `fx ≈ fy` and `cx, cy` are near the image center; you've sanity-checked them.
- [ ] An undistorted image passes the straight-line test (a known straight edge is straight after undistortion).
- [ ] The ray through `(cx, cy)` back-projects to approximately `(0, 0, 1)`.

---

## Stretch

- Save your `K` and `dist` into a ROS2 `camera_info` YAML and feed it to `image_proc`; confirm `/camera/image_rect` is published and the rectified image is undistorted on the live stream.
- Deliberately calibrate with only 5 all-frontal, all-centered views and compare the reprojection error and the recovered distortion to your good run. See the calibration degrade — this is *why* varied views matter.
- Calibrate a **fisheye** lens (or a wide-FOV Gz Sim camera) with `cv2.fisheye.calibrate` and compare the undistortion to the standard model. The standard model fails on strong fisheye; the fisheye model handles it.

---

When this feels comfortable, move to [Exercise 2 — ORB + RANSAC](exercise-02-orb-match-ransac.py).
