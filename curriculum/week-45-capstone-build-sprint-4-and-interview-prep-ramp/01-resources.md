# Week 45 — Resources

Interview prep is the one area where the internet is *full* of garbage — generic "top 50 robotics interview questions" listicles that teach you nothing. The links below are the ones that are actually current to 2026 and actually written by people who have sat on both sides of a robotics-startup table. Everything here is free unless flagged. If a link rots, open an issue.

## Required reading (work it into your week)

- **The system-design interview, robotics edition** — your own `interview-prep/` folder in this repo. The twelve worked problems (warehouse AMR, last-mile delivery, surgical assist, autonomous forklift, drone inspection) with rubrics. Start here; this is the source of truth for the format we grade against.
- **Probabilistic Robotics** (Thrun, Burgard, Fox) — Chapter 3 (Gaussian filters) and Chapter 7 (mobile-robot localization). The EKF predict/update derivation you will write on the board. The PDF is widely available for personal study; the print edition is the canonical reference.
- **Modern Robotics: Mechanics, Planning, and Control** (Lynch & Park) — Chapters 3–5 (rigid-body motions, forward kinematics, velocity kinematics and the Jacobian). Free PDF and the full Coursera/edX lecture set at <http://hades.mech.northwestern.edu/index.php/Modern_Robotics>. This is the kinematics half of your technical mock.
- **Your own capstone README and safety case** — re-read them as if you were the interviewer. Every claim is a follow-up question waiting to happen.

## System design

- **"Designing the autonomy stack" engineering blogs** — read at least two of these before the system-design mock; they *are* the interview answer written down:
  - **Waymo's "Under the Hood" series** and the Waymo Research blog: <https://waymo.com/research/> — sensor fusion, behavior prediction, the safety case at scale.
  - **Zoox engineering blog**: <https://zoox.com/journal/> — full-stack AV design decisions, written by engineers.
  - **Skydio engineering**: <https://www.skydio.com/blog> — onboard autonomy under a tight compute and latency budget; the drone version of your AMR problem.
  - **Locus Robotics / Symbotic / Fetch (Zebra) warehouse-AMR material** — search their engineering posts; the warehouse-AMR design prompt comes straight from this domain.
- **"System Design Interview" methodology (Alex Xu)** — not robotics-specific, but the *method* (clarify, estimate, draw, defend) transfers directly. Skim the first three chapters for the structure; ignore the web-scale specifics.
- **ROS 2 design articles** — <https://design.ros2.org/> — DDS, QoS, executors, lifecycle. When the interviewer asks "how do nodes talk and what happens under packet loss?", this is the answer.

## State estimation and the EKF

- **Kalman and Bayesian Filters in Python** (Roger Labbe) — the best free, runnable EKF tutorial in existence: <https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python>. Notebooks for KF, EKF, UKF, particle filter. Work the EKF notebook before Thursday's mock.
- **GTSAM documentation and the factor-graph tutorial** — <https://gtsam.org/tutorials/intro.html>. When the interviewer asks "why EKF and not a factor graph?", you need to be able to articulate the marginalization-vs-smoothing trade-off. This is the canonical reference.
- **`robot_localization` package docs** (`ekf_node` / `ukf_node`) — <https://docs.ros.org/en/jazzy/p/robot_localization/> — the production EKF you almost certainly used in your own stack. Know its state vector, its `process_noise_covariance`, and how it handles multiple odometry sources.
- **State Estimation for Robotics** (Timothy Barfoot) — free PDF at <http://asrl.utias.utoronto.ca/~tdb/bib/barfoot_ser_17_compressed.pdf>. Chapter 4 (nonlinear estimation) is the rigorous version of what you will hand-wave at the whiteboard. Read it so your hand-waving is *correct*.

## Controls (for the technical mock)

- **Underactuated Robotics** (Russ Tedrake, MIT 6.832) — <https://underactuated.mit.edu/> — free, runnable, current. The LQR and trajectory-optimization chapters are the controls deep-dive. When asked "why MPC over LQR?", this is where the real answer lives.
- **Steve Brunton's Control Bootcamp** (YouTube) — <https://www.youtube.com/playlist?list=PLMrJAkhIeNNR20Mz-VpzgfQs5zrYi085m> — the clearest free explanation of controllability, LQR, and the Riccati equation. Watch the LQR episodes before Tuesday.
- **`ros2_control` and MPC framework docs** — your own controller from Weeks 18–24. Re-read your notes on why you tuned `Q` and `R` the way you did; "I copied the defaults" is a failing answer.

## Kinematics and manipulation

- **MoveIt 2 concepts** — <https://moveit.picknik.ai/main/doc/concepts/concepts.html> — kinematics solvers, planning scene, the Jacobian-based Cartesian path. The manipulation half of the technical mock assumes you know this from Weeks 25–28.
- **"A mathematical introduction to robotic manipulation"** (Murray, Li, Sastry) — free PDF at <https://www.cds.caltech.edu/~murray/mlswiki/> — the rigorous SE(3) / screw-theory reference if a follow-up goes deep on twists and wrenches.

## The résumé and behavioral conversation

- **"Cracking the Coding Interview"** (McDowell) — chapters on the behavioral interview and the project deep-dive. Robotics loops still include a clean coding round; this covers it. (Paid book; library copies abound.)
- **STAR method** — Situation, Task, Action, Result. The two-minute story structure for each of your five projects. Any reputable career-services write-up covers it; the structure matters more than the source.
- **levels.fyi robotics compensation data** — <https://www.levels.fyi/> — know the band before you negotiate. Not study material, but the reason you are doing all this.

## Tools you'll use this week

- **A whiteboard** — physical, a tablet with a stylus, or **Excalidraw** (<https://excalidraw.com/>, free, no signup). The box diagram is the deliverable; practice drawing it fast.
- **A timer** — your phone. Forty-five minutes for system design, forty-five for technical. The clock is part of the test.
- **A screen recorder** — OBS Studio (<https://obsproject.com/>, free) or your OS's built-in recorder, for solo-path learners and for the stretch goal of watching yourself back.
- **`numpy`** — for the EKF predict/update exercise. Already in your C24 environment.

## Open-source projects to read this week

You learn more about state estimation from reading one production EKF than from ten interview-prep blogs:

- **`cra-ros-pkg/robot_localization`** — <https://github.com/cra-ros-pkg/robot_localization> — the EKF/UKF you used. Read `ekf.cpp`'s `predict()` and `correct()` and map them onto the textbook equations.
- **`borglab/gtsam`** — <https://github.com/borglab/gtsam> — factor-graph smoothing. Read the `ImuFactor` and an `iSAM2` example to understand the EKF-vs-smoother contrast you will be asked about.
- **`ros-navigation/navigation2`** — <https://github.com/ros-navigation/navigation2> — the Nav2 behavior-tree navigator. Your warehouse-AMR design answer should map cleanly onto this; reading it makes your answer concrete.

## Glossary cheat sheet

Keep this open during both mocks.

| Term | Plain English |
|------|---------------|
| **System-design interview** | "Design X" with no right answer; graded on method, trade-offs, and how you handle "why". |
| **Technical / deep-dive** | Math + sensors + a coding question; graded on correctness and clarity. |
| **EKF** | Extended Kalman Filter — linearizes a nonlinear model around the current estimate via Jacobians, then runs the KF predict/update. |
| **`F` (state Jacobian)** | ∂(motion model)/∂(state); propagates covariance in the predict step. |
| **`H` (measurement Jacobian)** | ∂(measurement model)/∂(state); maps state covariance into measurement space in the update step. |
| **`Q` / `R`** | Process-noise / measurement-noise covariances. The two matrices you tune. |
| **Factor graph** | A graph of variables and constraints solved by nonlinear least squares (GTSAM); smooths over a window instead of marginalizing like an EKF. |
| **MPC** | Model Predictive Control — re-solves a finite-horizon optimal-control problem every cycle; handles constraints LQR cannot. |
| **LQR** | Linear-Quadratic Regulator — the closed-form optimal controller for a linear system with a quadratic cost. |
| **STAR** | Situation, Task, Action, Result — the two-minute structure for a project story. |
| **Three-layer "why"** | The interviewer asks "why" repeatedly; you must defend a decision to the third level before hitting "we'd measure that." |
| **Overclaiming** | Saying you did something you cannot defend. The single most common way to fail a robotics loop. |

---

*If a link 404s, please open an issue so we can replace it.*
