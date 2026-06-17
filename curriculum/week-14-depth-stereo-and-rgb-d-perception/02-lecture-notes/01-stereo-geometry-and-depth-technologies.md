# Lecture 1 — Stereo Geometry, the Depth Equation, and Why Every Depth Camera Lies Differently

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can derive the stereo depth equation from similar triangles, explain why depth error grows as `Z²`, and classify any depth camera as passive-stereo / active-stereo / structured-light / ToF and predict the surfaces that defeat it.

If you remember one sentence from this entire week, remember this one:

> **A depth image is not a measurement of distance. It is the output of an algorithm that *estimates* distance, and every algorithm has a noise model, a valid range, and a set of surfaces on which it confidently reports numbers that are wrong.**

Your 2D LiDAR (Weeks 3, 7) was honest: it measured time-of-flight of a laser and gave you a range with a small, well-behaved error. A depth *camera* is a different animal. Most of them recover depth from *triangulation* — the same geometry your two eyes use — and triangulation has structural blind spots that no amount of firmware fixes. This lecture builds the geometry from the ground up, derives the error law that governs where you can mount the camera, and then walks the four sensing technologies and the surfaces that break each one. By the end you will look at a depth image and see not "the scene" but "the scene, plus the camera's opinions about the parts it couldn't measure."

---

## 1. Stereo geometry from similar triangles

Start with two identical, perfectly-aligned cameras separated by a horizontal distance `B` (the **baseline**), both with focal length `f` (in pixels), looking in parallel directions. This is the *rectified* stereo configuration — real cameras are never perfectly aligned, so a calibration + rectification step warps the two images until they *are*, which is why we can assume it here.

A 3D point `P = (X, Y, Z)` in the left camera's frame projects to pixel column `x_left` in the left image and `x_right` in the right image. By the pinhole projection (Week 12):

```
x_left  = fx · X / Z + cx
x_right = fx · (X − B) / Z + cx
```

The point is the same height in both images (that's what rectification guarantees), so it only shifts *horizontally*. Subtract:

```
disparity  d = x_left − x_right = fx · B / Z
```

Solve for depth:

```
        fx · B
  Z  =  ───────
          d
```

That is the entire foundation of stereo depth. **Depth is inversely proportional to disparity.** A point far away shifts little between the two images (small `d`, large `Z`); a point close up shifts a lot (large `d`, small `Z`). A point at infinity has `d = 0`.

Three immediate consequences a senior engineer carries in their head:

1. **You need a larger baseline `B` to see farther accurately.** Double the baseline and you double the disparity at a given depth, which halves the relative depth error. This is why long-range stereo rigs (autonomous vehicles) have baselines of 10–30 cm, and why a tiny phone-sized stereo camera is hopeless past a few metres.
2. **You need texture to find the disparity at all.** Computing `d` means *matching* a patch in the left image to the same patch in the right. On a blank white wall every patch looks like every other patch — the matcher cannot find the shift, and depth is undefined. This single fact is the reason "active stereo" (§4.2) exists.
3. **Disparity is quantized.** A standard stereo matcher computes integer-pixel disparity, so the *smallest* depth difference it can resolve is set by one pixel of disparity. Sub-pixel refinement (fitting a parabola to the matching-cost curve) buys you a fraction of a pixel, but the quantization is real, and it is the root of the error law in §2.

### 1.1 Epipolar geometry — why we only search one row

Why does a point shift only horizontally? Because of **epipolar geometry**. Given a point in the left image, the corresponding point in the right image is constrained to lie on a single line — the *epipolar line*. After rectification, all epipolar lines are horizontal and aligned with image rows. So the matcher, instead of searching the entire right image for each left pixel (an O(N²) nightmare), searches *one row*. Rectification turns a 2D search into a 1D search, and that is what makes real-time stereo possible.

This is also why a stereo matcher that's fed *un*-rectified images produces garbage: the corresponding point is no longer on the same row, the 1D search misses it, and you get a depth map full of noise. If your custom stereo rig produces a noisy depth map, "did I rectify?" is the first question.

---

## 2. The `Z²` error law — the most important practical fact about depth cameras

Here is the fact that decides where you mount the camera and how far you trust it. Take the depth equation and differentiate with respect to disparity:

```
  Z = fx·B / d        ⟹        dZ/dd = −fx·B / d²
```

Substitute `d = fx·B / Z`:

```
  dZ/dd = −fx·B / (fx·B / Z)² = −Z² / (fx·B)
```

So a fixed disparity error `δd` (say, half a pixel — the resolution of a sub-pixel matcher) produces a depth error:

```
        Z²
  δZ ≈ ────── · δd
       fx·B
```

**Depth error grows with the *square* of distance.** A camera that's accurate to ±2 mm at 0.5 m is accurate to only ±8 mm at 1 m, ±32 mm at 2 m, and ±200 mm at 5 m. The error doesn't grow linearly — it explodes.

This is not a defect you can tune away. It is geometry. And it has hard engineering consequences:

- **Mount the depth camera to look at the range you care about.** A tabletop manipulation robot wants the camera close to the table (0.3–1.0 m), where error is millimetres. A camera mounted high on a mast looking 4 m ahead for navigation has decimetre-scale depth error — fine for "is there a wall" but useless for "grasp this cup."
- **Every depth camera has a *useful* range that is shorter than its *maximum* range.** A D435i lists a max range of ~10 m, but at 10 m the depth error is tens of centimetres. The useful range — where error is below your task's tolerance — might be 0.3–3 m. Homework Problem characterizes exactly this for your camera.
- **Far obstacles are detected, but their *position* is uncertain.** A path planner using depth must widen its obstacle inflation with distance, because the far obstacle could be half a metre from where the depth says it is.

> **The senior habit:** before you trust a depth number, ask "at what range, and what's the `Z²` error there?" A depth of "the cup is at 0.6 m" is trustworthy to a few millimetres. A depth of "the wall is at 6 m" is trustworthy to ~20 cm. Same camera, wildly different confidence, and the difference is `Z²`.

---

## 3. From disparity to a 3D point: the `Q` matrix

Per-pixel, the back-projection from a rectified disparity map to a 3D point is a single matrix multiply. OpenCV packages the stereo geometry into a `4×4` **reprojection matrix `Q`**:

```
  [ X ]       [ u ]
  [ Y ] = Q · [ v ]
  [ Z ]       [ d ]
  [ W ]       [ 1 ]
```

and the metric point is `(X/W, Y/W, Z/W)`. For a rectified pair, `Q` has the form:

```
       [ 1   0    0       −cx        ]
  Q =  [ 0   1    0       −cy        ]
       [ 0   0    0        fx        ]
       [ 0   0  −1/B   (cx−cx')/B    ]
```

You do not need to memorize this. You need to know that **`reprojectImageTo3D(disparity, Q)` does the entire dense reconstruction in one call**, and that the `Q` matrix is just the depth equation plus the back-projection, packed for vectorized evaluation. In Exercise 2 you'll back-project from a *depth* image (where `Z` is given directly, so you skip `Q` and use the pinhole back-projection); the `Q` matrix is the path when you start from *disparity*. The stretch goal has you confirm both give the same cloud.

---

## 4. The four depth technologies and how each one lies

Now the taxonomy. There are four ways to get a depth image in 2026, and they fail on *different* surfaces. Knowing which technology your camera uses tells you, in advance, which scenes will betray you.

### 4.1 Passive stereo

Two ordinary cameras, ambient light only. Depth from matching disparity, exactly as §1. The Stereolabs ZED is the canonical example (it then runs a neural network to fill the gaps).

- **Strength:** works outdoors in sunlight (it *uses* ambient light); no projector to wash out.
- **Fails on:** textureless surfaces (blank walls, clear sky, a white tabletop) — no texture, no match, no depth. Repeating textures (tiled floors, brick, picket fences) — the matcher finds the *wrong* match one period over and confidently reports a depth that's off by the texture's period. Low light — no light, no image, no match.

### 4.2 Active stereo

Passive stereo plus an **IR projector** that throws a random dot pattern onto the scene, giving texture to surfaces that have none. The Intel RealSense D4xx family is the dominant example. The two IR cameras see the projected dots; the matcher matches the dots; the blank wall now has texture.

- **Strength:** solves passive stereo's textureless-surface failure indoors. The reason the RealSense "just works" on a blank wall.
- **Fails on:** bright sunlight (the sun's IR washes out the projector — active stereo degrades to passive outdoors). Range (the projector dims with distance, so the assist fades past a few metres). And it still inherits stereo's other failures: **specular surfaces** (a mirror or polished metal reflects the dots elsewhere), **transparent surfaces** (glass passes the IR through and the camera sees *behind* the glass), and **IR-black surfaces** (matte black plastic, dark fabric absorb the IR — no dots return, no depth).

### 4.3 Structured light

A *known* pattern (stripes, a coded grid) is projected, and depth is recovered from how the pattern *deforms* on the surface — a single-camera-plus-projector triangulation. The original Microsoft Kinect (v1) and many industrial 3D scanners.

- **Strength:** very precise at short range; great for static, controlled scenes (3D scanning, bin-picking in a fixed cell).
- **Fails on:** the same specular/transparent/absorptive triad as active stereo (it's still light projection + triangulation), plus **multiple structured-light cameras interfere** with each other's patterns, and **motion** smears the pattern. This is why structured light lost the robotics mainstream to active stereo and ToF.

### 4.4 Time-of-flight (ToF)

Emit modulated IR light, measure the *phase shift* of the returning light to compute the round-trip time, and thus the distance — per pixel, no triangulation, no baseline. The Microsoft Azure Kinect, many phone "LiDAR" sensors, and the PMD/pmd-based cameras.

- **Strength:** no baseline means no triangulation blind spot; dense, low-noise depth on textureless surfaces (it doesn't need texture); compact.
- **Fails on:** **multi-path interference** — light bounces off two surfaces before returning (a corner, a shiny floor), and the camera averages the two path lengths into a depth that's between them, so concave corners "round off." **Bright sunlight** (ambient IR swamps the modulated signal). **Highly specular or absorptive surfaces** (no clean return). And ToF has a **phase-wrap ambiguity**: beyond the unambiguous range set by the modulation frequency, a far object can alias to a near depth.

### 4.5 The taste-test table

| Technology | Example | Best at | Defeated by |
|---|---|---|---|
| Passive stereo | Stereolabs ZED | Outdoors, sunlight, long range with big baseline | Textureless & repeating surfaces, low light |
| Active stereo | RealSense D435i / D455 | Indoors, blank walls, general robotics | Sunlight, glass, mirrors, matte-black, long range |
| Structured light | Kinect v1, industrial scanners | Precise short-range static scans | Specular/transparent, motion, multi-camera interference |
| Time-of-flight | Azure Kinect | Dense indoor depth, textureless surfaces | Multi-path (corners), sunlight, phase-wrap |

The one surface that defeats *all four* is **clear glass**: stereo and structured light see through it (depth of whatever's behind), ToF gets no clean return. There is no passive depth camera that reliably sees a glass door. This is why warehouse robots use *additional* sensors (ultrasonic, bumpers) for glass, and why "the robot drove into a glass wall" is a perennial demo-day disaster. Your perception stack must *know* it cannot see glass, not discover it on impact.

---

## 5. The three failures you will actually see, in pictures

Forget the taxonomy for a moment; here is what the failures look like on the depth image you'll stare at this week.

**Holes (zero / NaN).** Where the camera couldn't measure — glass, black surfaces, too-close, too-far, occluded — the depth is the invalid sentinel: `0` in a `16UC1` millimetre image, `NaN` in a `32FC1` metre image. **A hole is not "zero distance." It is "no measurement."** Treating a `0` as "an obstacle 0 m away" is a classic beginner bug that makes the robot stop for holes. You must mask invalid pixels before you do anything with the depth.

**Flying pixels at edges.** At a depth discontinuity — the edge of a foreground object against a far background — the matcher's window straddles both depths and produces a blended value, so you get points floating in the empty space *between* the foreground and background. In a point cloud these look like a faint "skirt" or "comet tail" trailing off every object edge. They are not real geometry. A grasp planner that picks one as a surface point grasps at air. Spatial filtering and edge-aware processing reduce them; you'll never fully remove them.

**Range smear / `Z²` noise.** Far surfaces get noisy because of §2 — the same flat wall reads crisp at 1 m and "fuzzy," like a thick noisy slab, at 5 m. This is not a hole and not a flying pixel; it's the depth error growing with distance. The temporal filter (Lecture 2) helps on static scenes by averaging frames.

Learn to see these three on sight. In the challenge you diagnose a stream with a glass-hole, a flying-pixel skirt, and a unit bug planted in it, and the whole skill is *recognizing the failure from its signature*.

---

## 6. The IMU on the camera, and why it's there

The D435i and OAK-D ship an IMU *inside the camera*. Why put an IMU on a camera? Three reasons that matter for the rest of C24:

1. **Visual-inertial odometry (VIO).** Fusing the camera's motion (from the images) with the IMU (Week 9) gives a drift-bounded pose estimate — the basis of ORB-SLAM3 and the VIO most AR headsets run. You don't build VIO this week, but the IMU stream is why this camera *can* do it.
2. **Gravity alignment.** The IMU tells you which way is down, so you can level a point cloud or detect the ground plane without a separate calibration. Next week's RANSAC ground segmentation gets easier when you know the approximate gravity direction.
3. **Motion deblur / rolling-shutter correction.** Knowing the camera's angular velocity during the exposure lets you correct rolling-shutter skew.

The catch: the camera IMU and the camera optical centre are at *different physical locations* with an extrinsic between them, and the IMU is in *its own* frame. When you publish `/camera/imu`, it carries `frame_id = camera_imu_optical_frame`, and fusing it correctly means respecting that extrinsic — exactly the frame discipline from Week 2. Exercise 1 has you publish the IMU with correct QoS and frame; using it for VIO is a Phase-later concern.

---

## 7. Picking a camera for *your* robot (the 2026 decision)

You will be asked, in an interview and on the job, "which depth camera would you spec for this robot?" The senior answer is never "the best one" — it's "the one whose failure surfaces don't overlap my operating environment, at the range I care about, within budget." A decision procedure:

1. **What range matters?** Tabletop manipulation: 0.2–1.0 m → short-baseline active stereo (D435i) or ToF (Azure Kinect) both excellent. Mobile navigation: 1–5 m → larger-baseline stereo (D455, ZED) for the range, accepting decimetre error far out.
2. **Indoors or outdoors?** Outdoors in sun → passive stereo (ZED) or LiDAR; active stereo and ToF degrade badly in sunlight. Indoors → active stereo or ToF.
3. **What surfaces?** Lots of glass/mirrors/shiny metal → no passive depth camera is reliable; budget for an additional modality. Textureless white walls indoors → active stereo (the projector) or ToF (no texture needed), *not* passive stereo.
4. **Do you need on-camera compute?** OAK-D runs the detector on the camera, so the detection arrives pre-associated with depth and your host CPU/GPU is freed — a real advantage for the Week 16 latency budget.
5. **Budget and ecosystem.** RealSense has the most mature ROS2 driver and the largest community; that alone is often decisive for a student or a small team.

For the C24 capstone's tabletop-pick-and-place-in-a-shared-indoor-space task, the **RealSense D435i** is the default: short useful range where the manipulation happens, active stereo for indoor textureless surfaces, a built-in IMU, and the best-supported ROS2 driver. That is why the labs target it (with a sim fallback). When you defend your perception stack at the Week 16 midterm, "why this camera" is a question you should be able to answer in these terms.

---

## 4.6 — Active stereo, in slightly more depth, because you'll use it

The capstone camera is active stereo, so it's worth understanding the mechanism past "it projects dots." A RealSense D4xx has *two* infrared cameras and *one* IR projector between them. The projector throws a fixed, pseudo-random dot pattern onto the scene. The two IR cameras both see the dots. Because the pattern is random (no repeating period), each small patch of dots is *locally unique*, so the stereo matcher can unambiguously find the same patch in both images and compute its disparity — even on a surface that has no natural texture of its own (a blank white wall).

Three consequences that matter in practice:

- **The color camera is separate and *passive*.** The depth comes from the two IR cameras + projector; the RGB comes from a third, ordinary color camera. That's why depth and color need alignment (the extrinsic between the IR rig and the color camera) — they are literally different cameras looking from slightly different places. The IR projector does *not* help the color image; it's invisible to it (and on some cameras you can faintly see the dots in the IR stream but never in RGB).
- **The projector is the thing sunlight defeats.** Outdoors, the sun's broadband IR floods the scene and washes out the projector's modest dot pattern, so the matcher loses the artificial texture and degrades to *passive* stereo — which then fails on the textureless surfaces the projector was there to rescue. This is why active-stereo cameras work beautifully in an office and poorly on a sunny patio.
- **You can turn the projector off.** If your scene already has rich natural texture (a cluttered, patterned environment) and you're outdoors, disabling the emitter and running passive can sometimes be better. The driver exposes this; it's a knob worth knowing exists.

The reason this level of detail earns its place: at the Week 16 midterm, "why does your depth get worse near the window?" has a real answer for an active-stereo camera ("sunlight through the window washes out the IR projector, degrading active stereo to passive, which then drops the textureless wall"), and that answer is the difference between someone who *configured* the camera and someone who *understands* it.

## 4.7 — Time-of-flight, the mechanism, and its signature failure

Active stereo earned a closer look (§4.6); ToF earns one too, because it's the other technology you're likely to use (the Azure Kinect) and its failures are *completely different* from stereo's, so you must recognize them.

A ToF camera emits *amplitude-modulated* infrared light — the IR brightness oscillates at a high frequency (tens of MHz). The light bounces off the scene and returns, and the camera measures the *phase shift* between the emitted and received modulation at each pixel. Phase shift is proportional to round-trip time, which is proportional to distance. So each pixel directly measures distance, with no triangulation, no baseline, no stereo matching — which is why ToF gives dense depth even on textureless surfaces (it doesn't need texture) and has no triangulation blind spot.

But phase measurement has its own signature failures:

- **Multi-path interference.** Light can reach a pixel by more than one path — directly off a surface, *and* bounced off a nearby second surface (a shiny floor, a concave corner). The camera measures the *combined* phase of both returns, which corresponds to a distance *between* the two true distances. The effect: concave corners "round off," and surfaces near reflective floors read closer than they are. This is ToF's equivalent of stereo's flying pixels — a structural artifact you learn to recognize. Stereo doesn't do this; ToF does. If a depth camera rounds off the corners of a room, it's a ToF camera showing multi-path.
- **Phase wrap.** Phase is periodic — it wraps at 2π. Beyond the *unambiguous range* set by the modulation frequency, a far object's phase aliases to that of a near object, so a wall at 6 m might read as a surface at 1 m. Cameras mitigate this with multiple modulation frequencies, but it's a real failure at range. Stereo doesn't wrap; ToF can.
- **Motion blur from the integration.** ToF measures phase by integrating over several sub-exposures; a fast-moving object smears across them, producing edge artifacts. Different from stereo's flying pixels, same family of "edges are hard."

The practical upshot: **stereo and ToF fail differently, so the right camera depends on which failures your scene triggers.** A scene of shiny concave corners punishes ToF (multi-path) but not stereo; a scene of textureless walls in dim light punishes passive stereo but not ToF. Knowing the *mechanism* lets you predict the failure before you buy the camera — which is exactly the §7 selection discipline, grounded in physics rather than spec-sheet numbers.

## 7.5 — A worked numerical example: sizing a camera for the capstone

Abstract error laws don't build intuition; numbers do. Let's size a depth camera for the capstone's tabletop pick-and-place, end to end, the way you'd do it in a design review.

**The task.** Grasp a cup on a bench. The grasp planner (Week 25) needs the cup's surface localized to about **±5 mm** to close a parallel-jaw gripper around it reliably. The cup sits 0.4–0.8 m from the camera when the robot is in grasping position.

**The candidate.** A RealSense D435i: baseline `B ≈ 50 mm`, depth focal length `fx ≈ 640 px` at 640×480, sub-pixel disparity resolution `δd ≈ 0.1 px` (the SDK's sub-pixel mode). Plug into the error law from §2:

```
        Z²
  δZ ≈ ────── · δd
       fx·B

  At Z = 0.5 m:  δZ ≈ (0.25) / (640 · 0.05) · 0.1 = 0.25/32 · 0.1 ≈ 0.78 mm
  At Z = 0.8 m:  δZ ≈ (0.64) / 32 · 0.1                         ≈ 2.0 mm
  At Z = 1.5 m:  δZ ≈ (2.25) / 32 · 0.1                         ≈ 7.0 mm
```

**The verdict.** At the grasp range (0.4–0.8 m) the depth error is sub-2 mm — comfortably inside the ±5 mm budget. By 1.5 m it's already 7 mm — *over* budget for grasping, though fine for "is there an obstacle." So this camera's **useful range for grasping** is roughly 0.4–1.0 m, exactly where you'd position the robot for the task. The camera is well-matched. If the task instead needed ±5 mm at 3 m, this camera would fail and you'd need a larger baseline (the D455's 95 mm) or accept that grasping at 3 m isn't this camera's job.

This is the whole discipline in one calculation: take the task tolerance, take the camera's `fx·B` and sub-pixel resolution, apply the `Z²` law, and find where the error crosses the tolerance. That crossing is the camera's useful range *for that task*. The homework characterization makes you do this empirically for your own camera; this is the analytic version you do on a whiteboard before you buy anything.

## 7.6 — Why the depth image is darker and noisier than you expect

A practical note that saves a panicked first hour with a real camera. When you first `image_view` a raw depth stream, two things surprise people:

**The depth image looks almost black.** A `16UC1` depth image holds millimetres — values like 500–4000. An 8-bit display maps 0–255, so 1500 mm rendered naively is off the top of the scale or crushed to a faint grey. **The depth image is not broken; it's just that raw millimetres don't map to a nice grayscale.** Tools like `rqt_image_view` and Foxglove apply a colormap (near = blue, far = red, or a turbo map) precisely so you can see it. If you stare at a near-black depth image and conclude the camera is dead, check whether you're viewing raw `16UC1` without a colormap — the data is there.

**The edges shimmer and the far field crawls.** This is the `Z²` noise (§2) plus the flying pixels (§5), live. The same wall, frame to frame, has its far pixels jittering by centimetres while the near pixels are rock-steady. Object edges have a faint crawling skirt. This is *normal* for a stereo depth camera and it's exactly why the temporal filter (Lecture 2) exists for static scenes. A learner who expects LiDAR-clean depth from a stereo camera will think something is wrong; nothing is — this is what triangulated depth looks like, and your job is to *gate and filter* it, not to expect it to be perfect.

## 7.7 — The depth-to-color extrinsic, conceptually

One more concept you'll need in Lecture 2 and the labs: the depth and color sensors are *physically separated* on the camera body, by a small baseline of their own (a few centimetres on a D435i). They are two cameras. Each has its own intrinsics and its own optical frame, and there is a fixed **extrinsic transform** between them — a small translation (the inter-sensor baseline) plus a tiny rotation (manufacturing alignment).

This matters for two reasons that come up constantly. First, a 3D point seen by the *depth* sensor projects to a *different* pixel in the *color* image than it does in the depth image — which is why you can't naïvely overlay raw depth and raw color (Lecture 2 §5). Second, the IMU is at yet *another* physical location with its own extrinsic to both. The camera vendor calibrates these extrinsics at the factory and the driver publishes them as static transforms, so you mostly consume them rather than measure them — but you must *know they exist*, because every "the color is offset from the depth" and "the IMU points the wrong way" bug traces back to an extrinsic you ignored. The frame discipline from Week 2 is not academic here; a depth camera is a little tree of three sensors, each in its own frame, and getting the cloud right means respecting that tree.

## 7.8 — Rectification and calibration: where the depth quality is born

A depth camera's accuracy is set long before your code runs — at *calibration* and *rectification*. You met intrinsics calibration in Week 12; here is why it's load-bearing for depth specifically.

Recall (§1) that the disparity equation assumes a *rectified* stereo pair: two cameras with parallel optical axes, coplanar image planes, and matched focal lengths, so corresponding points lie on the same image row. Real cameras are never built that perfectly — the two sensors are slightly rotated and offset relative to each other. **Rectification** is the warp that corrects for this: using the calibrated intrinsics and the stereo extrinsic, each raw image is re-projected onto a common, idealized image plane, so that after rectification the epipolar lines *are* horizontal rows and the 1D disparity search is valid.

Two practical implications:

- **Bad calibration = bad depth, silently.** If the factory (or your own) calibration is off — a slightly wrong focal length, a mis-estimated baseline — the rectification is wrong, the disparities are wrong, and the depth is *systematically* off (a bias, not just noise). The cloud looks plausible but the cup is reported 3 cm too far, every time. This is why a depth camera that "used to be accurate" and now isn't may need re-calibration (a drop can shift the sensors). The homework characterization's *bias* check (measured distance vs. true distance) is exactly the test for a calibration error.
- **The `CameraInfo` carries the rectification.** The `/camera/depth/camera_info` you read in Exercise 1 isn't just the intrinsics `K` — it also carries the rectification matrix `R` and the projection matrix `P` that encode the rectified geometry. For the standard depth topics, the camera ships *already rectified*, so your back-projection uses the rectified intrinsics directly (which is why Lecture 2's projection is so simple). But knowing the rectification happened — and can be wrong — is what lets you diagnose a biased cloud as a calibration problem rather than a code bug.

The takeaway for a robotics engineer: a depth camera is a *calibrated instrument*, and its accuracy is only as good as its calibration. You mostly consume the factory calibration, but you must know it exists, know it can drift, and know that a *biased* (not just noisy) cloud points at calibration, while a *noisy* cloud points at the `Z²` law and filtering. Bias and noise are different failures with different causes, and telling them apart is the start of every depth-camera debugging session.

## 7.85 — Depth, LiDAR, and why a robot wants both

A natural question this week: if depth cameras lie so much, why not just use LiDAR (Weeks 3, 7), which is honest? The answer — and it's a near-certain interview question — is that depth cameras and LiDAR are *complementary*, and a serious robot carries both.

**LiDAR's strengths:** long range with honest, low-noise depth (a laser time-of-flight measurement, not a triangulation estimate); a wide field of view (often 360°); it works in the dark and outdoors. **LiDAR's weaknesses:** it's sparse (a 2D LiDAR is a single ring; even a 3D LiDAR has gaps between beams), it gives *no color or texture* (so it can't tell a red cup from a blue one), and 3D LiDAR is expensive.

**Depth cameras' strengths:** dense depth (every pixel), color (the RGB), short-range accuracy in the millimetres (within the useful range), cheap. **Their weaknesses:** the `Z²` error, the surface failures (glass, specular, dark), the limited field of view, and the indoor/lighting constraints.

So they fill each other's gaps: the LiDAR gives honest long-range geometry for navigation (where's the wall, the corridor), the depth camera gives dense, colored, short-range geometry for manipulation (where's the cup, what color is it). The capstone uses both — LiDAR for the base's navigation and obstacle avoidance, the RGB-D camera for the arm's grasping — and the Week 16 fused node combines them: LiDAR clusters for the 3D where, the camera for the color and the 2D class. "Why both?" — because no single sensor is honest, dense, colored, long-range, and cheap all at once, and a robot that must navigate *and* manipulate needs the union of their strengths. Knowing this is knowing why your perception stack has the sensors it has.

## 7.86 — Learned depth: Depth-Anything and the neural option

A 2026 development you should know: **learned monocular depth** has gotten good enough to matter. Models like Depth-Anything v2 (which you met at a glance in Week 13) estimate depth from a *single* RGB image — no stereo, no projector, no ToF — by learning the statistical relationship between appearance and depth from enormous training sets.

The trade-off vs. the geometric cameras of this lecture: learned monocular depth gives *relative* depth (the ordering and rough structure of the scene) far more robustly than stereo on textureless or glass surfaces, because it reasons about *appearance* ("that looks like a wall receding") rather than triangulation. But it gives *metric* depth poorly — without a stereo baseline or a ToF measurement, the absolute scale is ambiguous (a small near object and a large far one can look identical), so the metres are unreliable unless the model is fine-tuned or fused with a metric sensor.

The practical pattern in 2026: use the geometric depth camera (stereo/ToF) for *metric* accuracy within its useful range, and use learned monocular depth to *fill the gaps* — the glass, the textureless wall, the far field — where the geometric camera fails, accepting that the filled-in depth is structurally-right-but-scale-uncertain. The two are complementary, the same way LiDAR and depth cameras are. Knowing learned depth exists — and knowing its strength (robust relative structure) and weakness (uncertain metric scale) — is the answer to "what about the glass the stereo camera can't see?": a learned model can hallucinate plausible structure there, which is useful for *navigation* (don't drive into the rough shape) but dangerous for *grasping* (you can't grasp a hallucinated surface). The honest stance is the same as everything in this lecture: know what each sensor is good for, and gate accordingly.

## 7.87 — The interview answer: "tell me about depth cameras"

Because this is exactly the kind of thing a robotics interviewer probes, here is the compressed, senior answer to "how does a depth camera work, and what are its limits?" — assembled from this lecture:

"Most depth cameras recover depth by triangulation — stereo matching between two views, where depth is inversely proportional to disparity. That gives you two structural facts: depth error grows with the square of distance, so the camera has a *useful* range much shorter than its max range; and you need texture to match, which is why active-stereo cameras project an IR pattern to texture blank surfaces. The failures are surface-dependent: glass and mirrors and matte-black defeat stereo because there's nothing to match or the light doesn't return; ToF cameras avoid the triangulation blind spot but suffer multi-path on corners and shiny floors. The one thing no passive depth camera reliably sees is clear glass, which is why robots in glassy environments carry a second modality. The practical upshot is that a depth image is an *estimate with a noise model and blind spots*, not a measurement — you read its confidence, gate by range, and never trust the parts the camera fabricated."

That answer — geometry (`Z²`), the texture requirement, the surface failures, glass as the universal defeat, and the estimate-not-measurement stance — covers the whole lecture in a paragraph, and it's the difference between an interviewer hearing "I set up a RealSense once" and "I understand depth sensing." Everything in this lecture rolls up to that paragraph; if you can deliver it cold, you've internalized the week.

## 7.9 — The one-paragraph mental model to carry forward

If you compress this entire lecture into one mental model, it's this: **a depth camera is a triangulation (or time-of-flight) instrument whose accuracy is set by geometry (`Z²`), whose blind spots are set by physics (the surface-technology interactions), and whose output you must always read as "estimate plus opinion," never as "ground truth."** The geometry tells you *where* to mount it and *how far* to trust it. The physics tells you *which scenes* will betray it. And the "estimate plus opinion" stance is what keeps you from driving into the glass door — because the camera's confident 2.5 m reading behind the glass is an opinion, not a measurement, and the engineer who knows the difference gates it out while the one who doesn't plans a path through it.

Everything downstream — next week's clustering, the Week 16 fused node, the capstone's grasp — inherits this stance. A point cloud is only as trustworthy as the depth it came from, and the depth is only trustworthy where the geometry is close and the surface cooperates. Carry that, and depth perception stops being a black box that "sometimes works" and becomes an instrument whose behavior you can predict, gate, and defend.

And that predict-gate-defend stance is the throughline of the entire perception phase: you don't trust a sensor, you *characterize* it — its accuracy law, its failure surfaces, its useful range — and then you build the gates that keep its lies out of your decisions. The IMU got an Allan-variance characterization in Week 9; the depth camera gets a `Z²`-and-failure-surface characterization here; next week the registration gets a fitness-and-drift characterization. Same discipline, different instrument, every time: know the instrument's limits, measure them, and gate accordingly. That is what a perception engineer does, and this lecture is where the depth camera joins the set of instruments you've learned to distrust productively.

## 8. Recap

You should now be able to:

- Derive `Z = fx·B / d` from similar triangles and explain disparity, baseline, and why texture is required for matching.
- State and *use* the `Z²` error law: depth error grows as the square of distance, which fixes the camera's useful range and where you mount it.
- Explain epipolar geometry and why rectification turns a 2D match into a 1D search.
- Classify any depth camera as passive-stereo / active-stereo / structured-light / ToF, and predict its failure surfaces — with glass as the one that beats them all.
- Recognize the three depth-image failures on sight: holes (invalid sentinel, *not* zero distance), flying pixels at edges, and `Z²` range smear.
- Explain why the camera carries an IMU and what its extrinsic/frame implications are.
- Spec a depth camera for a given robot by matching its failure surfaces to the operating environment and range.

Next up: how this geometry becomes a ROS2 topic family, how to synchronize and project it into a metric cloud, and how to read and filter the lie. Continue to [Lecture 2 — RGB-D Bring-up, Projection, and Filtering](./02-rgbd-bringup-projection-and-filtering.md).

---

## References

- Szeliski, *Computer Vision: Algorithms and Applications* (2nd ed., free PDF), Ch. 11–12: <https://szeliski.org/Book/>
- OpenCV — Depth Map from Stereo Images: <https://docs.opencv.org/4.x/dd/d53/tutorial_py_depthmap.html>
- Intel — Tuning depth cameras for best performance: <https://dev.intelrealsense.com/docs/tuning-depth-cameras-for-best-performance>
- Intel RealSense D435i datasheet (range, accuracy, FOV): <https://www.intelrealsense.com/depth-camera-d435i/>
- Microsoft Azure Kinect DK (ToF) docs: <https://learn.microsoft.com/en-us/azure/kinect-dk/>
- REP 103 — units and conventions (optical frames): <https://www.ros.org/reps/rep-0103.html>
