# Week 32 — Exercises

Three exercises, in order. They build the leash from Lecture 1 and the predictive filter and intervention meter from Lecture 2 into runnable artifacts you carry into the mini-project and defend at the second-midterm review. Exercise 1 defines the *constraint set* for your robot — the bounds everything else checks against. Exercise 2 builds the predictive safety filter that rolls an action forward and projects-or-rejects. Exercise 3 builds the three-rejection fallback switch and the intervention meter that produces the numbers you defend at the review.

Do them in order. Exercise 1's constraint set is the input to Exercise 2's filter; Exercise 2's verdicts are the input to Exercise 3's fallback and meter. The mini-project's launch graph cannot run without all three.

| # | File | Type | What you build | Est. time |
|---|------|------|----------------|-----------|
| 1 | [exercise-01-bound-the-action-space.md](./exercise-01-bound-the-action-space.md) | Guided (Markdown + code) | The constraint set for your robot — velocity, acceleration, joint-limit, and workspace bounds — plus the correct uniform-rescale clamp (vs. the wrong per-channel saturation), proven on a curved path. | 60 min |
| 2 | [exercise-02-runtime-safety-filter.py](./exercise-02-runtime-safety-filter.py) | Runnable (`rclpy`) | A predictive safety filter node that rolls a candidate action forward, checks the constraint set over a short horizon, projects-or-rejects, and counts every clamp and rejection — with a demo mode that drives synthetic safe and unsafe actions through it. | 120 min |
| 3 | [exercise-03-fallback-and-intervention-rate.py](./exercise-03-fallback-and-intervention-rate.py) | Runnable (`rclpy`) | The three-consecutive-rejection fallback switch and the intervention-rate meter (rejections by constraint, fallback-episode rate, filter latency), reported as a distribution you can defend. | 120 min |

## Prerequisites for all three

- ROS2 Jazzy on Ubuntu 24.04, sourced (`source /opt/ros/jazzy/setup.bash`).
- Your **best learned policy** from Weeks 29–31 (Diffusion Policy / ACT / fine-tuned VLA), or enough of it that it emits actions on a topic. Both `.py` exercises ship a `--demo` mode that drives synthetic policy actions (safe and deliberately-unsafe) so you can verify the *filter logic* without the full policy live.
- Your **classical fallback** available — MoveIt2 for the arm or a sampling planner for the base — for Exercise 3's fallback branch. The demo mode stubs the fallback so you can test the *switch* without the full planner.
- `geometry_msgs`, `sensor_msgs`, `std_msgs`, and `vision_msgs` available (standard Jazzy desktop install).
- `numpy` for the roll-forward model; optionally `cvxpy` or `osqp` for the CBF stretch goal.

## How to run a `.py` exercise

These files run two ways:

1. **Against your live policy** (the real way): source your workspace, bring up the policy + controller, then `python3 exercise-02-runtime-safety-filter.py`. The node intercepts the policy's action topic, filters it, and republishes the filtered action.
2. **Standalone in `--demo` mode** (for fast iteration and CI): `python3 exercise-02-runtime-safety-filter.py --demo`. The node drives a scripted sequence of safe and unsafe synthetic actions through the filter so you can confirm the PASS / CLAMP / REJECT verdicts without the full robot. Flip `--unsafe-burst` to drive three rejections in a row and confirm the fallback fires in Exercise 3.

Each file's header block has the exact commands and the expected output.

## The non-negotiable property

By the end of these three exercises, your wrapper must **fire** — clamp, reject, and fall back — on the deliberately-unsafe actions, and **pass** the safe ones. A wrapper that passes everything is the too-loose-filter defect (Lecture 1 §2, Defect 4) and is the worst possible result, because it provides no protection while *looking* like success. Exercise 2's demo includes unsafe actions specifically so you can prove your filter catches them. If your filter passes the through-the-table action in the demo, you are not done.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-32` to compare.
