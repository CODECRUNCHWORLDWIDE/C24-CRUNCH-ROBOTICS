#!/usr/bin/env python3
# Exercise 3 — Lucas-Kanade optical flow and forward velocity from flow
#
# Goal: Track features across a synthetic FORWARD-DRIVE sequence with pyramidal
#       Lucas-Kanade, and estimate the camera's FORWARD VELOCITY from the flow
#       field alone — no wheels, no IMU. This is the independent odometry sanity
#       check from Lecture 2 §4.1: when the robot drives straight forward, the
#       world flows radially OUTWARD from the focus of expansion, and the rate of
#       that expansion is proportional to forward speed / depth.
#
# THE GEOMETRY
#
#   A camera moving forward by distance d toward a fronto-parallel plane at depth Z
#   makes the image appear to ZOOM by a factor s = Z / (Z - d) per frame. Tracked
#   features move radially away from the focus of expansion (the image center for
#   straight-ahead motion). We recover s from the flow (least-squares radial scale)
#   and invert the geometry to get the per-frame forward distance, hence velocity.
#
#       s = Z / (Z - d)   =>   d = Z * (1 - 1/s)   =>   v = d / dt
#
# HOW TO USE THIS FILE
#
#       pip install opencv-python numpy
#       python3 exercise-03-lk-flow-velocity.py
#
# ACCEPTANCE CRITERIA
#
#   [ ] Pyramidal LK tracks the majority of seeded features each frame.
#   [ ] The recovered per-frame radial scale s matches the true zoom to ~1%.
#   [ ] The estimated forward velocity matches the simulated TRUE velocity to within
#       ~10% (flow is noisy; this is a SANITY CHECK, not a primary odometry source).
#   [ ] You can explain WHY an independent flow estimate is valuable even though you
#       already have wheel odometry (it catches wheel slip — Lecture 2 §4.1).
#
# Expected output is at the bottom of the file.

import numpy as np
import cv2

RNG = np.random.default_rng(3)
W, H = 640, 480
CX, CY = W / 2.0, H / 2.0           # focus of expansion for straight-ahead motion

# Ground truth of the simulated drive.
DT = 0.1                            # seconds per frame (10 FPS)
DEPTH_Z = 5.0                       # meters to the plane the camera drives toward
TRUE_V = 1.8                        # m/s forward speed we will try to recover
N_FRAMES = 8


def make_textured_plane() -> np.ndarray:
    """A grayscale plane full of trackable blobs (the wall the camera drives at)."""
    img = np.full((H, W), 30, np.uint8)
    for _ in range(200):
        x, y = int(RNG.integers(0, W)), int(RNG.integers(0, H))
        cv2.circle(img, (x, y), int(RNG.integers(3, 8)), int(RNG.integers(120, 255)), -1)
    return img


def synth_forward_sequence():
    """Render the plane as the camera drives forward, frame by frame.

    Per frame the camera advances v*dt meters; the apparent zoom is
    s = Z / (Z - v*dt). We compose the zoom about the focus of expansion.
    """
    base = make_textured_plane()
    frames = [base]
    accumulated_scale = 1.0
    for _ in range(1, N_FRAMES):
        d = TRUE_V * DT
        s_per_frame = DEPTH_Z / (DEPTH_Z - d)
        accumulated_scale *= s_per_frame
        M = cv2.getRotationMatrix2D((CX, CY), 0, accumulated_scale)
        frames.append(cv2.warpAffine(base, M, (W, H)))
    return frames


def estimate_velocity(frames):
    """Track LK flow frame-to-frame, recover the radial scale, invert to velocity."""
    lk_params = dict(winSize=(21, 21), maxLevel=3,
                     criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    foe = np.array([CX, CY])
    per_frame_scale = []
    tracked_counts = []

    prev = frames[0]
    p0 = cv2.goodFeaturesToTrack(prev, maxCorners=300, qualityLevel=0.01, minDistance=8)
    for frame in frames[1:]:
        p1, status, _ = cv2.calcOpticalFlowPyrLK(prev, frame, p0, None, **lk_params)
        ok = status.ravel() == 1
        a = p0[ok].reshape(-1, 2) - foe       # vectors from FOE, previous frame
        b = p1[ok].reshape(-1, 2) - foe       # vectors from FOE, current frame
        tracked_counts.append(int(ok.sum()))
        # Least-squares radial scale s minimizing || b - s*a ||.
        s = float(np.sum(b * a) / np.sum(a * a))
        per_frame_scale.append(s)
        prev = frame
        p0 = cv2.goodFeaturesToTrack(prev, maxCorners=300, qualityLevel=0.01, minDistance=8)

    s_mean = float(np.mean(per_frame_scale))
    # Invert s = Z/(Z-d)  =>  d = Z*(1 - 1/s)  =>  v = d/dt.
    d_per_frame = DEPTH_Z * (1.0 - 1.0 / s_mean)
    v_est = d_per_frame / DT
    return v_est, s_mean, per_frame_scale, tracked_counts


def main():
    frames = synth_forward_sequence()
    v_est, s_mean, scales, counts = estimate_velocity(frames)

    true_s = DEPTH_Z / (DEPTH_Z - TRUE_V * DT)
    err_pct = 100.0 * abs(v_est - TRUE_V) / TRUE_V

    print("==================== flow -> forward velocity ====================")
    print(f"features tracked per frame: {counts}")
    print(f"recovered radial scale s: mean={s_mean:.4f}  (true zoom={true_s:.4f})")
    print(f"estimated forward velocity: {v_est:.3f} m/s  "
          f"(true={TRUE_V:.3f} m/s, error={err_pct:.1f}%)")
    verdict = "GOOD (within 10%)" if err_pct < 10 else "OFF — debug the flow"
    print(f"-> {verdict}")
    print("==================================================================")
    print("Lesson: this estimate comes ONLY from the camera — no wheels, no IMU. "
          "It's rough (flow is noisy) so it's a SANITY CHECK, not primary odometry. "
          "Its value is INDEPENDENCE: if your wheel odometry says 1.8 m/s but the "
          "wheels are slipping, the flow disagrees, and two sensors that should "
          "agree but don't is a free fault detector (Lecture 2 §4.1).")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (deterministic seed; exact decimals depend on your OpenCV build)
# -----------------------------------------------------------------------------
#
# ==================== flow -> forward velocity ====================
# features tracked per frame: [3xx, 3xx, ...]
# recovered radial scale s: mean=1.0374  (true zoom=1.0376)
# estimated forward velocity: 1.7xx m/s  (true=1.800 m/s, error=x.x%)
# -> GOOD (within 10%)
# ==================================================================
# Lesson: this estimate comes ONLY from the camera ...
#
# The INVARIANT: the recovered radial scale matches the true zoom to ~1%, and the
# inverted velocity lands within ~10% of the simulated 1.8 m/s. The geometry that
# makes this work — forward motion = radial expansion from the focus of expansion,
# at a rate set by speed/depth — is the same geometry that underlies visual-inertial
# odometry. The next step (the challenge) runs it on a real drive video and uses it
# to catch a planted wheel-slip event.
# -----------------------------------------------------------------------------
