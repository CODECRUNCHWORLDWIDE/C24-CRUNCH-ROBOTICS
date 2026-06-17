# Week 45 — Exercises

Three drills. The first is a paired mock interview (allow a full block); the second and third are runnable Python you must get to pass. Do them in order — the third grades the first two.

## Index

1. **[Exercise 1 — System-design mock interview](./exercise-01-system-design-mock.md)** — run a 45-minute system-design mock with a peer: design the autonomy stack for a warehouse AMR. Includes the interviewer script, the candidate checklist, and the rubric. (~90 min with a peer)
2. **[Exercise 2 — The EKF predict step on the board](./exercise-02-ekf-predict-on-the-board.py)** — implement and verify the EKF predict (and update) step you will reproduce on the whiteboard. Fill in the marked sections; the built-in checks must all pass. (~60 min)
3. **[Exercise 3 — Self-grade both mocks](./exercise-03-self-grade-mocks.py)** — feed your two mock scores into the rubric tool, get a weighted result, and have it rank your two weakest topics for the study plan. (~30 min)

## How to work the exercises

- **Exercise 1 needs a human on the other side.** A peer is best. A senior engineer is better. Solo-path learners: the mini-project explains how to self-run it with a recording — but try hard to find a partner; the pressure is the point.
- **Type the Python yourself.** Do not copy-paste exercise 2. Writing the EKF by hand is exactly the muscle the technical mock tests.
- Every Python exercise must run clean: `python3 exercise-02-ekf-predict-on-the-board.py` prints `ALL CHECKS PASSED`. If it doesn't, you're not done.
- **Grade yourself honestly.** A mock you inflated is worthless. The whole point is to find holes now, not in Week 47.

## Environment

These run in your standard C24 environment (Ubuntu 24.04, Python 3.12, NumPy). No ROS 2 node is needed for the Python drills — they're pure NumPy so you can run them anywhere, including on the train. Quick check:

```bash
python3 -c "import numpy; print('numpy', numpy.__version__)"
```

There are no solutions checked in. After you finish, search GitHub for `c24-week-45` to compare with other learners' forks.
