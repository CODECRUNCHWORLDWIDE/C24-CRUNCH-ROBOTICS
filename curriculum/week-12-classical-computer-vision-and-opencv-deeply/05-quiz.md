# Week 12 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 13. Answer key is at the bottom — don't peek.

---

**Q1.** What does the intrinsic matrix `K` contain, and what is it *for*?

- A) The camera's pose in the world (rotation and translation).
- B) The focal lengths `fx, fy` and principal point `cx, cy`; it maps a camera-frame 3D point to a pixel (and `K⁻¹` back-projects a pixel to a ray).
- C) The lens distortion coefficients only.
- D) The image's RGB values.

---

**Q2.** Why can't a single image recover the absolute depth of a point?

- A) Cameras are too low-resolution.
- B) The pinhole projection divides by depth `Z`, so every point along a ray projects to the same pixel — the depth dimension is lost.
- C) Depth requires color information.
- D) It can, with a big enough `K`.

---

**Q3.** After calibration your mean reprojection error is 3.1 px. What does this tell you?

- A) Excellent calibration; ship it.
- B) The calibration is wrong — the model that turns pixels into rays is inaccurate, and every metric measurement built on it inherits the error. Recollect with more varied, sharper views.
- C) The camera resolution is 3.1 megapixels.
- D) Reprojection error doesn't indicate quality.

---

**Q4.** What is the visual acceptance test for correct undistortion?

- A) The image is brighter.
- B) Straight lines in the world are straight in the undistorted image (e.g. a doorframe that bowed under a wide lens comes out straight).
- C) The image is sharper.
- D) The colors are more saturated.

---

**Q5.** Why are *corners* the features you track, rather than edges or flat regions?

- A) Corners are brighter.
- B) A corner has strong gradient in two directions, so it can be matched unambiguously between frames; an edge suffers the aperture problem (motion along it is invisible) and a flat region has nothing to match.
- C) Edges are too numerous.
- D) Flat regions move faster.

---

**Q6.** Why does ORB use *binary* descriptors matched by Hamming distance?

- A) Binary descriptors are more accurate than SIFT's floats.
- B) Hamming distance (counting differing bits) is a single fast CPU instruction, so ORB matches in real time on a Jetson with no GPU — the speed that makes it the default on edge robots.
- C) Binary descriptors store color.
- D) It's required by RANSAC.

---

**Q7.** What does Lowe's ratio test do?

- A) Doubles the number of matches.
- B) Keeps a match only if the best descriptor distance is much smaller than the second-best, discarding ambiguous matches (common with repeated texture).
- C) Sorts matches by distance.
- D) Converts descriptors to binary.

---

**Q8.** A homography fit by plain least squares is wrecked by a few outlier matches. How does RANSAC fix this, and what's the analogous Week 11 idea?

- A) It averages the outliers in; analogous to a Kalman filter.
- B) It fits the model from random minimal samples, counts inliers, and keeps the best-supported model — rejecting outliers it was never told about. Analogous to the robust (Huber) noise model on a loop closure.
- C) It removes all matches and starts over; analogous to a particle filter.
- D) It increases the image resolution; analogous to a UKF.

---

**Q9.** A RANSAC homography reports a 15% inlier ratio. What should you conclude?

- A) Great matching; proceed with confidence.
- B) The matches are mostly noise and the recovered geometry is meaningless — the data didn't support a consistent model. Distrust whatever you computed from it.
- C) The camera is miscalibrated.
- D) The image is too dark.

---

**Q10.** Lucas-Kanade optical flow rests on which assumption, and what problem forces it to use a window?

- A) Color constancy; the resolution problem.
- B) Brightness constancy (a point keeps its intensity as it moves); the aperture problem (one flow-constraint equation has two unknowns per pixel, so it assumes constant flow over a window and solves by least squares).
- C) Depth constancy; the occlusion problem.
- D) Focal-length constancy; the distortion problem.

---

**Q11.** You estimate forward velocity from optical flow and compare it to wheel odometry. Why is this worth doing when you already have wheel odometry?

- A) Flow is always more accurate than wheels.
- B) It's an *independent* estimate; wheel odometry can't see slip (encoders measure wheel rotation, not body motion), but flow measures apparent world motion, so the two disagreeing is a free fault detector.
- C) Flow replaces the need for wheels.
- D) It makes the robot drive faster.

---

**Q12.** In stereo, how does disparity relate to depth, and what is the consequence?

- A) `depth = disparity × baseline`; far objects have large disparity.
- B) `depth = f · baseline / disparity`; disparity is *inversely* proportional to depth, so near objects shift a lot and far objects shift little (zero at infinity, which is also why stereo has a range limit).
- C) Depth and disparity are unrelated.
- D) `depth = disparity²`.

---

**Q13.** What's the most accurate description of how classical CV relates to learned perception in 2026?

- A) Learned perception completely replaced classical CV; ORB and RANSAC are obsolete.
- B) Classical CV is the substrate: the pinhole model underlies every learned depth/detection model, RANSAC cleans up after every learned matcher, ORB still anchors ORB-SLAM3, and learned models replace individual *tiles* (SuperPoint for ORB, Depth-Anything for stereo) while the geometric scaffolding stays classical.
- C) They are unrelated fields.
- D) Classical CV is only for textbooks.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — `K` holds `fx, fy, cx, cy`; it projects a camera-frame point to a pixel, and `K⁻¹` back-projects a pixel to a ray. (Lecture 1 §2.)
2. **B** — The pinhole projection divides by `Z`; all points on a ray project to one pixel, so depth is lost from a single view. (Lecture 1 §1.)
3. **B** — A 3 px reprojection error means the camera model is wrong; every metric measurement inherits the error. Recollect varied, sharp views. (Lecture 1 §5.)
4. **B** — Straight world lines must be straight after undistortion; that's the visual test. (Lecture 1 §3.)
5. **B** — Corners have two-directional gradient (unambiguous match); edges suffer the aperture problem; flat regions have nothing to match. (Lecture 2 §1.)
6. **B** — Binary descriptors + Hamming distance match in one CPU instruction → real-time, no GPU, the edge-robot default. (Lecture 2 §2.)
7. **B** — Lowe's ratio test keeps a match only if the best is clearly better than the second-best, discarding ambiguous matches. (Lecture 2 §2.2.)
8. **B** — RANSAC fits from random minimal samples, counts inliers, keeps the best-supported model — the geometric sibling of the Week 11 Huber kernel. (Lecture 2 §3.)
9. **B** — A 15% inlier ratio means the matches are mostly noise and the geometry is meaningless; distrust it. RANSAC's inlier ratio is a trust metric. (Lecture 2 §3.)
10. **B** — Brightness constancy; the aperture problem (one equation, two unknowns) forces the constant-flow-over-a-window least-squares solve. (Lecture 2 §4.)
11. **B** — It's independent; wheels can't see slip, flow can, so disagreement is a free fault detector. (Lecture 2 §4.1.)
12. **B** — `depth = f·b/disparity`; disparity is inversely proportional to depth, with a range limit as disparity goes sub-pixel. (Lecture 2 §5.)
13. **B** — Classical CV is the substrate; learned models replace individual tiles while the geometric scaffolding (pinhole, RANSAC, pose recovery) stays classical. (Lecture 2 §6.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./06-homework.md).
