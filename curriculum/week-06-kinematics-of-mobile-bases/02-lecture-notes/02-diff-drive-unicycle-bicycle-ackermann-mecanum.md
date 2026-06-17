# Lecture 2 — Five Motion Models: Diff-Drive, Unicycle, Bicycle, Ackermann, Mecanum

> **Reading time:** ~80 minutes. **Hands-on time:** ~55 minutes (you derive the diff-drive and mecanum Jacobians, then check them numerically).

Lecture 1 told you that odometry drifts and showed you *where* the error goes. This lecture tells you where the velocities `vₓ` and `ω` you integrated actually *come from*. They come from a **motion model** — a fixed relationship between the things you can command or measure (wheel speeds, steering angles) and the body twist of the chassis. There are five models you will meet on real platforms, and the central message of this lecture is that **the model is a choice with permanent consequences**: it fixes your parameter set, your constraint structure, and — as Lecture 1 promised — your dominant drift source. By the end you can derive diff-drive forward and inverse kinematics from the no-slip constraint, place every model on the holonomic/nonholonomic axis, write the mecanum Jacobian and explain why it cannot be inverted the way diff-drive's can, and name each model's worst error so that when you meet a real robot you can predict how it lies before you drive it.

## 2.1 — The one constraint that starts everything: rolling without slipping

Every wheeled-robot kinematic model is built on one physical idealization: **a wheel rolls without slipping.** A wheel of radius `r` spinning at angular velocity `φ̇` (phi-dot, rad/s) lays down ground contact at linear velocity

```
v_wheel = r · φ̇
```

That is the *whole* of wheel kinematics in one line. The encoder measures `φ̇` (or its integral, the wheel angle `φ`); you multiply by `r` to get the ground speed of that wheel's contact point. Everything else in this lecture is bookkeeping about how several wheels, rigidly attached to one chassis, combine their individual `r·φ̇` into a single body twist.

Two constraints govern that bookkeeping:

- **No-slip (rolling) constraint.** The wheel's contact point moves at exactly `r·φ̇` *along the wheel's rolling direction*. Encoders see this.
- **No-skid (lateral) constraint.** A *conventional* wheel cannot move *sideways* — its contact point has zero velocity perpendicular to the rolling direction. This is the constraint that makes a car nonholonomic: you cannot slide a car directly sideways into a parking space, you have to parallel-park.

A **passive caster** obeys neither constraint usefully: it is free to swivel, so it imposes *no* lateral constraint and contributes *no* odometry information. This is why we never read a caster's encoder — it has none, and if it did, it would tell us nothing about body motion. A **driven, fixed wheel** imposes the no-skid constraint and contributes one equation linking its `φ̇` to the body twist. The number and arrangement of constrained wheels is exactly what distinguishes the five models.

## 2.2 — The unicycle: the model every other model reduces to

Start with the simplest useful abstraction: a single wheel that can roll forward at speed `vₓ` and rotate in place at yaw rate `ω`. That is the **unicycle model**, and its state is the planar pose `(x, y, θ)` evolving as

```
ẋ = vₓ · cos(θ)
ẏ = vₓ · sin(θ)
θ̇ = ω
```

This is *exactly* the integration you ran in Lecture 1. The unicycle has two control inputs — `vₓ` and `ω` — and three pose states. Because it has fewer controls than states, and because the no-skid constraint forbids lateral motion (`ẏ` in the *body* frame is always zero — there is no `v_y` term), the unicycle is **nonholonomic**: it cannot reach every pose by a direct motion in that direction; it has to maneuver.

The reason the unicycle matters so much is that **diff-drive, bicycle, and Ackermann all reduce to it at the body level.** Each of those models is a different *mechanism* for producing a `(vₓ, ω)` pair, but once you have the pair, the pose integration is identical — it is the unicycle equations above. This is why **Nav2 plans and commands in unicycle space**: a `geometry_msgs/Twist` with `linear.x = vₓ` and `angular.z = ω` is a unicycle command. The base-specific controller (`diff_drive_controller`, an Ackermann controller, etc.) is responsible for the *last* translation from `(vₓ, ω)` to whatever the hardware actually takes (wheel speeds, steering angle). Learn the unicycle and you have learned the interface every mobile base in ROS2 presents upward.

## 2.3 — Differential drive: forward kinematics from the constraint

A differential-drive robot has two independently driven, fixed, coaxial wheels (left and right) and one or two passive casters for balance. Let:

- `r` = wheel radius (both wheels assumed equal — Lecture 1 showed that the *inequality* is the `Ed` error you calibrate).
- `L` = wheel separation (track width), the distance between the two contact points.
- `φ̇_L`, `φ̇_R` = left and right wheel angular velocities, from the encoders.

The left wheel's contact point moves forward at `v_L = r·φ̇_L`; the right at `v_R = r·φ̇_R`. Both points are rigidly attached to the chassis on a common axle, separated by `L`. The chassis is a rigid body, so its motion is fully described by the velocity of its center point (midway between the wheels) and its yaw rate. Two facts pin it down:

1. The **body forward velocity** is the average of the two wheel velocities — the center point moves at the mean of its two endpoints:

   ```
   vₓ = (v_R + v_L) / 2 = r · (φ̇_R + φ̇_L) / 2
   ```

2. The **body yaw rate** comes from the *difference*: if the right wheel runs faster than the left, the body rotates counter-clockwise. The relative velocity `v_R − v_L` across the separation `L` is the yaw rate:

   ```
   ω = (v_R − v_L) / L = r · (φ̇_R − φ̇_L) / L
   ```

That is **differential-drive forward kinematics**. Two encoder readings in, one body twist out. You will implement exactly these two lines in Exercise 1, and they are the heart of the mini-project's odometry node. Notice the structure: forward velocity is a *sum*, yaw rate is a *difference*, and `L` divides the yaw term — which is precisely why a *wheelbase* error scales your heading (Lecture 1, §1.3), because `L` sits in the denominator of `ω` and nowhere else.

### The instantaneous center of rotation (ICR)

A rigid body in planar motion is, at any instant, rotating about a single point — its **instantaneous center of rotation**. For a diff-drive robot the ICR always lies **on the line through the two wheel axles**, at a signed distance from the body center:

```
R_ICR = vₓ / ω = (L/2) · (v_R + v_L) / (v_R − v_L)
```

When `v_R = v_L`, `ω = 0`, the ICR is at infinity, and the robot drives straight. When `v_R = −v_L`, `vₓ = 0`, the ICR is at the body center, and the robot spins in place (this is why diff-drive bases are beloved indoors — zero turning radius). The ICR living on the axle line is the geometric signature of the no-skid constraint: the robot can only rotate about a point its fixed wheels can roll around.

## 2.4 — Differential drive: inverse kinematics and the Jacobian

Control runs the other direction. You have a desired `(vₓ, ω)` (from Nav2, from your square-driving script) and you need the wheel speeds that produce it. Invert the two equations from §2.3:

```
v_R = vₓ + (ω · L) / 2          →   φ̇_R = (vₓ + ω·L/2) / r
v_L = vₓ − (ω · L) / 2          →   φ̇_L = (vₓ − ω·L/2) / r
```

In matrix form, with the body twist `u = [vₓ, ω]ᵀ` and the wheel velocities `q̇ = [φ̇_L, φ̇_R]ᵀ`, forward kinematics is `u = J · q̇` where

```
        [ r/2      r/2   ]
J  =    [ -r/L     r/L   ]
```

`J` is **2×2 and square**, and its determinant is `r²/L ≠ 0`, so it is **invertible**. This is the deep reason diff-drive inverse kinematics is clean algebra: the number of controlled wheels (2) equals the dimension of the controllable body twist (2). You can demand *any* `(vₓ, ω)` and solve for exactly one `(φ̇_L, φ̇_R)`. Contrast this with the mecanum case (§2.7) where the matrix is non-square and the inverse is a least-squares pseudoinverse — a structural difference you will feel as worse odometry.

### Wheel-speed saturation

Inverse kinematics is mathematically exact but physically bounded: motors have a maximum `φ̇`. If a commanded `(vₓ, ω)` asks for `φ̇_R` above the limit, you must *scale*. The production `diff_drive_controller` scales *both* wheel commands by the same factor so the *ratio* `v_R/v_L` — and therefore the *path curvature* — is preserved, sacrificing speed but not direction. Naively clamping each wheel independently would change the curvature and send the robot off its intended arc. This is a one-line subtlety that separates a toy controller from a shippable one, and it is worth remembering when you compare your hand-rolled node to `diff_drive_controller` in resources.

## 2.5 — The bicycle model: front-steer, rear-drive

A car does not have two coaxial driven wheels; it has steerable front wheels and (often) driven rear wheels, separated by a *wheelbase* `ℓ` measured front-to-back (not the diff-drive track width `L`, which is side-to-side — the symbol collision is real and a common source of confusion, so we use `ℓ` for the front-rear distance). The **kinematic bicycle model** collapses the two front wheels into one virtual front wheel and the two rear wheels into one virtual rear wheel, both on the centerline. The state adds nothing — still `(x, y, θ)` — but the controls change: forward speed `vₓ` (at the rear axle) and **steering angle `δ`** (delta).

The geometry: the rear wheel rolls along the body `x` axis (it cannot steer), so its no-skid constraint is the unicycle constraint. The front wheel is tilted by `δ`; its no-skid constraint forces the whole vehicle to turn about an ICR that lies on the rear-axle line, at radius

```
R = ℓ / tan(δ)
```

and the resulting yaw rate is

```
ω = vₓ / R = (vₓ / ℓ) · tan(δ)
```

So the bicycle's body twist is `(vₓ, (vₓ/ℓ)·tan δ)` — and once you have that pair, the pose integration is the **same unicycle integration** from §2.2. The critical difference from diff-drive: **yaw rate is coupled to forward speed.** A bicycle *cannot* spin in place (`vₓ = 0 ⇒ ω = 0`, no matter the steering angle) and cannot achieve a zero turning radius (`δ` is mechanically limited, so `R` has a minimum). Its dominant odometry error is **steering-angle bias** — a few tenths of a degree of misalignment in `δ` becomes, through the `tan δ` relationship, a systematic heading drift that behaves exactly like the wheelbase error of Lecture 1: it lives in the heading channel and therefore dominates.

The **kinematic** bicycle assumes the tires roll without lateral slip — valid at low speed and low lateral acceleration, which covers indoor and slow outdoor robots. The **dynamic** bicycle model adds tire slip angles and lateral forces and becomes necessary above roughly 0.5 g of lateral acceleration (fast cars, aggressive AMRs). The dynamic model is Phase 3 control material; this week is purely kinematic, and we state the boundary so you know when the kinematic model stops being honest.

## 2.6 — Ackermann steering: why a real car's front wheels disagree

The bicycle model's single virtual front wheel is a fiction. A real car has *two* front wheels separated by a track width, and here is the subtlety that gives the model its name: **for the car to turn without skidding, the two front wheels must steer at *different* angles.** Both front wheels must be tangent to circles centered on the *same* ICR (which sits on the extended rear axle). The inner wheel traces a tighter circle than the outer wheel, so the inner wheel must steer *more*. This is **Ackermann steering geometry**, and a real steering linkage (the Ackermann linkage) is mechanically designed to produce it.

If `δ_i` and `δ_o` are the inner and outer steering angles, the Ackermann condition is

```
cot(δ_o) − cot(δ_i) = w / ℓ
```

where `w` is the front track width and `ℓ` the wheelbase. The two angles differ; only at `δ = 0` (straight) are they equal. The "bicycle" steering angle `δ` is the angle of the *virtual* centerline wheel, satisfying `tan δ = ℓ / R` for the ICR radius `R` — it is the average geometry, not either physical wheel.

This is why ROS2's `ackermann_msgs/AckermannDrive` carries **one** `steering_angle` field, not two: it transmits the *virtual* bicycle steering angle, and the vehicle's own steering linkage (or its controller) splits it into the two physical wheel angles via the Ackermann condition. For *odometry*, an Ackermann car reads its rear-wheel encoders for `vₓ` and its steering sensor for `δ`, then uses the bicycle equations of §2.5 — Ackermann geometry matters for the *steering mechanism*, but the *odometry model* is the bicycle. Its dominant drift source is therefore the same as the bicycle's: steering-angle (heading) bias.

## 2.7 — Omnidirectional / mecanum: holonomy at the cost of slip

The four models so far are all **nonholonomic** — they cannot move sideways. **Mecanum** (and its cousin, the omni-wheel base) breaks that constraint. A mecanum wheel has a ring of passive rollers mounted at **45°** to the wheel axis. When the wheel spins, it pushes the ground both forward (from the wheel rotation) and sideways (from the angled rollers free-rolling). With four mecanum wheels arranged in the canonical pattern (rollers forming an "X" or "O" when viewed from above), independent control of the four wheel speeds gives you full planar control: forward, sideways (`v_y` — a real lateral velocity, impossible for diff-drive), and yaw, *simultaneously*. That is **holonomic** motion: three controllable DOF for three pose DOF.

The forward kinematics relate four wheel speeds `[φ̇_1, φ̇_2, φ̇_3, φ̇_4]ᵀ` to the body twist `[vₓ, v_y, ω]ᵀ`. With half-track `a` (lateral half-distance) and half-wheelbase `b` (longitudinal half-distance), and the standard wheel numbering (1 = front-left, 2 = front-right, 3 = rear-left, 4 = rear-right):

```
[ vₓ ]         [  1    1    1    1   ] [ φ̇_1 ]
[ v_y ] = (r/4)[ -1    1    1   -1   ] [ φ̇_2 ]
[ ω  ]         [ -1/(a+b)  1/(a+b)  -1/(a+b)  1/(a+b) ] [ φ̇_3 ]
                                                        [ φ̇_4 ]
```

Read off the structure: `vₓ` is the sum of all four wheels (forward), `v_y` is the *signed* combination that the 45° rollers produce (sideways), and `ω` is the moment combination scaled by `1/(a+b)`. The matrix is **3×4 — non-square.** Forward kinematics (wheels → twist) is fine: four inputs collapse to three outputs. But **inverse kinematics (twist → wheels) requires solving an over-determined system**, and odometry — the *forward* direction we care about this week — is where the trouble lives.

### Why mecanum odometry is *worse* than diff-drive

Here is the punchline Lecture 1 promised. On a diff-drive base, the no-skid constraint means that, *ideally*, the wheels do not slip sideways at all; slip is an occasional, stochastic intruder (Lecture 1, Class 2). On a mecanum base, the rollers are **designed to slip sideways** — that is how you get `v_y`. The forward-kinematic equations above assume each roller free-rolls perfectly, transmitting exactly the geometric component of motion. In reality the rollers have friction, finite contact patches, and load-dependent slip, so **every wheel contributes slip error on every cycle, by construction.** There is no "no-skid" channel to anchor the estimate. The result: mecanum dead-reckoning drifts noticeably faster than diff-drive, *despite* having twice as many encoders. More sensors do not help when the extra sensors measure a quantity (roller slip) you cannot model precisely. This is the cleanest illustration in the whole week of the rule that **odometry quality is set by the constraint structure, not the sensor count.**

## 2.8 — The five models, compared

| Model | DOF (controllable) | Holonomic? | Parameters to calibrate | Can spin in place? | Dominant odometry error |
|---|---|---|---|---|---|
| **Unicycle** | 2 (`vₓ`, `ω`) | No | — (abstraction) | Yes | n/a (it is the integration target) |
| **Differential drive** | 2 (`vₓ`, `ω`) | No | `r`, `L` | Yes | Wheelbase `L` → heading |
| **Bicycle** | 2 (`vₓ`, `δ`) | No | `ℓ`, `δ` offset | No | Steering bias → heading |
| **Ackermann** | 2 (`vₓ`, `δ`) | No | `ℓ`, `w`, `δ` offset | No | Steering bias → heading |
| **Mecanum / omni** | 3 (`vₓ`, `v_y`, `ω`) | Yes | `r`, `a`, `b` | Yes | Roller slip (every wheel, always) |

Three takeaways to carry into the rest of the track:

1. **All the nonholonomic models share a heading-dominated drift signature**, exactly as Lecture 1 predicted, and exactly because the calibration error always lands in the `ω` (or `δ`) channel. The fix is always the same: a heading sensor (gyro), Phase 2.
2. **Holonomy is not free.** Mecanum buys you lateral motion and pays for it with worse odometry. If your application does not *need* to strafe, a diff-drive base will localize better with cheaper hardware. Pick holonomy deliberately, not by default.
3. **The model dictates the message.** Diff-drive and mecanum take `geometry_msgs/Twist`; Ackermann takes `ackermann_msgs/AckermannDrive`. Sending a `Twist` with a nonzero `angular.z` to an Ackermann base at `vₓ = 0` commands a spin-in-place the vehicle physically cannot do — a category error that the type system *should* but does not catch, so you catch it by knowing the model.

## 2.9 — Pose integration: Euler vs exact arc vs SE(2) exponential

You have a body twist `(vₓ, ω)` each cycle (from whichever model). Lecture 1 integrated it; now we earn the right to that integration by comparing three schemes and quantifying the error of the cheap one. Over one cycle of duration `Δt` with a *constant* twist:

**Scheme 1 — Euler (rectangular).** Assume the robot points in its *start-of-cycle* heading for the whole step:

```
x  += vₓ · cos(θ) · Δt
y  += vₓ · sin(θ) · Δt
θ  += ω · Δt
```

Cheap, one `sin`/`cos`, and the form everyone writes first. Its error: it lays the position increment along the *old* heading even though the heading is rotating during the step, producing a cross-track error that grows with `ω·Δt`. At 50 Hz (`Δt = 0.02 s`) and a brisk `ω = 1 rad/s`, `ω·Δt = 0.02 rad ≈ 1.1°` of un-accounted rotation per step — small, but it accumulates over a turn.

**Scheme 2 — Exact arc.** A constant twist traces a circular arc of radius `R = vₓ/ω`. Integrate along the arc exactly:

```
if |ω| > ε:
    x += (vₓ/ω) · ( sin(θ + ω·Δt) − sin(θ) )
    y += (vₓ/ω) · ( cos(θ) − cos(θ + ω·Δt) )
    θ += ω·Δt
else:                       # straight-line limit, avoids divide-by-zero
    x += vₓ · cos(θ) · Δt
    y += vₓ · sin(θ) · Δt
```

This is exact *for a constant twist over the cycle* and removes essentially all of the Euler cross-track error. It is the integrator your mini-project node uses, and it is what you ran in Lecture 1's `integrate()` function. The `|ω| > ε` guard is mandatory — at `ω = 0` the arc radius is infinite and the formula divides by zero; the straight-line branch is the limit.

**Scheme 3 — SE(2) matrix exponential.** The mathematically pure form: a twist is an element of the Lie algebra `se(2)`, and the pose increment is its exponential map `exp([twist]·Δt) ∈ SE(2)`. Worked out, it produces *exactly* the exact-arc formulas of Scheme 2 — they are the same thing, with Scheme 3 being the coordinate-free derivation and Scheme 2 the expanded result. Knowing they coincide is worth it: it tells you the exact-arc integrator is not an ad-hoc trick but the genuine `SE(2)` exponential, which is why it is *exact* for constant twist and why no further refinement helps unless the twist *varies* within a cycle (which a higher sample rate fixes more cheaply than a fancier integrator).

### When does the difference matter?

Quantitatively: the Euler-vs-arc discrepancy per step scales like `vₓ·ω·Δt²`. At 50 Hz it is sub-millimeter and you will never see it. At **10 Hz during a 90°/s spin** it becomes tens of centimeters over a full square — visible in your Thursday closure error and easily mistaken for a calibration error. The rule: **use the exact-arc integrator and run your odometry loop at the rate your `/joint_states` arrives (typically 30–50 Hz).** If you ever see closure error that *grows when you slow your loop rate down*, you are looking at integration error (Lecture 1, Class 4), not calibration — and the fix is software, not a wrench.

## 2.10 — Hands-on: derive and check the diff-drive and mecanum Jacobians

Reproduce the two Jacobians numerically so the algebra is not just on the page. Save as `jacobians.py` and run with `python3 jacobians.py`.

```python
#!/usr/bin/env python3
"""Week 6 Lecture 2 — verify the diff-drive and mecanum kinematic Jacobians.

For diff-drive we confirm that forward kinematics (wheels -> twist) and
inverse kinematics (twist -> wheels) are exact inverses, because J is square.
For mecanum we confirm that forward kinematics is well-defined but the inverse
is a least-squares pseudoinverse, and that a round-trip twist -> wheels -> twist
is exact while wheels -> twist -> wheels is NOT (information is lost).
"""
import numpy as np

# ----- Differential drive -----
r = 0.05      # wheel radius [m]
L = 0.30      # wheel separation [m]

# Forward kinematics matrix:  [vx, w]^T = J @ [phidot_L, phidot_R]^T
J_diff = np.array([
    [r / 2.0,  r / 2.0],
    [-r / L,   r / L],
])

def diff_forward(phidot_L, phidot_R):
    return J_diff @ np.array([phidot_L, phidot_R])

def diff_inverse(vx, w):
    return np.linalg.inv(J_diff) @ np.array([vx, w])

# Round trip: a commanded twist -> wheels -> twist must return the input.
vx_cmd, w_cmd = 0.4, 0.6
phidot_L, phidot_R = diff_inverse(vx_cmd, w_cmd)
vx_back, w_back = diff_forward(phidot_L, phidot_R)
print("=== Differential drive (square, invertible J) ===")
print(f"  commanded twist:  vx={vx_cmd:.3f}  w={w_cmd:.3f}")
print(f"  wheel speeds:     L={phidot_L:.3f}  R={phidot_R:.3f}  rad/s")
print(f"  recovered twist:  vx={vx_back:.3f}  w={w_back:.3f}")
print(f"  round-trip error: {np.linalg.norm([vx_back-vx_cmd, w_back-w_cmd]):.2e}")
print(f"  det(J) = {np.linalg.det(J_diff):.4f}  (nonzero -> invertible)\n")

# ----- Mecanum (4 wheels) -----
a = 0.20      # half track width [m]
b = 0.15      # half wheelbase [m]
rm = 0.05     # mecanum wheel radius [m]

# Forward kinematics: [vx, vy, w]^T = M @ [p1, p2, p3, p4]^T  (3x4, non-square)
k = 1.0 / (a + b)
M = (rm / 4.0) * np.array([
    [1.0,  1.0,  1.0,  1.0],     # vx
    [-1.0, 1.0,  1.0, -1.0],     # vy
    [-k,   k,    -k,   k],       # w  (the /4 cancels the geometric factor below)
])
# Correct the w row: yaw uses (a+b) scaling without the /4 averaging of vx/vy.
M[2, :] = (rm / (4.0 * (a + b))) * np.array([-1.0, 1.0, -1.0, 1.0])

def mec_forward(wheels):
    return M @ np.array(wheels)

# Pseudoinverse for the inverse problem (twist -> wheels), least-squares.
M_pinv = np.linalg.pinv(M)

def mec_inverse(vx, vy, w):
    return M_pinv @ np.array([vx, vy, w])

print("=== Mecanum (3x4 M, pseudoinverse inverse) ===")
twist_cmd = np.array([0.3, 0.2, 0.4])      # vx, vy, w
wheels = mec_inverse(*twist_cmd)
twist_back = mec_forward(wheels)
print(f"  commanded twist:  vx={twist_cmd[0]:.3f} vy={twist_cmd[1]:.3f} w={twist_cmd[2]:.3f}")
print(f"  wheel speeds:     {np.array2string(wheels, precision=3)}")
print(f"  recovered twist:  vx={twist_back[0]:.3f} vy={twist_back[1]:.3f} w={twist_back[2]:.3f}")
print(f"  twist round-trip error: {np.linalg.norm(twist_back - twist_cmd):.2e}"
      "   (small -> forward o inverse = identity on twist)")

# But the OTHER round trip loses information: arbitrary wheels -> twist -> wheels
wheels_arbitrary = np.array([1.0, -2.0, 3.0, 0.5])
twist_mid = mec_forward(wheels_arbitrary)
wheels_back = mec_inverse(*twist_mid)
print(f"\n  arbitrary wheels:   {np.array2string(wheels_arbitrary, precision=3)}")
print(f"  -> twist -> wheels: {np.array2string(wheels_back, precision=3)}")
print(f"  wheel round-trip error: {np.linalg.norm(wheels_back - wheels_arbitrary):.2e}"
      "   (LARGE -> the 4D wheel space does not survive the 3D twist bottleneck)")
print("\n  Interpretation: mecanum forward kinematics throws away one dimension")
print("  of wheel motion (the internal-strain / slip mode). That discarded mode")
print("  is exactly where roller slip hides -> worse odometry than diff-drive.")
```

Run it. The diff-drive round trip returns near machine-zero error (the 2×2 Jacobian is a true inverse). The mecanum *twist* round trip is also near zero — `forward(inverse(twist))` is the identity — but the *wheel* round trip has a large residual, because the 4-dimensional wheel-velocity space is squeezed through a 3-dimensional twist and the discarded fourth dimension is precisely the internal-strain / slip mode. **That discarded dimension is where mecanum's extra odometry error lives.** Seeing the residual be *large* on your own machine is the numerical proof of §2.7's claim: four encoders, three observable DOF, one unobservable slip mode that drift accumulates in.

## 2.11 — From model to message: what each base presents to ROS2

The five models are mathematics; ROS2 is plumbing. The bridge between them is the *message type* a base accepts and the *message type* it emits, and getting this mapping right is half of not fighting your stack. Memorize this table — it is the practical payoff of the whole lecture.

| Model | Command message (in) | Odometry message (out) | The controller that does the translation |
|---|---|---|---|
| **Diff-drive** | `geometry_msgs/Twist` (`linear.x`, `angular.z`) | `nav_msgs/Odometry` | `diff_drive_controller` (ros2_control) |
| **Unicycle** | `geometry_msgs/Twist` (same two fields) | `nav_msgs/Odometry` | n/a — the abstraction Nav2 commands in |
| **Bicycle / Ackermann** | `ackermann_msgs/AckermannDriveStamped` (`speed`, `steering_angle`) | `nav_msgs/Odometry` | `ackermann_steering_controller` (ros2_control) |
| **Mecanum / omni** | `geometry_msgs/Twist` (all three: `linear.x`, `linear.y`, `angular.z`) | `nav_msgs/Odometry` | `mecanum_drive_controller` (ros2_control) |

Three things to internalize from the table:

1. **Nav2 only speaks `Twist`.** Every nonholonomic planner in Nav2 emits a `geometry_msgs/Twist` with `linear.x` and `angular.z` — unicycle commands (§2.2). The *base-specific controller* is the only component that knows whether those two numbers become wheel speeds (diff-drive), a steering angle (Ackermann), or four wheel speeds (mecanum). This is why you can run the *same* Nav2 stack on a diff-drive robot and an Ackermann car: the planner is model-agnostic and the controller is model-specific. The seam is exactly the `(vₓ, ω)` unicycle interface.

2. **`linear.y` is the holonomy tell.** A nonzero `linear.y` on a `Twist` is *only* meaningful to a holonomic base (mecanum/omni). Send a `Twist` with `linear.y = 0.3` to `diff_drive_controller` and it is silently ignored — the base cannot strafe, so the lateral command evaporates with no error. If you find yourself surprised that "my robot won't go sideways," the question is not "is my command wrong" but "is my base holonomic," and the answer is in the URDF, not the code.

3. **Ackermann has its own message because it has its own constraint.** `ackermann_msgs/AckermannDrive` carries `speed` and `steering_angle` — *not* a yaw rate — because for a car-like base the controllable input *is* the steering angle, and the yaw rate is a derived quantity (`ω = (vₓ/ℓ)tan δ`, §2.5). Forcing a car through a `Twist` interface would require the controller to invert that relationship every cycle and would obscure the steering-rate limit that a real vehicle has. The message type encodes the model's natural control input. When you meet a new platform, the first question is "what message does it take?" — the answer tells you its model.

There is one more subtlety worth a sentence: the odometry *output* is `nav_msgs/Odometry` for *every* model. The downstream consumers (SLAM, the EKF, Nav2's costmap) do not care how the pose was produced — they consume `(pose, twist, covariance)` in the `odom` frame. That uniformity on the *output* side is what lets you swap a diff-drive base for an Ackermann base without rewriting Phase 2. The model-specificity lives entirely on the *input* (command) side and inside the controller; the estimate you publish this week is model-agnostic by design.

## 2.12 — Choosing a model for a real platform: a decision guide

You will, more than once in your career, stand in front of a chassis and have to decide which kinematic model to write code against. Here is the decision guide a senior engineer carries in their head. It is short because the choice is usually forced by the hardware — but knowing *why* it is forced is what lets you defend it.

- **Two driven wheels on a common axle + casters?** Diff-drive. Calibrate `r` and `L`; expect heading-dominated drift; the IMU is your friend. This is 80% of indoor research and warehouse robots, and it is the model the rest of this track assumes.
- **Steered front wheels, driven rear (or front) wheels, no spin-in-place?** Bicycle for odometry, Ackermann for the steering linkage. Calibrate the wheelbase `ℓ` and the steering-angle offset; expect steering-bias-dominated drift. This is every car-like AMR, delivery rover, and autonomous forklift. Note the minimum turning radius — a planner that does not respect it will produce paths the vehicle cannot follow (Phase 3's SMAC Hybrid-A* exists for exactly this reason).
- **Four wheels with angled rollers, need to strafe?** Mecanum. Calibrate `r`, `a`, `b`; expect *worse* odometry than diff-drive (§2.7) and budget for re-localization sooner. Choose this *only* if the application genuinely needs lateral motion (tight-aisle picking, omnidirectional camera dollies). If it does not, you are paying for holonomy in drift you did not have to spend.
- **Three or four omni-wheels in a symmetric layout?** Omnidirectional, same holonomic story as mecanum, same odometry caveat. Common on RoboCup and lab platforms; rare in production because the rollers wear and the drift is hard to bound.

The meta-rule, the one to repeat in a design review: **the model is dictated by the wheels, but the consequences are paid in the estimator.** A holonomic base buys motion freedom and pays in drift; a car-like base buys efficiency and pays in maneuverability; a diff-drive base is the boring, well-behaved default that localizes best for the least money. There is no free lunch in mobile-base kinematics — only trade-offs you make on purpose or make by accident. This week you make them on purpose.

One last connection to the rest of the track: whichever model your capstone platform uses, the *odometry node you build this week* is the template. Diff-drive is the worked example because it is the most common and the cleanest derivation; but the discipline — derive the forward kinematics from the constraint, integrate with the exact-arc scheme, publish honest covariance, stamp from the sample time — is identical for all five. Swap the two-line forward-kinematics block for the bicycle or mecanum equations and the rest of the node is unchanged. Learn it once, here, correctly.

## 2.13 — Summary

- Every model is built on `v_wheel = r·φ̇` plus the no-slip and no-skid constraints; casters contribute no constraint and no odometry.
- The **unicycle** `(ẋ, ẏ, θ̇) = (vₓcos θ, vₓsin θ, ω)` is the integration target every nonholonomic model reduces to; Nav2 commands in this space.
- **Diff-drive** forward kinematics: `vₓ = r(φ̇_R+φ̇_L)/2`, `ω = r(φ̇_R−φ̇_L)/L`. The Jacobian is square and invertible, so inverse kinematics is clean. The ICR sits on the axle line.
- **Bicycle / Ackermann** couple yaw to speed via `ω = (vₓ/ℓ)·tan δ`; they cannot spin in place; Ackermann's two front wheels steer at different angles, but odometry uses the single virtual bicycle angle. Dominant error: steering/heading bias.
- **Mecanum** is holonomic (`vₓ, v_y, ω`) via 45° rollers, but its 3×4 Jacobian is non-square and the rollers slip by design, so its odometry is *worse* than diff-drive despite four encoders.
- Integrate with the **exact-arc / SE(2)-exponential** scheme (they coincide), guard `|ω|>ε`, and run at the joint-state rate; Euler error only shows up at low rates and high turn rates.
- The unifying rule: **odometry quality is set by the constraint structure, not the sensor count**, and every nonholonomic model's dominant error is heading — which is the IMU's job to fix in Phase 2.
- **The model dictates the message**: diff-drive/unicycle/mecanum take `geometry_msgs/Twist` (mecanum uses `linear.y` too); Ackermann takes `ackermann_msgs/AckermannDrive`. Every model emits `nav_msgs/Odometry`, which is why Phase 2 is model-agnostic on its input.
- **Nav2 plans in unicycle space** and the base-specific controller is the only model-aware component; the `(vₓ, ω)` interface is the seam that lets one nav stack drive five different bases.
- **Pick the model on purpose**: the wheels dictate the model, but the consequences are paid in the estimator — holonomy buys strafing and pays in drift; car-like buys efficiency and pays in maneuverability; diff-drive is the well-behaved default.

### Why this lecture sits where it does

You learned QoS and DDS last week so your topics *flow*; you learn kinematics this week so the numbers flowing through them *mean something*. Next week's SLAM and Phase 2's EKF are both, at bottom, machines for correcting the drift these models produce — but neither can correct an estimate that was wrong at the source. A SLAM front-end that gets a heading-biased motion prior matches scans against the wrong predicted pose and works harder for a worse result; an EKF handed a dishonest covariance either ignores good wheels or follows bad ones. The five models are not trivia — they are the contract your odometry node signs with every estimator downstream of it. Sign it correctly here, once, and the rest of the track inherits a clean foundation. Sign it sloppily and you will be debugging "phantom drift" in Week 10 that was actually a Week 6 sign error.

Next: the exercises. You implement diff-drive forward kinematics in an `rclpy` node consuming `/joint_states`, publish `/odom` and the `odom → base_link` TF, then drive the square and measure the drift Lecture 1 taught you to expect.

### The two equations to carry out of this lecture

If you remember only the math — not the derivations, not the comparison table — remember these two lines, because everything you build this week is downstream of them:

```
vₓ = r · (φ̇_R + φ̇_L) / 2          # forward velocity is the SUM
ω  = r · (φ̇_R − φ̇_L) / L          # yaw rate is the DIFFERENCE, divided by L
```

The sum gives you distance, the difference gives you heading, and `L` lives only in the heading term — which is the algebraic reason Lecture 1's wheelbase error landed in the heading channel and dominated the drift. The forward velocity is a *sum*, so a radius error scales it linearly and benignly; the yaw rate is a *difference over L*, so a wheelbase error scales your heading and compounds. These two lines, the exact-arc integrator that turns them into a pose, and the honest covariance that tells the EKF how much to trust the result — that is the entire odometry node, and it is the entire reason the next ten weeks of fusion and SLAM have something to correct. Write them from memory before you open the editor, and the node is twenty minutes of typing instead of an afternoon of sign-chasing.

---

*Re-derive the diff-drive Jacobian (§2.4) on paper from the two scalar equations before the exercises. If you can write the 2×2 matrix and its inverse from memory, the odometry node is twenty minutes of typing. If you cannot, you will fight sign errors all afternoon.*
