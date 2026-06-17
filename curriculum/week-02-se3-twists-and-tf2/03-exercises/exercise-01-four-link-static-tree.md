# Exercise 1 — Build the four-link static tree

**Goal:** Stand up a complete `base → shoulder → elbow → wrist` tf2 tree using nothing but the `static_transform_publisher` command-line tool — one process per joint. Verify it is a single connected tree with `view_frames`, read individual edges back with `tf2_echo`, and visualize the whole thing in `rviz2`. This is the "publish the edges, ask tf2 for paths" workflow in its simplest form.

**Estimated time:** 45 minutes.

---

## Why static-only first

Every joint in this exercise is published as a **static** transform: it goes out once on `/tf_static` (latched, `TRANSIENT_LOCAL` QoS) and never changes. That is wrong for a real arm — an elbow rotates — but it is exactly right for learning the tree, because nothing moves and nothing can be stale. You will replace one edge with a dynamic broadcaster in Exercise 2. Walk before you run: get a connected, inspectable tree first.

The arm we are modeling, with the numbers you will publish:

```text
        base
          │  base → shoulder:  +0.10 m in z (the shoulder sits 10 cm above the base), no rotation
       shoulder
          │  shoulder → elbow: +0.25 m in x (the upper arm is 25 cm long), no rotation
        elbow
          │  elbow → wrist:    +0.20 m in x (the forearm is 20 cm long), no rotation
        wrist
```

All translations, no rotations, for now. We add rotation when the joint becomes dynamic.

---

## Step 0 — Source ROS2

In every terminal:

```bash
source /opt/ros/jazzy/setup.bash
```

Confirm the daemon is alive:

```bash
ros2 topic list
```

You should see at least `/parameter_events` and `/rosout`. If `ros2` is "command not found," you have not sourced Jazzy.

---

## Step 1 — Publish the first edge: base → shoulder

The Jazzy `static_transform_publisher` takes **named** arguments. The argument order learners remember from older ROS2 (`x y z yaw pitch roll`) still works positionally, but use the named form — it is self-documenting and it is what you will write in launch files.

Open terminal 1:

```bash
ros2 run tf2_ros static_transform_publisher \
  --x 0 --y 0 --z 0.10 \
  --roll 0 --pitch 0 --yaw 0 \
  --frame-id base --child-frame-id shoulder
```

The node starts and stays running (it has to — it owns the latched publication). Leave it. You will see one log line confirming the static transform was sent. The `--frame-id` is the **parent**; `--child-frame-id` is the **child**. The transform expresses the child *in* the parent.

---

## Step 2 — Publish the other two edges

Open terminal 2:

```bash
ros2 run tf2_ros static_transform_publisher \
  --x 0.25 --y 0 --z 0 \
  --roll 0 --pitch 0 --yaw 0 \
  --frame-id shoulder --child-frame-id elbow
```

Open terminal 3:

```bash
ros2 run tf2_ros static_transform_publisher \
  --x 0.20 --y 0 --z 0 \
  --roll 0 --pitch 0 --yaw 0 \
  --frame-id elbow --child-frame-id wrist
```

You now have three processes, each owning one edge of the tree. This is deliberately ugly — three terminals for a three-edge tree — and it is exactly why launch files exist (the mini-project fixes it). For now, the ugliness makes the "one process per edge" model concrete.

---

## Step 3 — Confirm it is *one* tree

Open a fourth terminal and render the tree:

```bash
ros2 run tf2_tools view_frames
```

This listens to `/tf` and `/tf_static` for a few seconds, then writes `frames.pdf` and `frames.gv` to the current directory. Open the PDF:

```bash
xdg-open frames.pdf      # or: evince frames.pdf
```

You must see **exactly this**, a single connected chain:

```text
base ──▶ shoulder ──▶ elbow ──▶ wrist
```

Each edge is annotated with `Broadcaster`, `Average rate`, `Buffer length`, and the most-recent/oldest transform times. For static transforms the rate shows as a very large number or `10000.0` — static frames are reported with a sentinel high rate because they never expire.

**If you see two trees, or an orphan `wrist` with no parent**, one of your publishers is not running or you typed a frame name wrong (`sholder` instead of `shoulder` is the classic). Fix it and re-run `view_frames`. Do not proceed until the PDF shows one connected tree.

---

## Step 4 — Read an edge back with tf2_echo

`view_frames` shows the shape. `tf2_echo` shows the numbers. Ask for the wrist expressed in the base:

```bash
ros2 run tf2_ros tf2_echo base wrist
```

The argument order is `tf2_echo <target_frame> <source_frame>` — "give me the transform that puts a point from `source` into `target`." It prints once per second. You should see translation `[0.450, 0.000, 0.100]` and an identity rotation:

```text
At time 0.0
- Translation: [0.450, 0.000, 0.100]
- Rotation: in Quaternion [0.000, 0.000, 0.000, 1.000]
- Rotation: in RPY (radian) [0.000, 0.000, 0.000]
- Rotation: in RPY (degree) [0.000, 0.000, 0.000]
- Matrix:
  1.000  0.000  0.000  0.450
  0.000  1.000  0.000  0.100
  0.000  0.000  1.000  0.100
  ...
```

**Check the math by hand.** The wrist is `0.25 + 0.20 = 0.45 m` in x from the shoulder, and the shoulder is `0.10 m` in z from the base, all with no rotation. So `base → wrist` is `[0.45, 0, 0.10]`. That `0.450` in the translation is tf2 composing three edges for you — `T_base_wrist = T_base_shoulder @ T_shoulder_elbow @ T_elbow_wrist` — which is exactly the SE(3) composition from lecture 2. You just watched the tree walk happen.

Stop `tf2_echo` with `Ctrl+C`.

---

## Step 5 — Visualize in rviz2

```bash
rviz2
```

In rviz2:

1. Set **Fixed Frame** (top-left, under "Global Options") to `base`. If `base` is not in the dropdown, your tree is not connected — go back to Step 3.
2. Click **Add** (bottom-left) → **By display type** → **TF** → **OK**.
3. Expand the **TF** display. You will see all four frames as axis triads, each labelled. The wrist triad sits up and forward of the base, exactly where the numbers say.

Turn on **Show Names** and **Show Axes** in the TF display options if they are not already on. You should see four labelled triads in a connected chain. That is your SE(3) tree, rendered.

---

## Step 6 — Watch the raw messages

In a spare terminal, look at what is actually on the wire:

```bash
ros2 topic echo /tf_static
```

Because `/tf_static` is latched, a brand-new subscriber still receives the last value of every static transform — you get all three `TransformStamped` entries immediately even though they were published seconds ago, before this `echo` started. That latching is the whole reason static transforms can be published once and forgotten. Contrast with `/tf` (Exercise 2), which is *not* latched: a late subscriber there sees nothing until the next broadcast.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] Three `static_transform_publisher` processes are running, one per joint.
- [ ] `ros2 run tf2_tools view_frames` produces a `frames.pdf` showing a **single connected tree** `base → shoulder → elbow → wrist` with no orphans and no second root.
- [ ] `ros2 run tf2_ros tf2_echo base wrist` reports translation `[0.450, 0.000, 0.100]` and identity rotation.
- [ ] In `rviz2` with Fixed Frame `base`, all four frames appear as labelled axis triads in a connected chain.
- [ ] You can state, in one sentence, why `ros2 topic echo /tf_static` shows you all three transforms the instant you start it.

---

## Stretch

- Re-publish the `shoulder → elbow` edge with a 90° yaw (`--yaw 1.5708`) and re-run `tf2_echo base wrist`. Predict the new wrist position **before** you read the output, then check. (Hint: rotating the upper-arm frame rotates everything downstream of it.)
- Kill the `shoulder → elbow` publisher (`Ctrl+C` in terminal 2) and immediately re-run `view_frames`. Confirm the tree splits into two: `base → shoulder` and an orphaned `elbow → wrist`. This is the `ConnectivityException` condition you will trigger deliberately in Exercise 3.
- Put all three publishers in a single launch file (`tree.launch.py`) using `Node(package='tf2_ros', executable='static_transform_publisher', arguments=[...])`. This is a preview of the mini-project; if you do it now, the mini-project is half done.

---

## Hints

<details>
<summary>If <code>base</code> does not appear in the rviz2 Fixed Frame dropdown</summary>

rviz2 only offers frames it currently sees in the tf tree. If `base` is missing, no broadcaster is publishing an edge whose parent is `base` — check terminal 1's publisher is still alive. Also confirm the rviz2 you launched sourced the same ROS2 distro (Jazzy) as your publishers; a mismatched `ROS_DOMAIN_ID` will hide everything.

</details>

<details>
<summary>If <code>view_frames</code> writes a PDF but it is empty / says "no tf data received"</summary>

`view_frames` listens for a few seconds and then renders. If your publishers started *after* `view_frames` began listening, or if they crashed, you get an empty graph. For static transforms specifically: `view_frames` does subscribe to `/tf_static` with the correct latched QoS in Jazzy, so a running static publisher will be captured — re-run `view_frames` and make sure the publishers are alive the whole time.

</details>

<details>
<summary>If <code>tf2_echo</code> prints <code>Could not transform</code> repeatedly</summary>

You probably swapped the argument order. It is `tf2_echo <target> <source>`. `tf2_echo base wrist` asks for `T_base_wrist`. If you wrote `tf2_echo wrist base` you get the inverse, which is also valid here — but if you used a frame name that does not exist, you get a `LookupException`-style message. Run `view_frames` to confirm the exact spelling of every frame.

</details>

---

When this tree feels solid, move to [Exercise 2 — Add a dynamic broadcaster](./exercise-02-dynamic-broadcaster.py).
