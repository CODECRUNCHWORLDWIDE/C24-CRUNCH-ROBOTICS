# Week 16 — Exercises

Three exercises, in order. They build the artifacts you carry into the mini-project and the midterm defense. Exercise 1 turns your perception graph into an interface-contract table and a latency block diagram — the document the panel reads first. Exercise 2 writes the latency probe that measures your end-to-end budget honestly. Exercise 3 writes the detection-to-cluster association that fuses your two detection streams into one object.

Do them in order. Do not skip Exercise 1 because it "is just drawing" — the contract table and the latency budget are the artifacts the panel grades your stack against, and the mini-project assumes you can point at the row that owns each seam. Exercises 2 and 3 are the two pieces of machinery the fused node cannot ship without.

| # | File | Type | What you build | Est. time |
|---|------|------|----------------|-----------|
| 1 | [exercise-01-draw-the-latency-budget.md](./exercise-01-draw-the-latency-budget.md) | Guided (Markdown) | Turn your perception graph into an interface-contract table (topic/type/frame/rate/QoS per seam) and a latency block diagram with a measured budget per hop and the critical-path total. | 90 min |
| 2 | [exercise-02-perception-latency-probe.py](./exercise-02-perception-latency-probe.py) | Runnable (`rclpy`) | A probe node that measures sensor-stamp-to-publish latency end-to-end, reports the p50/p95/p99 distribution, and flags when the budget is blown — the number you defend at the midterm. | 90 min |
| 3 | [exercise-03-detection-cluster-association.py](./exercise-03-detection-cluster-association.py) | Runnable (`rclpy` + `scipy`) | Associate 2D detections with 3D clusters into fused objects via projection + IoU + the Hungarian assignment, handling the no-match and double-match cases explicitly. | 120 min |

## Prerequisites for all three

- ROS2 Jazzy on Ubuntu 24.04, sourced (`source /opt/ros/jazzy/setup.bash`).
- Your composed perception stack from Weeks 9–15, or enough of it that the topics the exercises reference exist. Both `.py` exercises ship a `--demo` mode that publishes synthetic versions of every topic, so you can run and verify them headless before the full stack is live.
- `vision_msgs`, `geometry_msgs`, `std_msgs`, and `scipy` available (`scipy` for the Hungarian solver in Exercise 3; `pip install scipy` if needed).
- The Week 5 QoS literacy: the probe and the association node subscribe to sensor and detection streams, and the wrong QoS silently receives nothing.

## How to run a `.py` exercise

These files run two ways:

1. **Against your live stack** (the real way): source your workspace, bring up the composed graph, then run the node. It introspects the live graph.
2. **Standalone in `--demo` mode** (for fast iteration and CI): `python3 exercise-02-perception-latency-probe.py --demo`. The node spawns synthetic publishers for every topic it consumes, so you can verify the *logic* without the full robot. A `--break` flag forces a failure (a blown budget, a stale input) so you confirm the detection path.

Each file's header block has the exact commands and the expected output.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-16` to compare.
