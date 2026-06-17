# Week 5 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 6. Answer key is at the bottom — don't peek.

---

**Q1.** What is the ROS2 *default* QoS profile (reliability, durability, history, depth) as of Jazzy?

- A) `BEST_EFFORT` / `VOLATILE` / `KEEP_LAST` / 5
- B) `RELIABLE` / `VOLATILE` / `KEEP_LAST` / 10
- C) `RELIABLE` / `TRANSIENT_LOCAL` / `KEEP_ALL` / 1
- D) `BEST_EFFORT` / `TRANSIENT_LOCAL` / `KEEP_LAST` / 10

---

**Q2.** A 30 Hz LiDAR publishes `/scan`. Why is `BEST_EFFORT` the *correct* reliability for it, not a compromise?

- A) `BEST_EFFORT` is faster to type than `RELIABLE`.
- B) A retransmitted scan arrives stale — the next fresh scan is already available and more useful — and reliable retransmit adds head-of-line blocking that can stall the stream.
- C) `RELIABLE` is not supported for `sensor_msgs/LaserScan`.
- D) `BEST_EFFORT` automatically increases the publish rate.

---

**Q3.** A map server publishes `/map` exactly once at startup with default QoS. A localization node subscribes ten seconds later and receives nothing, ever. What is the fix?

- A) Make the map server publish `/map` continuously at 10 Hz.
- B) Increase the subscriber's depth to 1000.
- C) Publish `/map` with `TRANSIENT_LOCAL` durability (and have the subscriber request it too).
- D) Switch the whole graph to CycloneDDS.

---

**Q4.** Publisher offers `BEST_EFFORT`; subscriber requests `RELIABLE`. Same topic, same type, same domain. What happens?

- A) Data flows; reliability is negotiated down to `BEST_EFFORT`.
- B) The subscriber node crashes with an exception at startup.
- C) The endpoints discover each other but no data link forms — a silent failure; an incompatible-QoS event fires that almost nobody listens for.
- D) Data flows but every sample is duplicated.

---

**Q5.** Which two QoS policies do **not** participate in the request–offered compatibility check?

- A) Reliability and durability.
- B) Deadline and liveliness.
- C) History and depth.
- D) Durability and deadline.

---

**Q6.** For deadline, a subscriber requesting a 100 ms deadline is compatible only with a publisher offering a deadline that is:

- A) ≥ 100 ms (slower or equal).
- B) ≤ 100 ms (at least as often).
- C) exactly 100 ms.
- D) any value — deadline never affects compatibility.

---

**Q7.** What does `qos_profile_sensor_data` expand to?

- A) `RELIABLE` / `VOLATILE` / `KEEP_LAST(10)`
- B) `BEST_EFFORT` / `VOLATILE` / `KEEP_LAST(5)`
- C) `RELIABLE` / `TRANSIENT_LOCAL` / `KEEP_LAST(1)`
- D) `BEST_EFFORT` / `TRANSIENT_LOCAL` / `KEEP_ALL`

---

**Q8.** In DDS discovery, which protocol carries the full QoS profile of each endpoint, and over what transport?

- A) SPDP, over unicast.
- B) SEDP, over unicast — and it's where QoS compatibility is actually evaluated.
- C) SPDP, over multicast — compatibility is checked there.
- D) TCP three-way handshake, over multicast.

---

**Q9.** Two terminals run nodes that can't see each other's topics, even though the code is identical and the topic names match. The most likely cause is:

- A) A QoS reliability mismatch.
- B) Different `ROS_DOMAIN_ID` values (or one terminal didn't `export` it) — they're in different domains.
- C) The message type hash changed.
- D) `frame_id` is empty.

---

**Q10.** Which statement about CycloneDDS vs Fast-DDS on Jazzy is correct?

- A) Fast-DDS is the default rmw; you switch to CycloneDDS with `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`, and the same `QoSProfile` behaves identically on both.
- B) CycloneDDS is the default; Fast-DDS cannot run on Ubuntu 24.04.
- C) Switching vendors requires recompiling every node from source.
- D) QoS profiles behave differently on each vendor, so you must rewrite them when switching.

---

**Q11.** A camera node reads a frame, runs 40 ms of inference, then stamps the published detection with `now()`. Why is this wrong?

- A) `now()` is slower than reading the camera stamp.
- B) Every downstream consumer thinks the detection happened 40 ms later than it did; on a robot moving 1 m/s that injects ~4 cm of error that compounds. The stamp must be the *acquisition* time.
- C) Detections cannot carry a `std_msgs/Header`.
- D) Nothing is wrong; publish-time stamping is the convention.

---

**Q12.** You append one field to a custom `.msg` and rebuild only the publisher, not the old subscribers. What happens, and why?

- A) Nothing changes; ROS2 messages are forward-compatible like Protobuf optional fields.
- B) The new publisher and the old subscribers have different type hashes (RIHS), so they refuse to connect — loudly telling you to rebuild both ends.
- C) The old subscribers silently deserialize garbage into the new field.
- D) The publisher crashes because the message is now larger.

---

**Q13.** On `/cmd_vel`, why is `KEEP_LAST(1)` correct and a deep history (e.g. `KEEP_LAST(50)`) dangerous?

- A) Deep queues use too much RAM on an embedded robot.
- B) Only the latest velocity command matters; a deep queue lets stale commands drain into the motors after a hiccup — "the robot kept driving after I let go of the joystick."
- C) `/cmd_vel` must be `BEST_EFFORT`, which forbids deep queues.
- D) Depth participates in compatibility, so a deep queue breaks the connection.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — The ROS2 default is `RELIABLE` / `VOLATILE` / `KEEP_LAST(10)`. That default is wrong for sensors (should be `BEST_EFFORT`) and for latched maps (should be `TRANSIENT_LOCAL`), which is the whole premise of the week.
2. **B** — High-rate, time-sensitive, "the next one fixes a drop." Reliable retransmit delivers stale data and adds head-of-line blocking. (Lecture 1 §2.1.)
3. **C** — The map is latched state; it needs `TRANSIENT_LOCAL` so late subscribers get the cached sample. Durability is a two-sided handshake, so the subscriber must request it too. (Lecture 1 §2.2.)
4. **C** — The request–offered rule: a `BEST_EFFORT` publisher cannot satisfy a `RELIABLE` subscriber. Endpoints are discovered (visible in `ros2 topic info -v`) but no data flows. The silent failure. (Lecture 1 §3.)
5. **C** — History and depth are local resource decisions; they do not participate in compatibility. Reliability, durability, deadline, and liveliness do. (Lecture 1 §3.)
6. **B** — The publisher must promise *at least* as often as the subscriber demands: offered period ≤ requested period. (Lecture 1 §2.4.)
7. **B** — `BEST_EFFORT` / `VOLATILE` / `KEEP_LAST(5)`. The right profile for sensor streams on both ends. (Lecture 1 §4.)
8. **B** — SEDP (Simple Endpoint Discovery Protocol), unicast, carries topic/type/QoS and is where compatibility is evaluated. SPDP (multicast) only finds participants. (Lecture 2 §1.2–1.3.)
9. **B** — Different `ROS_DOMAIN_ID` (or a forgotten `export`) means different domains; participants never discover each other. The symptom looks like a QoS mismatch but has a different fix — which is why the decision tree checks `ros2 topic list` (discovery) before QoS. (Lecture 2 §1.1, §4.)
10. **A** — Fast-DDS is the Jazzy default rmw; CycloneDDS is one `RMW_IMPLEMENTATION` away; QoS is portable across vendors. (Lecture 2 §2.1–2.2.)
11. **B** — Stamp at acquisition time, not publish time. Late stamping injects motion-proportional error that tf2 and the EKF then trust. (Lecture 2 §3.1.)
12. **B** — ROS2 uses the type hash to gate connections; changing the `.msg` changes the hash; mismatched hashes refuse to connect. Unlike Protobuf, "additive" is not free — it's a redeploy-everything event, which the system enforces loudly. (Lecture 2 §3.4.)
13. **B** — Only the latest command is meaningful; a deep queue drains stale velocities into the motors after a scheduling hiccup. History doesn't break the connection — it breaks the robot. (Lecture 1 §5, Class 3.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./06-homework.md).
