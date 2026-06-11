# Week 14 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 15. Answer key is at the bottom — don't peek.

---

**Q1.** The stereo depth equation is `Z = fx·B / d`. If a point's disparity `d` is small, the point is:

- A) Close to the camera.
- B) Far from the camera.
- C) Behind the camera.
- D) Outside the field of view.

---

**Q2.** Why does depth error grow with the *square* of distance (`δZ ∝ Z²`)?

- A) The IR projector dims linearly with distance.
- B) Depth depends on `1/d`, so a fixed disparity error `δd` maps to a depth error that scales as `Z²/(fx·B)`.
- C) The camera's frame rate drops at range.
- D) Sunlight increases with distance.

---

**Q3.** A RealSense D435i uses **active stereo**. What does the "active" part add over passive stereo, and what still defeats it?

- A) It adds a LiDAR; nothing defeats it.
- B) It projects an IR dot pattern so blank/textureless surfaces get texture to match — but glass, mirrors, matte-black, and bright sunlight still defeat it.
- C) It adds a second IMU; repeating textures still defeat it.
- D) It increases the baseline; low light still defeats it.

---

**Q4.** Which surface defeats **all four** depth technologies (passive stereo, active stereo, structured light, ToF)?

- A) A white matte wall.
- B) A textured carpet.
- C) Clear glass.
- D) A black-and-white checkerboard.

---

**Q5.** A depth image is encoded `16UC1`. A pixel value of `1500` means:

- A) 1500 metres.
- B) 1.5 metres (the encoding is millimetres).
- C) 1500 in arbitrary units.
- D) An invalid pixel.

---

**Q6.** In a `16UC1` depth image, a pixel value of `0` means:

- A) The object is exactly 0 metres away (touching the lens).
- B) No measurement here — a hole (glass, black, occluded, or out of range). It must be masked, not treated as 0 m.
- C) The brightest possible depth.
- D) A calibration error.

---

**Q7.** You subscribe to `/camera/depth/image_rect_raw` with the default QoS (a bare integer) and receive nothing, though `ros2 topic hz` shows the camera publishing at 30 Hz. The cause is most likely:

- A) The camera is broken.
- B) A QoS reliability mismatch: depth is `BEST_EFFORT`, your default subscriber is `RELIABLE`, and a `BEST_EFFORT` publisher can't satisfy a `RELIABLE` subscriber (Week 5).
- C) The depth encoding is wrong.
- D) The optical-frame TF is missing.

---

**Q8.** You pair each depth frame with the *most recent* color frame instead of using `message_filters`. On a moving object, what happens?

- A) Nothing; latest-of-each is correct.
- B) The color is painted onto where the object was at the older color stamp, smearing color off moving objects. Use `ApproximateTimeSynchronizer`.
- C) The depth values become negative.
- D) The point cloud rotates 90°.

---

**Q9.** Your point cloud appears lying on its side — the scene goes "up" instead of "forward" in rviz2. The cause is:

- A) A unit bug.
- B) Unmasked invalid pixels.
- C) A missing or wrong optical-frame TF (the camera optical frame is z-forward/x-right/y-down per REP 103; without the transform the cloud is sideways).
- D) The temporal filter is on.

---

**Q10.** The back-projection from pixel `(u, v)` and depth `Z` to a 3D point uses the intrinsics as:

- A) `X = u·fx + Z`, `Y = v·fy + Z`.
- B) `X = (u − cx)·Z / fx`, `Y = (v − cy)·Z / fy`, `Z = Z`.
- C) `X = (u + cx)·fx / Z`, `Y = (v + cy)·fy / Z`.
- D) `X = u/Z`, `Y = v/Z`, `Z = fx·B/d`.

---

**Q11.** The depth **temporal filter** (an exponential moving average across frames) is best used when:

- A) The robot is moving fast and the scene changes every frame.
- B) The camera and the workspace are static — it averages out per-frame jitter; on a moving scene it lags and smears, which is the cost.
- C) Always; it has no downside.
- D) Never; temporal filtering is invalid for depth.

---

**Q12.** Among the depth post-processing filters, **hole-filling** is the most dangerous for a robot because:

- A) It is the slowest.
- B) It *invents* depth where there was none — converting an honest "I don't know" (a glass hole) into a confident fabricated surface, which a planner may treat as real geometry.
- C) It only works on `32FC1` images.
- D) It changes the camera intrinsics.

---

**Q13.** You color a point cloud from the *raw* (unaligned) depth and color images by reading color pixel `(u, v)` for depth pixel `(u, v)`. The result, most visible on near objects, is:

- A) Perfect color.
- B) Color offset from the geometry by the depth-to-color parallax — you must color from the *aligned* depth (or warp via the extrinsic).
- C) The cloud becomes monochrome.
- D) The depth values double.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — `Z = fx·B/d`, so small disparity means large depth (far). A point at infinity has `d = 0`. (Lecture 1 §1.)
2. **B** — Depth depends on `1/d`; differentiating gives `δZ ≈ (Z²/fx·B)·δd`. Error grows as the square of distance — geometry, not a defect. (Lecture 1 §2.)
3. **B** — Active stereo projects an IR dot pattern to texture blank surfaces, solving passive stereo's textureless failure indoors. Glass, mirrors, matte-black, and sunlight still defeat it. (Lecture 1 §4.2.)
4. **C** — Clear glass: stereo/structured-light see through it; ToF gets no clean return. No passive depth camera reliably sees glass — budget another modality. (Lecture 1 §4.5.)
5. **B** — `16UC1` is millimetres; `1500` = 1.5 m. Mixing it up with `32FC1` (metres) is the 1000× unit bug. (Lecture 2 §1.)
6. **B** — `0` is the invalid sentinel: "no measurement," not "0 m away." Treating it as 0 m makes the robot stop for holes. Mask it. (Lecture 2 §1, §3.)
7. **B** — Depth is a sensor stream (`BEST_EFFORT`); a default (`RELIABLE`) subscriber can't be satisfied by a `BEST_EFFORT` publisher, so it silently receives nothing. The Week 5 reliability mismatch, presenting as "camera broken." (Lecture 2 §1.)
8. **B** — Latest-of-each pairs a depth frame with an older color frame, painting color onto where the object was. Use `message_filters` `ApproximateTimeSynchronizer`. (Lecture 2 §2.)
9. **C** — The optical frame is z-forward/x-right/y-down (REP 103). Without the static transform to the body frame, the cloud is sideways — the canonical "my cloud is sideways" bug. (Lecture 2 §1, §6.)
10. **B** — The pinhole back-projection: `X = (u−cx)·Z/fx`, `Y = (v−cy)·Z/fy`, `Z = Z`. (Lecture 2 §3.)
11. **B** — Static camera + static workspace: the EMA averages out jitter for a big noise win. On a moving scene it lags and smears — the cost. Not free. (Lecture 2 §4.1.)
12. **B** — Hole-filling fabricates depth where there was none, turning "I don't know" into a confident fake surface a planner may trust. Prefer keeping holes for safety-relevant geometry. (Lecture 2 §4.1.)
13. **B** — Depth and color are physically different sensors with an extrinsic between them; pairing raw `(u,v)` offsets color by the parallax. Color from the *aligned* depth, most visibly important on near objects. (Lecture 2 §5.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).
