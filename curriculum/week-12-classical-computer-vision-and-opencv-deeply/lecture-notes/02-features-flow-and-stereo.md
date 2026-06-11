# Lecture 2 — Features, Flow, and Stereo: The Floor Under Visual Perception

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can detect and describe features (corners, ORB), match them across two views and reject the outliers with RANSAC, implement Lucas-Kanade optical flow and estimate ego-motion from it, and compute stereo depth from a disparity — and you can say where each of these reappears inside a modern learned-perception stack.

Lecture 1 turned a pixel into a ray. This lecture turns *pairs of images* into geometric relationships — which features moved where, how fast the camera is going, and how far away things are. If you remember one sentence:

> **Classical CV did not go away; it became the substrate. ORB still anchors ORB-SLAM3, Lucas-Kanade still runs in visual-inertial odometry, RANSAC still cleans up after every learned matcher, and stereo's `depth = f·b/d` still underlies every depth camera. Learn the floor and next week's learned models stop being magic — they're learned replacements for individual tiles of this floor.**

---

## 1. Features: corners are where the information is

You cannot match a flat, textureless region between two images — every patch looks like every other patch, so you can't tell which moved where (this is the **aperture problem**). You also can't reliably match an edge: you can tell motion *across* the edge but not *along* it. The points you *can* match unambiguously are **corners** — places where the image gradient is strong in *two* directions. Corners are where the information lives.

The **Harris corner detector** formalizes this. Look at the gradient structure tensor over a small window:

```
        ┌ Σ Ix²    Σ Ix·Iy ┐
   M  = │                  │
        └ Σ Ix·Iy  Σ Iy²   ┘
```

Both eigenvalues of `M` large ⇒ gradient varies in two directions ⇒ corner. One large, one small ⇒ edge. Both small ⇒ flat. The Harris response `R = det(M) − k·trace(M)²` is large and positive at corners. **Shi-Tomasi** (`cv2.goodFeaturesToTrack`) uses `min(λ1, λ2)` directly and is what you'll feed Lucas-Kanade.

```python
import cv2
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
corners = cv2.goodFeaturesToTrack(gray, maxCorners=200, qualityLevel=0.01, minDistance=10)
```

### 1.1 The structure tensor, read as eigenvalues

To build intuition, read the structure tensor `M` through its two eigenvalues `λ1 ≥ λ2`, because they classify the local image directly:

- **Both large** (`λ1, λ2` both big) — the gradient is strong in two independent directions. A **corner**. You can localize it in 2D, so it's matchable. High Harris response.
- **One large, one small** (`λ1 ≫ λ2 ≈ 0`) — strong gradient in one direction only. An **edge**. You can localize *across* the edge but not *along* it (the aperture problem), so a single edge patch is a poor feature. Low Harris response.
- **Both small** (`λ1, λ2 ≈ 0`) — no gradient. A **flat region**. Nothing to localize. Near-zero Harris response.

The Harris response `R = det(M) − k·trace(M)² = λ1·λ2 − k·(λ1+λ2)²` (with `k ≈ 0.04–0.06`) is a cheap proxy for "are both eigenvalues large" that avoids computing the eigenvalues explicitly — `det` and `trace` come straight from the four tensor entries. Shi-Tomasi simplifies this further to `R = min(λ1, λ2)`, which is more stable and is what `goodFeaturesToTrack` returns. Either way, the conceptual content is the same: **a good feature is a point that's pinned down in both image directions**, and that's exactly the property that lets you find the same physical point in the next frame. Everything downstream — ORB, optical flow, stereo matching — depends on starting from points you can actually localize.

---

## 2. ORB: detect, describe, and match efficiently

A corner location alone isn't enough to match across views — you need a **descriptor**, a compact summary of the patch *around* the keypoint, so you can find the same physical point in another image. **ORB (Oriented FAST and Rotated BRIEF)** is the workhorse for robots in 2026: it detects FAST corners, assigns each an orientation (so it's rotation-invariant), and computes a 256-bit **binary** descriptor (BRIEF). Binary descriptors are matched by **Hamming distance** (count differing bits) — a single CPU instruction — which is why ORB runs in real time on a Jetson with no GPU.

```python
import cv2

orb = cv2.ORB_create(nfeatures=1000)
kp1, des1 = orb.detectAndCompute(gray1, None)   # keypoints + (N, 32) uint8 descriptors
kp2, des2 = orb.detectAndCompute(gray2, None)

# Brute-force Hamming matcher for binary descriptors.
bf = cv2.BFMatcher(cv2.NORM_HAMMING)
# knnMatch returns the 2 nearest neighbors per descriptor, for the ratio test.
matches = bf.knnMatch(des1, des2, k=2)
```

### 2.1 ORB vs SIFT vs the learned front-ends — the honest 2026 picture

- **SIFT** (now patent-free, in OpenCV main) uses 128-float descriptors and is more accurate than ORB on hard scale/viewpoint changes — but slower and heavier. Use it offline or when accuracy beats latency.
- **ORB** wins on *speed and no-GPU* deployment. It's what ORB-SLAM3 uses, and it's the right default on an Orin Nano where every millisecond counts (Week 13's whole theme).
- **SuperPoint + LightGlue** (learned detector + learned matcher) beat both on genuinely hard data — large viewpoint changes, low texture, day/night — but they need a GPU and a model. In 2026 this is the SOTA front-end for visual SLAM when you have the compute. The stretch goal has you try it.

The lesson is *not* "ORB is obsolete." It's that **the detect-describe-match pipeline is the invariant**, and you swap the tile (ORB ↔ SuperPoint) based on your compute and accuracy budget — exactly the trade-off you'll formalize next week.

### 2.2 Lowe's ratio test: throwing away ambiguous matches

The nearest-neighbor match is often wrong, especially with repeated texture. **Lowe's ratio test** keeps a match only if the best neighbor is *much* closer than the second-best — if the two are comparably close, the match is ambiguous and discarded:

```python
good = []
for m, n in matches:             # m = best, n = second-best
    if m.distance < 0.75 * n.distance:
        good.append(m)
```

The ratio test alone removes most bad matches. But some survive — and that's where RANSAC comes in.

---

## 3. RANSAC: robust geometry from contaminated matches

Even after the ratio test, a handful of matches are **outliers** — wrong correspondences that don't fit any consistent geometry. If you fit a geometric model (a homography, a fundamental matrix) by least squares, those few outliers wreck it, exactly the way a false loop closure wrecked the Week 11 pose graph under a plain-Gaussian model. **RANSAC (Random Sample Consensus)** is the classical robust-estimation answer, and it's the geometric sibling of the Huber kernel you used in Week 11.

The algorithm:

1. Randomly pick the *minimal* number of matches needed to fit the model (4 for a homography, 5–8 for a fundamental matrix).
2. Fit the model to that minimal sample.
3. Count how many of *all* the matches agree with this model (inliers, within a pixel threshold).
4. Repeat for many random samples; keep the model with the most inliers.
5. Refit the model using all its inliers.

```python
import numpy as np
import cv2

pts1 = np.float32([kp1[m.queryIdx].pt for m in good])
pts2 = np.float32([kp2[m.trainIdx].pt for m in good])

# RANSAC homography (for a planar scene) — mask marks inliers.
H, mask = cv2.findHomography(pts1, pts2, cv2.RANSAC, ransacReprojThreshold=3.0)
inliers = int(mask.sum())
print(f"matches: {len(good)} -> RANSAC inliers: {inliers} ({100*inliers/len(good):.0f}%)")
```

The inlier ratio is the "the geometry closed" promise for matching: **a healthy ratio (say > 50%) means the recovered geometry is trustworthy; a ratio of 15% means your matches are mostly noise** and whatever you computed from them is meaningless. RANSAC doesn't just fit the model — it *tells you whether the data supported a model at all*. That's the same diagnostic value as the reprojection error and NEES: a number that says "trust this, or don't."

For visual odometry you fit the **essential matrix** instead (the calibrated version of the fundamental matrix), then decompose it into rotation and translation:

```python
E, mask = cv2.findEssentialMat(pts1, pts2, K, method=cv2.RANSAC, threshold=1.0)
_, R, t, mask = cv2.recoverPose(E, pts1, pts2, K)   # R, t up to scale
```

That `R, t` is the camera's motion between the two frames — monocular visual odometry, and the heart of the mini-project. The translation is only known *up to scale* (a monocular camera can't tell a small nearby motion from a large far one), which is exactly why robots fuse visual odometry with wheel odometry or IMU to recover metric scale — the sensor-fusion thread from Weeks 9–11.

### 3.1 Fundamental vs essential: the one-line distinction that confuses everyone

Two `3×3` matrices encode the geometry between two views, and conflating them is a classic mistake:

- The **fundamental matrix** `F` relates pixel coordinates directly: `x₂ᵀ F x₁ = 0` for corresponding pixels `x₁, x₂`. It needs *no* calibration — you can estimate it from raw matches alone with `cv2.findFundamentalMat`. But because it's uncalibrated, you cannot decompose it into a metric rotation and translation.
- The **essential matrix** `E` relates *normalized* (calibrated) coordinates: `E = K₂ᵀ F K₁`. Because the intrinsics are baked out, `E` *can* be decomposed into the relative rotation `R` and translation direction `t` via `cv2.recoverPose` — which is what makes visual odometry possible.

The rule: **use the fundamental matrix when you don't have `K` (or for stereo rectification of an uncalibrated rig); use the essential matrix when you have `K` and want the actual camera motion.** For a robot, you almost always have `K` (you calibrated it in Lecture 1), so you reach for the essential matrix. The reason this matters for your mini-project: if you accidentally feed `findFundamentalMat` and try to `recoverPose` from it, the geometry is wrong; `recoverPose` wants `E`, and `E` needs calibrated points. The chain is: calibrate (Lecture 1) → match (this lecture) → essential matrix → pose. Skip the calibration and the whole chain produces nonsense.

The essential matrix also has a structural property worth knowing: it has exactly **five degrees of freedom** (3 rotation + 3 translation − 1 for the lost scale), which is why the minimal solver is the *five-point algorithm* (Nistér's, what OpenCV uses under `findEssentialMat`). The fundamental matrix has seven DOF (the seven/eight-point algorithm). You don't implement these, but knowing the DOF count explains why RANSAC needs five vs. eight correspondences per minimal sample — directly affecting how many iterations RANSAC needs to find a clean sample.

### 3.2 How many RANSAC iterations is enough?

One practical number every perception engineer should be able to estimate. RANSAC's job is to draw *at least one* minimal sample (size `m`) that's all-inliers. If the inlier fraction is `w`, the probability a single `m`-sample is all-inliers is `wᵐ`, so the number of iterations `N` to succeed with probability `p` is:

```
N = log(1 − p) / log(1 − wᵐ)
```

Plug in numbers: for a homography (`m = 4`), `p = 0.99`, and a *clean* 80% inlier fraction (`w = 0.8`), `N ≈ 11` — eleven samples is plenty. But for a *contaminated* 40% inlier fraction (`w = 0.4`), `N ≈ 177`, and for the essential matrix (`m = 5`) at `w = 0.4`, `N ≈ 450`. The cost explodes as the data gets dirtier and the model needs more points. This is *why* the ratio test matters so much: every bad match you remove beforehand raises `w`, which slashes the RANSAC iteration count exponentially. The ratio test isn't just cleaner — it makes RANSAC *cheaper*, which on a latency-budgeted robot is the difference between a 5 ms and a 50 ms front-end. OpenCV picks `N` adaptively (it re-estimates `w` from the best model so far), but knowing the formula lets you sanity-check why a dirty match set is slow.

---

## 4. Optical flow: motion without matching

Features-and-matching is one way to relate two frames. **Optical flow** is another: instead of detecting and matching discrete keypoints, it directly estimates the apparent motion of brightness patterns. It rests on **brightness constancy** — the assumption that a world point keeps the same intensity as it moves between frames:

```
I(x, y, t) = I(x + dx, y + dy, t + dt)
```

Taylor-expanding gives the **optical flow constraint equation**:

```
Ix·u + Iy·v + It = 0          (u, v = the flow; Ix, Iy, It = image gradients)
```

That's one equation in two unknowns (`u, v`) per pixel — the aperture problem again. **Lucas-Kanade** resolves it by assuming the flow is *constant over a small window* and solving the resulting over-determined system by least squares. OpenCV's pyramidal LK handles large motions by running coarse-to-fine over an image pyramid:

```python
import cv2
import numpy as np

# Track Shi-Tomasi corners from the previous frame into the current one.
p0 = cv2.goodFeaturesToTrack(prev_gray, maxCorners=200, qualityLevel=0.01, minDistance=10)
p1, status, err = cv2.calcOpticalFlowPyrLK(prev_gray, gray, p0, None,
                                           winSize=(21, 21), maxLevel=3)
good_old = p0[status == 1]
good_new = p1[status == 1]
flow = good_new - good_old              # per-feature pixel displacement
```

### 4.1 Ego-motion from flow: a free odometry sanity check

Here's the payoff that connects to the whole course. When a robot drives **straight forward**, the world flows *outward* from a single point in the image — the **focus of expansion** (the point you're driving toward, where flow is zero). The *magnitude* of the outward flow is proportional to the forward speed and inversely proportional to depth. For features on the ground plane at known geometry, you can invert this to estimate **forward velocity from the flow alone** — no wheels, no IMU, just the camera.

Why bother, when you already have wheel odometry? Because it's an **independent** estimate, and independence is what catches lies. Wheel odometry drifts on slip (Week 6); a wheel spinning on a wet floor reports motion the robot isn't making. Optical flow, derived from the camera, *sees* that the world isn't moving and disagrees. **Two sensors that should agree and don't is a fault detector for free** — and diagnosing exactly that planted wheel-slip event is this week's challenge. This is the classical-CV version of the sensor-consistency idea you'll see everywhere in a robust autonomy stack.

The estimate is rough (flow is noisy, the ground-plane assumption is approximate), so it's a *sanity check*, not a primary odometry source. But a rough independent check that costs one camera you already have is exactly the kind of cheap redundancy senior robotics engineers build in.

### 4.2 The geometry, made precise

The exercise's recovery rests on a clean geometric fact worth stating exactly. For a camera moving forward by distance `d` per frame toward a fronto-parallel plane at depth `Z`, the image appears to **zoom** by a scale factor:

```
s = Z / (Z − d)
```

because a feature that was at depth `Z` is now at depth `Z − d`, and its image size scales inversely with depth. Tracked features move radially *away* from the focus of expansion by exactly this factor: if a feature's vector from the FOE was `a`, it becomes `s·a`. So you recover `s` from the flow by a one-line least-squares fit (`s = Σ(b·a)/Σ(a·a)` over all tracked features), then invert:

```
d = Z · (1 − 1/s)        and        v = d / dt
```

This is exactly the math in Exercise 3, and it's a stripped-down version of what visual-inertial odometry does continuously. Real VIO doesn't assume a single plane — it estimates per-feature depth jointly with motion — but the *intuition* (forward motion = radial expansion, rate set by speed/depth) is identical, and the FOE shifting off-center is precisely how you'd detect turning. Building the simple version by hand is what makes the production version (OpenVINS, VINS-Fusion) legible rather than magical.

### 4.3 Sparse vs. dense flow

Lucas-Kanade is **sparse** — it tracks a few hundred good corners. The alternative is **dense** optical flow (Farnebäck, `cv2.calcOpticalFlowFarneback`), which estimates a flow vector for *every* pixel. The trade-off:

- **Sparse (LK)** — fast, robust on textured features, but blind in textureless regions (no corners to track). Right for ego-motion and feature tracking.
- **Dense (Farnebäck)** — a vector per pixel, so it fills textureless areas with interpolated flow, but it's slower and noisier. Right for segmentation-by-motion and visualizing the full flow field.

For the robot odometry sanity check you want *sparse* — you only need a few reliable tracks to estimate the radial scale, and you don't want to pay for a full dense field. The lesson generalizes: **match the algorithm's density to what the downstream task actually needs.** Computing a dense field to extract one scalar (forward speed) is the kind of over-computation that blows a latency budget — exactly the discipline next week makes a first-class concern.

---

## 5. Stereo depth: putting back the dimension the pinhole threw away

A single pinhole loses depth. **Two** pinholes a known distance apart recover it, because a world point projects to *different* pixels in the two cameras, and that difference encodes the depth.

Set up two cameras side by side, rectified so their image rows align (the **epipolar constraint** guarantees a point in the left image lies on the same row in the right image — rectification makes the search 1D). A world point at depth `Z` projects to column `xL` in the left and `xR` in the right; the **disparity** is `d = xL − xR`. The geometry gives the depth directly:

```
   depth Z  =  f · b / d
```

where `f` is the focal length (pixels) and `b` is the **baseline** (the distance between the cameras, meters). Read the relationship: **disparity is inversely proportional to depth.** Near objects have large disparity (shift a lot between views); far objects have tiny disparity; objects at infinity have zero disparity. This is also why stereo has a *range limit* — beyond some distance the disparity is sub-pixel and depth becomes unrecoverable.

```python
import cv2

# Semi-Global Block Matching: better than plain BM on weak texture.
stereo = cv2.StereoSGBM_create(minDisparity=0, numDisparities=128, blockSize=5)
disparity = stereo.compute(left_rect, right_rect).astype("float32") / 16.0

# Convert disparity to metric depth (avoid divide-by-zero on disparity 0).
focal_px = K[0, 0]
baseline_m = 0.06
with np.errstate(divide="ignore"):
    depth = focal_px * baseline_m / disparity
depth[disparity <= 0] = 0.0       # no valid disparity -> no depth
```

### 5.0 The depth equation, by the numbers

Plug in real numbers so the range limit becomes concrete. Take a stereo rig with focal length `f = 600 px` and baseline `b = 0.06 m` (6 cm, a typical small RGB-D rig). An object at:

```
disparity = 60 px   ->  depth = 600 · 0.06 / 60  = 0.60 m   (close, large shift)
disparity = 12 px   ->  depth = 600 · 0.06 / 12  = 3.00 m   (medium)
disparity =  3 px   ->  depth = 600 · 0.06 /  3  = 12.0 m   (far, tiny shift)
disparity =  1 px   ->  depth = 600 · 0.06 /  1  = 36.0 m   (one pixel = 36 m!)
```

Read that last line: at 36 m, a *one-pixel* error in disparity is the difference between 36 m and 18 m (disparity 2). The depth error grows with the *square* of the depth — `ΔZ ∝ Z²·Δd/(f·b)` — so stereo is precise up close and useless far away. This is why a wider baseline (`b` larger) extends the useful range (it spreads the same depth over more disparity), and why a long-range robot needs a long stereo baseline or a different sensor entirely. Knowing this equation in your fingers lets you *predict* a stereo rig's useful range before you buy it, which is a real procurement decision.

### 5.1 Where stereo fails (and why next week exists)

Stereo's failure modes are the reason robots also carry active depth sensors and learned depth models:

- **Textureless surfaces** (a blank white wall) — no features to match between left and right, so no disparity, so no depth. The single biggest stereo failure.
- **Repeated patterns** (a tiled floor, a brick wall) — the matcher locks onto the wrong repeat, giving confidently-wrong depth.
- **Occlusion** — a point visible in one camera but not the other has no disparity. You get holes at depth discontinuities.
- **Range limit** — beyond a few meters (for a small baseline) disparity is sub-pixel and depth is noise.

These are *exactly* the gaps that **structured-light/ToF depth cameras** (Week 14) and **learned monocular depth** (Depth-Anything, Week 13) fill. Stereo isn't obsolete — it's passive, cheap, and metric — but knowing its failure modes is what lets you choose the right depth sensor for a scene, which is a senior perception skill.

---

## 6. The substrate map: where each tile reappears

Tie it together. Every classical technique in this week is a tile in a modern stack:

```
classical tile (this week)        modern stack where it lives
─────────────────────────────     ─────────────────────────────────────────
pinhole model + calibration   →   under EVERY learned depth/detection model
ORB features + matching       →   ORB-SLAM3 tracking; visual place recognition
Lucas-Kanade optical flow     →   visual-inertial odometry (VINS, OpenVINS)
RANSAC robust fitting         →   outlier rejection after any learned matcher
essential matrix / recoverPose→   monocular visual odometry front-end
stereo depth = f·b/d          →   passive depth; the baseline for RGB-D fusion
```

The learned models of Weeks 13–16 don't replace this floor — they replace *individual tiles* with learned versions (SuperPoint for ORB, Depth-Anything for stereo) while the geometric scaffolding (pinhole, RANSAC, pose recovery) stays classical. An engineer who knows the floor can read any perception paper as "which tile did they learn, and why" — which is the literacy this week buys you.

---

## 7. The mistakes that break a first feature pipeline

When you run ORB + matching + RANSAC in the exercises and the mini-project, these account for nearly every wrong result:

1. **Wrong matcher norm.** ORB descriptors are *binary*; they need `NORM_HAMMING`, not `NORM_L2`. Using `NORM_L2` (the SIFT default) silently produces garbage matches and a low inlier ratio. *Fix:* `BFMatcher(cv2.NORM_HAMMING)` for ORB, `NORM_L2` for SIFT.

2. **Skipping the ratio test.** Raw nearest-neighbor matches are full of ambiguous pairs. Feeding them straight to RANSAC works *sometimes* but wastes iterations and lowers the inlier ratio. *Fix:* always apply Lowe's ratio test before RANSAC.

3. **Fundamental where you wanted essential.** Estimating `F` from raw pixels and trying to `recoverPose` gives nonsense — `recoverPose` needs the calibrated `E` (§3.1). *Fix:* `findEssentialMat(..., K, ...)` with calibrated points when you want metric motion.

4. **Claiming metric scale from monocular VO.** The recovered translation is a *direction*, not a distance (§3). Treating it as meters is the classic beginner error. *Fix:* fuse wheel odom / IMU / known object size to recover scale.

5. **Optical flow across too-large a motion.** Lucas-Kanade assumes small displacement; a fast motion between frames breaks brightness constancy and the tracker diverges. *Fix:* use the *pyramidal* LK (`maxLevel ≥ 3`) and/or a higher frame rate so per-frame motion stays small.

6. **Dividing by zero disparity in stereo.** Untextured pixels get disparity 0; `f·b/0` is infinity. *Fix:* mask `disparity <= 0` to "no depth" before the division.

Each has a distinct symptom — a low inlier ratio, garbage pose, infinite depth, a diverged tracker. Mapping symptom → cause is the diagnostic muscle this whole phase builds.

---

## 8. Recap

You should now be able to:

- Explain why corners (not edges or flat regions) are matchable, and detect them with Harris/Shi-Tomasi.
- Use ORB to detect + describe + match features, apply Lowe's ratio test, and say when to reach for SIFT or SuperPoint instead.
- Apply RANSAC to fit robust geometry (homography, essential matrix) from contaminated matches, and read the inlier ratio as a trust metric.
- Implement Lucas-Kanade optical flow and estimate forward velocity from the flow field as an independent odometry sanity check.
- Compute stereo depth from disparity with `depth = f·b/d`, and name the four failure modes (texture, repetition, occlusion, range).
- Map each classical tile to where it reappears in a modern learned-perception stack.

One closing thread ties this lecture to the rest of C24. Every technique here is, at heart, a way to *extract a geometric constraint from images* — a match is a "these two pixels are the same world point" constraint, a flow vector is a "this point moved this much" constraint, a disparity is a "this point is this far" constraint, an essential matrix is a "the camera moved like this" constraint. And constraints are exactly what the Week 11 factor graph eats. The arc of the perception phase is: classical CV (this week) and learned perception (next week) *manufacture constraints*; the estimator (filter or factor graph) *fuses them into a state*. ORB matches become VO between-factors; stereo depths become landmark factors; flow becomes a velocity constraint. Seen this way, this week isn't a detour into image processing — it's the front-end that feeds everything you built in Weeks 9–11. That's why classical CV is the floor: it's where the measurements that the whole estimation stack consumes are born.

Next: the exercises put all of this on real images — calibrate a camera, match with ORB+RANSAC, and estimate velocity from flow. Continue to [the exercises](../exercises/README.md).

---

## Pipeline reference card

The end-to-end classical matching pipeline, in order — tape it next to the equation card from Lecture 1:

```
1. detect    orb = cv2.ORB_create(); kp, des = orb.detectAndCompute(gray, None)
2. match     knn = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(des1, des2, k=2)
3. ratio     good = [m for m,n in knn if m.distance < 0.75*n.distance]
4. geometry  E, mask = cv2.findEssentialMat(p1, p2, K, cv2.RANSAC, threshold=1.0)
5. pose      n, R, t, _ = cv2.recoverPose(E, p1, p2, K, mask=mask)   # t up to scale
6. trust     inlier_ratio = mask.sum() / len(good)   # > 50% = trustworthy

Optical flow:  p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, cur, p0, None, maxLevel=3)
Stereo depth:  depth = f * baseline / disparity     (mask disparity <= 0)
```

Steps 1–6 are the front-end of every visual-SLAM system. Memorize the order; the parameters you can tune. The single most common pipeline bug is skipping step 3 (the ratio test) — which both lowers your inlier ratio and, per §3.2, makes RANSAC exponentially slower.

---

## References

- Szeliski — *Computer Vision*, Ch. 7 (features), Ch. 9 (flow), Ch. 12 (stereo): <https://szeliski.org/Book/>
- OpenCV — ORB tutorial: <https://docs.opencv.org/4.x/d1/d89/tutorial_py_orb.html>
- OpenCV — Optical Flow (Lucas-Kanade): <https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html>
- OpenCV — Epipolar geometry & Depth from stereo: <https://docs.opencv.org/4.x/da/de9/tutorial_py_epipolar_geometry.html>
- Lucas & Kanade (1981): <https://www.ri.cmu.edu/pub_files/pub3/lucas_bruce_d_1981_2/lucas_bruce_d_1981_2.pdf>
- Fischler & Bolles — RANSAC (1981): <https://www.sri.com/wp-content/uploads/2021/12/ransac-publication.pdf>
- SuperPoint + LightGlue (the learned front-end): <https://github.com/cvg/LightGlue>
