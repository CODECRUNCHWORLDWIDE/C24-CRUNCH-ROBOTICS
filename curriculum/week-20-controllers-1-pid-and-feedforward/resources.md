# Week 20 — Resources

Every resource here is **free** or has a free, legal full-text version. The controls classics we lean on (Åström & Murray's *Feedback Systems*, Åström & Hägglund on PID) are published as free PDFs by their authors. The `ros2_control` docs are open and pinned to **Jazzy** wherever they're versioned. No paywalled books are linked; where a famous text is the canonical reference, we point at the free author-hosted PDF, not a bookstore.

When a link is versioned, the Jazzy URL is given. If you are on a newer distro later, swap `jazzy` for your distro name — the controls concepts are distro-independent; only the `ros2_control` API URLs move.

## Required reading (work it into your week)

- **Åström & Murray, *Feedback Systems* (2nd ed.) — Chapter 11, "PID Control."** The single best free treatment of PID, anti-windup, and the two-degree-of-freedom structure. Read §11.1–11.5 Monday, §11.6 (implementation) Thursday:
  <https://fbswiki.org/wiki/index.php/Main_Page> (full PDF linked from the front page)
- **`ros2_control` concepts — the framework overview.** The `controller_manager`, hardware interfaces, command/state interfaces. Read it before you touch the mini-project:
  <https://control.ros.org/jazzy/doc/getting_started/getting_started.html>
- **`ros2_control` — writing a new controller.** The exact plugin lifecycle (`on_init`, `on_configure`, `on_activate`, `update`) you implement in the mini-project:
  <https://control.ros.org/jazzy/doc/ros2_controllers/doc/writing_new_controller.html>
- **`control_toolbox::Pid`** — the production PID the ROS controls stack actually ships, including its anti-windup. Read the header and the implementation; your Exercise 2 fix should match what it does:
  <https://github.com/ros-controls/control_toolbox>

## The controls classics (skim the relevant chapters, don't read cover to cover)

- **Åström & Hägglund, *Advanced PID Control* / *PID Controllers: Theory, Design, and Tuning*.** The definitive PID reference. The anti-windup and derivative-filtering chapters are the canonical treatment; the Åström lecture notes hosted at Lund cover the same ground freely:
  <https://www.control.lth.se/education/doctorate-program/> (Åström's PID and control lecture notes)
- **Brian Douglas — "Control System Lectures" (YouTube).** The best free intuition-building videos in controls. The PID, integral wind-up, and "control systems in practice" playlists are required watching if the math feels abstract:
  <https://www.youtube.com/@ControlSystemLectures>
- **Steve Brunton — Control Bootcamp (YouTube/Univ. of Washington).** Goes from PID into state-space and LQR — a perfect bridge into Week 21. Watch the first few lectures this week, the LQR ones next week:
  <https://www.youtube.com/playlist?list=PLMrJAkhIeNNR20Mz-VpzgfQs5zrYi085m>

## `ros2_control` deep dive (you'll have these open all week)

- **`ros2_control` demos repository** — runnable examples of controllers, hardware interfaces, and the diff-drive bot. The `example_*` packages are the templates you'll copy from:
  <https://github.com/ros-controls/ros2_control_demos>
- **`diff_drive_controller`** — the stock differential-drive controller. Read how it consumes `/cmd_vel` and commands the wheel velocity interfaces:
  <https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html>
- **`pid_controller`** — the stock chainable PID controller in `ros2_controllers`. Compare its config surface to your hand-rolled plugin:
  <https://control.ros.org/jazzy/doc/ros2_controllers/pid_controller/doc/userdoc.html>
- **`gz_ros2_control`** — the bridge that lets your `ros2_control` controllers drive the Gz Sim robot. This is how the mini-project plugin actually moves wheels in simulation:
  <https://github.com/ros-controls/gz_ros2_control>

## Tuning references (the practical ones)

- **Ziegler–Nichols tuning rules** — the original 1942 heuristics, both the ultimate-gain and the reaction-curve methods, summarized honestly with their caveats:
  <https://en.wikipedia.org/wiki/Ziegler%E2%80%93Nichols_method>
- **`scipy.optimize.minimize`** — the optimizer you'll use to auto-tune gains against an ITAE cost in the stretch work and the mini-project:
  <https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html>
- **`scipy.signal`** — `lti`, `lsim`, `step` for simulating the plants in Exercise 1 without writing your own integrator:
  <https://docs.scipy.org/doc/scipy/reference/signal.html>

## API references (the ones you'll have open all week)

- **`numpy`** — arrays, `clip` (you'll use it for saturation), `trapz`:
  <https://numpy.org/doc/stable/reference/>
- **`matplotlib.pyplot`** — every step-response plot this week:
  <https://matplotlib.org/stable/api/pyplot_summary.html>
- **`rclpy` timers and clock** — the fixed-rate control loop runs on a `create_timer`; the `dt` discipline depends on the clock:
  <https://docs.ros.org/en/jazzy/p/rclpy/>
- **`tf_transformations` / `transforms3d`** — to pull a yaw out of the IMU quaternion in Exercise 3:
  <https://github.com/DLu/tf_transformations>

## Read the source of code that gets control right

- **`control_toolbox`** — `Pid`, `PidROS`, the filters. The reference implementation of everything in Lecture 1:
  <https://github.com/ros-controls/control_toolbox>
- **Nav2 `RegulatedPurePursuitController`** — a real path-tracking controller with feedforward-style velocity scaling and constraint handling. Read it to see PID-class ideas in a shipped navigation controller:
  <https://docs.nav2.org/configuration/packages/configuring-regulated-pp.html>
- **PX4 / ArduPilot rate controllers** — the most-deployed PID loops on Earth (every multirotor). The PX4 multicopter rate controller is a clean, real, anti-windup-correct cascaded PID:
  <https://docs.px4.io/main/en/flight_stack/controller_diagrams.html>

## Talks worth your time (free, no signup)

- **"Control systems in practice" — Brian Douglas / MathWorks.** Short, dense, and exactly the gap between the equation and the deployed loop:
  <https://www.youtube.com/@ControlSystemLectures>
- **ROSCon `ros2_control` deep-dives** — the OSRF posts every talk free; the `ros2_control` architecture sessions are the ones to watch before the mini-project:
  <https://roscon.ros.org/> and <https://vimeo.com/osrfoundation>

## Tools you'll use this week

- **`matplotlib`** — `pip install matplotlib` (or `sudo apt install python3-matplotlib`). Every step-response plot.
- **`scipy`** — `sudo apt install python3-scipy`. `signal` for plants, `optimize` for auto-tuning.
- **PlotJuggler** — `sudo apt install ros-jazzy-plotjuggler-ros`. Live-plot the IMU yaw, the setpoint, and the command during Exercise 3. The single best tool for watching a control loop in real time.
- **`ros2 control` CLI** — `list_controllers`, `load_controller`, `set_controller_state`. How you load and activate your plugin against the controller manager.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Setpoint / reference** `r(t)` | What you want the output to be. |
| **Process variable / output** `y(t)` | What the output actually is (the measurement). |
| **Error** `e(t) = r − y` | The gap the controller works to close. |
| **`Kp` (proportional)** | Push proportional to current error. Faster response, but alone leaves steady-state offset and can oscillate. |
| **`Ki` (integral)** | Push proportional to *accumulated* error. Kills steady-state offset; the term that causes wind-up. |
| **`Kd` (derivative)** | Push proportional to the *rate of change* of error. Adds damping; amplifies noise; causes kick on setpoint steps. |
| **Integrator wind-up** | The integral keeps accumulating while the actuator is saturated, then must unwind — causing huge overshoot. |
| **Derivative kick** | A step in the setpoint differentiates to an impulse, spiking the command. Fixed by differentiating the measurement. |
| **Feedforward** | A command computed from the *reference* (not the error), doing the predictable work before feedback engages. |
| **Regulation** | Holding a fixed setpoint against disturbances. |
| **Tracking** | Following a time-varying reference. |
| **Rise time** | Time to go from 10% to 90% of the final value. |
| **Overshoot** | How far the response exceeds the setpoint, as a percentage. |
| **Settling time** | Time to stay within a band (usually ±2%) of the final value. |
| **Steady-state error** | The residual error after the transient dies. |
| **Damping ratio** `ζ` | Second-order shape parameter: ζ<1 underdamped (overshoots), ζ=1 critically damped, ζ>1 overdamped (sluggish). |
| **`command_interface`** | A `ros2_control` handle the controller *writes* (e.g., a wheel velocity command). |
| **`state_interface`** | A `ros2_control` handle the controller *reads* (e.g., a wheel position/velocity measurement). |
| **`controller_manager`** | The `ros2_control` process that loads controllers, owns the real-time loop, and arbitrates interface access. |

---

*If a link 404s, please open an issue so we can replace it.*
