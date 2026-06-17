# Week 20 — Controllers Part 1: PID and Feedforward

Welcome to the part of the track where the robot stops *knowing* things and starts *doing* them. For nineteen weeks you have built perception, estimation, and planning — you know where the robot is, what's around it, and where it should go. None of that moves a wheel. The controller is the thing that closes the gap between "the plan says be at 90°" and "the IMU says I'm at 71° and drifting." This week you build the oldest, most-deployed, most-underestimated controller in all of engineering: **PID**. And then you make it good, which is mostly about the parts nobody teaches — anti-windup, derivative filtering, and feedforward.

By Friday you will be able to write a PID controller from a blank file, tune it by feel against a step response, read a rise-time/overshoot/settling plot the way you read a stack trace, add a feedforward term that does most of the work so the feedback only has to clean up the residue, and ship the whole thing as a real `ros2_control` controller plugin instead of a one-off node. You will also be able to say *why* — why the integrator is the most dangerous term, why derivative kick will spike your actuators the first time someone steps the setpoint, and why the difference between regulation and tracking decides your entire architecture.

We assume you finished Week 19 and have a behavior tree that dispatches navigation goals, and that your **week-3 differential-drive robot** still spawns in Gz Sim and publishes `/scan`, `/imu/data`, `/odom`, and accepts `/cmd_vel`. Every exercise this week runs against that robot. If it doesn't spawn, fix that first.

The one thing to internalize before you read another line: **PID is not obsolete, and it is not a toy. It is the floor under every controller you will ever build, including the LQR you write next week and the MPC you write the week after.** An MPC with a broken low-level velocity loop is a broken MPC. The textbook three-term controller is forty years old, ships in every drone, every CNC machine, every thermostat, and most of the warehouse robots you'll interview at — and the reason it has a bad reputation is that most people deploy the naive version (the one in the Wikipedia equation) and never add the three fixes that make it production-grade. This week is those three fixes.

## Learning objectives

By the end of this week, you will be able to:

- **Derive** the PID control law from the definition of error, and state precisely what each of the three terms (P, I, D) buys you and what it costs you.
- **Distinguish** regulation (hold a fixed setpoint against disturbance) from tracking (follow a moving reference), and explain why that distinction changes your gains, your feedforward, and your success metric.
- **Implement** a discrete-time PID controller correctly: fixed-rate or `dt`-aware integration, a band-limited derivative, and a clean reset — with none of the off-by-`dt` bugs that plague first attempts.
- **Diagnose and fix integrator wind-up** with at least two methods (conditional integration / clamping, and back-calculation), and explain why a saturated actuator turns a naive integrator into a slow-motion catastrophe.
- **Eliminate derivative kick** by differentiating the measurement instead of the error, and explain why a step in the setpoint should never produce an impulse in the command.
- **Add a feedforward term** — static, velocity, and acceleration feedforward — and quantify how much tracking error it removes before the feedback loop ever engages.
- **Tune** a PID controller three ways: manual (the structured loop, not random poking), Ziegler–Nichols (and why you'll rarely ship its aggressive gains), and a small optimization-based auto-tune over a simulated step response.
- **Analyze** a step response: read rise time, percent overshoot, settling time, and steady-state error off a plot, and connect each number back to a specific gain.
- **Ship** a PID controller as a `ros2_control` controller plugin — understanding the `command_interface` / `state_interface` model, the update loop, and why the controller manager exists — instead of an ad-hoc node that fights the rest of the stack.

## Prerequisites

This week assumes you have completed **C24 weeks 1–19**, or have equivalent ROS2 and controls fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04** (or the same in a container / WSL2). `ros2 --version` works.
- You can write a `rclpy` publisher, subscriber, and timer from memory, and you understand the executor model from Week 4.
- You have the **week-3 robot** (the diff-drive xacro with a 2D LiDAR and IMU) and it spawns in Gz Sim, accepts `/cmd_vel`, and publishes `/imu/data` with a usable yaw.
- You are fluent in `numpy` and can read a `matplotlib` plot. We use `scipy.signal` for one discrete-time demonstration but introduce it inline.
- You remember enough calculus to read `∫e dt` and `de/dt` without flinching. We do not re-teach calculus; we do connect every symbol to a line of code.

You do **not** need prior controls coursework. We start at "what is error" and build to a shipped `ros2_control` plugin. If you've used PID only by copying gains from a tutorial without knowing what the I term does when the motor saturates, this is the week that knowledge becomes load-bearing — and the week your robot stops overshooting.

## Topics covered

- **PID anatomy.** The error signal `e(t) = r(t) − y(t)`; the proportional term `Kp·e`; the integral term `Ki·∫e dt`; the derivative term `Kd·de/dt`. What each term *physically* does to the response, and the order in which you add them.
- **Continuous vs. discrete PID.** The textbook continuous law and the discrete implementation you actually ship: rectangular vs. trapezoidal integration, the backward-difference derivative, and why `dt` correctness is the most common silent bug.
- **The two killers — and their fixes.** *Integrator wind-up* (the integral accumulates while the actuator is saturated, then has to unwind, causing massive overshoot) fixed by conditional integration and by back-calculation. *Derivative kick* (a setpoint step differentiates to an impulse) fixed by differentiating the measurement, not the error. Plus *derivative noise amplification* and the first-order filter that tames it.
- **Feedforward.** Static (gravity / friction compensation), velocity feedforward (`Kv·v_ref`), and acceleration feedforward (`Ka·a_ref`). The two-degree-of-freedom controller: feedforward does the predictable work, feedback cleans up the unpredictable residue. Why a good feedforward term removes most of the tracking error *before* the feedback loop sees it.
- **Regulation vs. tracking.** Holding a yaw setpoint against a disturbance (regulation) vs. following a time-varying yaw-rate reference (tracking). Why tracking *needs* feedforward and regulation often doesn't, and why your error metric differs (steady-state error vs. tracking error / phase lag).
- **Tuning, three ways.** The structured manual loop (P until it oscillates, back off, add D for damping, add minimal I for the offset). Ziegler–Nichols (ultimate-gain and step-response methods) and an honest account of why its gains are usually too hot to ship. Optimization-based auto-tuning: define a cost over the step response (ISE / ITAE) and minimize it with `scipy.optimize`.
- **Step-response analysis.** Rise time, peak time, percent overshoot, settling time (2% band), steady-state error. Reading each off a plot and mapping it to the gain that controls it. The second-order-system intuition (damping ratio ζ, natural frequency ωn) that lets you *predict* the shape before you run it.
- **`ros2_control`.** The hardware-abstraction model: `command_interface` and `state_interface`, the `controller_manager`, the real-time update loop, and why you write a controller as a plugin loaded by the manager rather than a node publishing `/cmd_vel`. The stock `pid_controller` and `diff_drive_controller`, and when to write your own.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | PID anatomy; discrete implementation; the two killers |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Anti-windup + derivative kick exercises; step response |   1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | Feedforward; regulation vs tracking; tuning methods   |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | `ros2_control` model; the yaw-rate PID on the robot   |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Auto-tuning; the feedforward win; plugin packaging    |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                               |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, tuning-log polish                      |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                      | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | The controls texts, the PID-anti-windup papers, the `ros2_control` docs, and the talks worth your time |
| [lecture-notes/01-pid-anatomy-windup-and-derivative-kick.md](./02-lecture-notes/01-pid-anatomy-windup-and-derivative-kick.md) | The three terms, the discrete implementation, and the two killers with their fixes |
| [lecture-notes/02-feedforward-tuning-and-ros2-control.md](./02-lecture-notes/02-feedforward-tuning-and-ros2-control.md) | Feedforward, regulation vs tracking, the three tuning methods, and shipping it as a `ros2_control` plugin |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-step-response-and-tuning.md](./03-exercises/exercise-01-step-response-and-tuning.md) | Tune a PID for a second-order plant; read rise time, overshoot, settling off the plot |
| [exercises/exercise-02-antiwindup-and-derivative-kick.py](./03-exercises/exercise-02-antiwindup-and-derivative-kick.py) | Reproduce wind-up and derivative kick, then fix both; the simulation proves it |
| [exercises/exercise-03-yaw-rate-pid.py](./03-exercises/exercise-03-yaw-rate-pid.py) | A closed-loop yaw-rate PID on the diff-drive robot, with feedforward, consuming IMU and emitting `/cmd_vel` |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-tune-three-step-responses.md](./04-challenges/challenge-01-tune-three-step-responses.md) | Tune one controller to hit three different step targets (45°, 90°, 180°) inside a spec, and defend the gains |
| [quiz.md](./05-quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./06-homework.md) | Six problems including the headline tuning-log deliverable |
| [mini-project/README.md](./07-mini-project/00-overview.md) | The reusable `crunchbot_control` PID + feedforward `ros2_control` plugin with a tuning harness |

## The "step response is in spec" promise

C24 uses a recurring marker for every controls exercise that ends in a response that actually meets a specification:

```
$ python3 analyze_step.py --log yaw_step_90.csv
Rise time (10–90%):   0.41 s
Peak time:            0.62 s
Percent overshoot:    8.2 %   (spec: <= 10 %)   PASS
Settling time (2%):   1.05 s   (spec: <= 1.5 s)  PASS
Steady-state error:   0.3 deg  (spec: <= 1 deg)  PASS
```

If overshoot is 40% when the spec says 10%, or the response never settles, you are not done. A controller that "moves the robot roughly toward the goal" is not a controller — it is a suggestion. The point of Week 20 is to make those four numbers ordinary, and to make a *failing* number a thing you can fix by naming the specific gain responsible.

## A word on the math, and on honesty

Controls is the first genuinely mathematical week of Phase 3, and it is where a lot of self-taught engineers have a quiet gap. We close it without apology and without showing off. Every equation in the lecture notes is connected to a line of runnable Python. When we write `Ki·∫e dt`, the very next code block shows `integral += error * dt` and the bug that's waiting if you forget the `dt`. You do not need to have taken a controls course. You do need to be willing to run the code, perturb a gain, and watch the plot change — because that loop, run fifty times this week, is how controls intuition is actually built. Nobody develops it from the Laplace transform alone.

## Stretch goals

If you finish the regular work early and want to push further:

- Implement the controller in the **velocity form** (incremental PID) instead of the positional form, and explain why incremental PID gives you bumpless transfer and anti-windup almost for free. Compare the two on the same step.
- Add a **gain-scheduled** PID: different gains for small errors vs. large errors, switched smoothly. This is the bridge to next week's LQR gain scheduling.
- Replace your hand-tuned gains with the output of a **`scipy.optimize.minimize`** run over an ITAE cost, and compare the auto-tuned response to your hand-tuned one. Where does the optimizer beat you? Where does it produce gains you'd never ship?
- Read the **`ros2_control` `pid_controller` source** and the `control_toolbox::Pid` class it wraps. Find where they implement anti-windup and confirm it matches the back-calculation you implemented in Exercise 2: <https://github.com/ros-controls/control_toolbox>.

## Up next

Week 21 takes the PID intuition you built here and asks the question PID can't answer cleanly: *what if you have more than one state to control at once, and you want the **optimal** trade-off between effort and error?* That's **LQR** — PID with adult supervision, solved from a model and a cost function instead of tuned by feel. The feedforward habit you build this week carries straight over. Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
