# Week 2 — Quiz

Twelve multiple-choice questions. Take it with your lecture notes closed. Aim for 10/12 before starting Week 3. Answer key at the bottom — don't peek.

---

**Q1.** A 4×4 homogeneous transform is written `T = [[R, t], [0, 0, 0, 1]]`. Why is the bottom row `[0 0 0 1]`?

- A) It is an arbitrary convention; any nonzero bottom row works.
- B) It makes the last coordinate of a homogeneous point pass through unchanged, so the affine map `R@p + t` becomes a single matrix multiply.
- C) It encodes the scale factor of the transform; `1` means "no scaling."
- D) It is required so that `det(T) = 1`.

---

**Q2.** You have `T_a_b` (puts a point from frame `b` into frame `a`) and `T_b_c`. Which product gives `T_a_c`?

- A) `T_b_c @ T_a_b`
- B) `T_a_b @ T_b_c`
- C) `T_a_b @ inv(T_b_c)`
- D) `inv(T_a_b) @ T_b_c`

---

**Q3.** What is the correct, cheap inverse of an SE(3) element `T = [[R, t], [0, 1]]`?

- A) `numpy.linalg.inv(T)` — there is no cheaper way.
- B) `[[R.T, -R.T @ t], [0, 1]]`
- C) `[[R.T, t], [0, 1]]`
- D) `[[R.T, -t], [0, 1]]`

---

**Q4.** You apply a homogeneous transform `T` to a free vector (a velocity direction) by appending a `0` instead of a `1`: `T @ [d, 0]`. What happens to the vector?

- A) It is rotated and translated, like a point.
- B) It is rotated by `R` but **not** translated.
- C) It is translated by `t` but **not** rotated.
- D) Nothing — the `0` makes the result zero.

---

**Q5.** A twist is the element of the Lie algebra se(3). In the **ROS** ordering used throughout this course, a twist is written:

- A) `[ω, v]` — angular part first, matching *Modern Robotics*.
- B) `[v, ω]` — linear part first, matching `geometry_msgs/Twist`.
- C) `[v]` only — twists have no angular component.
- D) A 4×4 matrix; twists are not vectors.

---

**Q6.** Why does a point transform with `T` but a velocity (twist) transform with the adjoint `Ad_T`?

- A) They don't — both use `T`; the adjoint is only for rotations.
- B) A twist is a 6-vector describing instantaneous motion; expressing the same motion in a different frame couples the linear and angular parts through the frame's offset, which is exactly what the 6×6 `Ad_T` encodes.
- C) The adjoint is a numerical optimization; `T` would also work but is slower.
- D) Velocities are not affected by translation, so `Ad_T` is just `R` padded with zeros.

---

**Q7.** In a tf2 tree, how many parents may a frame have?

- A) Any number — tf2 is a general graph.
- B) Exactly one (except the root, which has none). tf2 enforces this; it is what makes the structure a tree.
- C) At most two — one static, one dynamic.
- D) Zero — frames are independent and the buffer connects them on demand.

---

**Q8.** Which statement about `/tf` versus `/tf_static` is correct?

- A) Both are latched; a late subscriber always gets the last value on either.
- B) `/tf_static` is latched (`TRANSIENT_LOCAL` QoS) so a late subscriber gets the last value; `/tf` is not latched, so a late subscriber sees nothing until the next broadcast.
- C) `/tf` is latched; `/tf_static` is not.
- D) Neither is latched; both require the subscriber to start before the publisher.

---

**Q9.** A listener calls `lookup_transform("base", "wrist", Time(0))`. What does `Time(0)` request?

- A) The transform exactly at epoch time zero (1970-01-01).
- B) The **latest available** transform tf2 can compose — the most recent one, not a pinned timestamp.
- C) An error — `Time(0)` is invalid.
- D) The oldest transform still in the buffer.

---

**Q10.** A lookup throws `ConnectivityException`. What does that mean, precisely?

- A) A named frame does not exist in the buffer.
- B) Both frames exist, but they are in two separate trees — there is no path between them.
- C) The requested time is outside the buffered window.
- D) The DDS discovery failed and no transforms are arriving.

---

**Q11.** A broadcaster stamps every transform with `now() - 2.0s`. A listener asks for `Time(0)` (latest) with zero timeout. What error fires and why?

- A) `LookupException`, because the stale stamp deletes the frame.
- B) `ExtrapolationException` for extrapolation **into the future**, because "latest" resolves to a time newer than the buffer's most-recent (2 s old) sample.
- C) `ConnectivityException`, because stale data disconnects the tree.
- D) No error — `Time(0)` always succeeds regardless of stamps.

---

**Q12.** Your listener comes up before its broadcaster and hits an empty-buffer failure on the first lookup. What is the correct fix?

- A) Increase the buffer cache duration to 60 seconds.
- B) Switch from `Time(0)` to a fixed timestamp in the past.
- C) Pass a nonzero `timeout` to `lookup_transform`, so it blocks until the transform becomes available (or the timeout elapses).
- D) Catch and ignore the exception forever; it is harmless.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — The `[0 0 0 1]` row is precisely what lifts the affine map into a linear one in homogeneous coordinates: it preserves the trailing `1` so `T @ [p, 1]` yields `[R@p + t, 1]`. It is not arbitrary (A), encodes no scale (C), and `det(T) = det(R) = 1` is a consequence of `R ∈ SO(3)`, not of the bottom row (D).
2. **B** — Frame naming makes this mechanical: `T_a_b @ T_b_c` — the inner `b` indices "cancel," leaving `T_a_c`. This is the SE(3) composition the tf2 tree walk performs.
3. **B** — For an SE(3) element, the inverse is `R.T` for the rotation block and `-R.T @ t` for the translation. It is exact, cheaper than a general 4×4 inverse, and numerically cleaner. `numpy.linalg.inv` (A) works but throws away the structure. C and D have the translation wrong.
4. **B** — Appending a `0` zeroes out the `t` contribution: `T @ [d, 0] = [R@d, 0]`. Directions rotate but do not translate. This is the points-get-a-1, directions-get-a-0 rule, and getting it wrong puts your LiDAR rays in the wrong place.
5. **B** — This course uses the ROS ordering `[v, ω]` (linear first) because that is what `geometry_msgs/Twist` gives you. *Modern Robotics* uses `[ω, v]`; we flag the swap whenever we cite the textbook (A is the MR convention, not ours).
6. **B** — A twist couples linear and angular components; re-expressing it in another frame mixes them according to the frame offset, which is exactly the structure of the 6×6 adjoint. A point has no angular part, so the homogeneous `T` suffices. D is wrong: translation absolutely affects how a twist's linear part transforms.
7. **B** — Exactly one parent per frame (root excepted). tf2 enforces single-parent; two broadcasters claiming the same child produce `TF_OLD_DATA`/`frame already has a parent` warnings and nondeterministic results. The single-parent rule is what makes it a tree, not a graph.
8. **B** — `/tf_static` uses `TRANSIENT_LOCAL` (latched) QoS, so a subscriber that joins late still receives the last static transform. `/tf` is volatile; a late subscriber waits for the next broadcast. This is why static transforms can be published once and forgotten.
9. **B** — `Time(0)` is the "latest available" sentinel: compose the most recent transform you can, do not pin a specific stamp. It is the forgiving default for "where is X right now."
10. **B** — `ConnectivityException`: both frames exist but live in disconnected trees, so no path can be composed. Compare to `LookupException` (A — a frame is missing) and `ExtrapolationException` (C — a time problem).
11. **B** — The newest data in the buffer is 2 s old; "latest" resolves to that, but the listener's clock-driven request is newer, so the lookup would require extrapolating *into the future*. This is the most common real-world extrapolation cause: a node forwarding a stale stamp instead of stamping afresh.
12. **C** — A nonzero `timeout` makes `lookup_transform` block until the transform is available, absorbing the startup race. Bumping the cache (A) addresses past-extrapolation, not an empty buffer; a fixed past time (B) makes it worse; ignoring it (D) means the node silently does nothing on every cold boot.

</details>

---

If you scored under 8, re-read lecture 1 (the tf2 section) and lecture 2 (SE(3) and the adjoint) for the questions you missed. If you scored 10 or higher, you're ready for the [homework](./06-homework.md) and the [mini-project](./07-mini-project/00-overview.md).
