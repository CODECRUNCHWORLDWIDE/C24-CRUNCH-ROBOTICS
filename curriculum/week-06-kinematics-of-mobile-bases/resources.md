# Week 6 — Resources

Almost everything on this page is **free**. The ROS2 documentation, the REP specs, the `ros-controls` and `nav2` docs, the PlotJuggler docs, and the Borenstein/Feng UMBmark paper are all freely available. Two textbooks (Siegwart and *Modern Robotics*) are paid in print, but *Modern Robotics* is fully free as a PDF from the authors and Siegwart has free lecture slides that mirror the relevant chapter. No paywalled link is required to complete the week.

## Required reading (work it into your week)

- **REP-103 — Standard Units of Measure and Coordinate Conventions** — the document that defines right-handed axes, the `x`-forward / `z`-up body frame, and radians/metres. Read this before you write a single line of the odometry node; getting the frame convention wrong is the most common Week 6 bug:
  <https://www.ros.org/reps/rep-0103.html>
- **REP-105 — Coordinate Frames for Mobile Platforms** — defines `map`, `odom`, and `base_link`, and the rule that `odom → base_link` must be continuous and is published by *your* odometry source while `map → odom` is published by the localizer. This is the contract your node fulfills:
  <https://www.ros.org/reps/rep-0105.html>
- **`nav_msgs/Odometry` message definition** — the exact fields you populate: `header`, `child_frame_id`, `pose` (with covariance), `twist` (with covariance):
  <https://docs.ros.org/en/jazzy/p/nav_msgs/interfaces/msg/Odometry.html>
- **ros2_control `diff_drive_controller` documentation** — the production reference implementation of exactly what you build by hand this week. Read it to see how a shipped controller handles wheel-speed limits, odometry publishing, and open-loop fallback:
  <https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html>
- **`tf2` Python broadcaster tutorial (Jazzy)** — how to construct and send a `TransformStamped`, the part of the odometry node that publishes `odom → base_link`:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Broadcaster-Py.html>
- **PlotJuggler — getting started** — the visualization tool of the week. Learn to drag a topic onto a plot, split the view, and load/save a layout `.xml`:
  <https://plotjuggler.io/>

## The kinematics canon

- **Siegwart, Nourbakhsh & Scaramuzza — *Introduction to Autonomous Mobile Robots* (2nd ed.), Chapter 3 "Mobile Robot Kinematics."** The standard mobile-robotics textbook treatment of wheel constraints, the diff-drive/bicycle/omnidirectional models, holonomy, and the kinematic constraint matrices. The course slides for the ETH "Autonomous Mobile Robots" MOOC reproduce the figures for free:
  <https://asl.ethz.ch/education/lectures/autonomous_mobile_robots.html>
- **Lynch & Park — *Modern Robotics: Mechanics, Planning, and Control* — Chapter 13 "Wheeled Mobile Robots."** Free, complete PDF from the authors. The cleanest modern treatment of the unicycle/diff-drive/omnidirectional kinematics in twist (`SE(2)`) language, which is exactly the language we use to integrate pose:
  <https://hades.mech.northwestern.edu/index.php/Modern_Robotics>
- **Thrun, Burgard & Fox — *Probabilistic Robotics*, Chapter 5 "Robot Motion."** The probabilistic motion model — odometry-based and velocity-based — and the noise model that becomes the covariance you put on `/odom`. This is the bridge from "odometry drifts" to "the EKF weights it by covariance":
  <https://probabilistic-robotics.org/>
- **Corke — *Robotics, Vision and Control* (3rd ed.), Chapter 4 "Mobile Robot Vehicles."** A MATLAB/Python-flavored treatment with runnable code; the bicycle and unicycle integrations here map almost line-for-line onto the `rclpy` node you write:
  <https://petercorke.com/rvc/home/>

## Odometry drift — the primary sources

- **Borenstein & Feng — "Measurement and Correction of Systematic Odometry Errors in Mobile Robots" (IEEE T-RO, 1996) — the UMBmark paper.** The canonical method for separating systematic from non-systematic odometry error using a bidirectional (CW + CCW) square test, and the two correction factors (`Ed` for wheel-diameter ratio, `Eb` for effective wheelbase). The square you drive this week is a direct descendant of this benchmark:
  <https://www-personal.umich.edu/~johannb/Papers/paper58.pdf>
- **Borenstein, Everett & Feng — "Where am I? Sensors and Methods for Mobile Robot Positioning" (1996 survey).** The free 282-page survey that catalogs every dead-reckoning and reference-based positioning method of the era; Chapters 1–2 on odometry and its error sources are still the best single reference on *why* wheels lie:
  <https://www-personal.umich.edu/~johannb/Papers/pos96rep.pdf>
- **Olson — "A Primer on Odometry and Motor Control" (MIT 6.186 notes).** A short, practical primer that ties encoder counts → wheel velocity → body twist → pose, with the quantization analysis we use in Lecture 1:
  <https://ocw.mit.edu/courses/6-186-mobile-autonomous-systems-laboratory-january-iap-2005/>

## Official ROS2 docs (Jazzy)

- **`ros2_control` concepts** — controllers, hardware interfaces, the controller manager. Background for why `diff_drive_controller` is structured the way it is:
  <https://control.ros.org/jazzy/doc/getting_started/getting_started.html>
- **`sensor_msgs/JointState` message** — the input to your node: `name[]`, `position[]`, `velocity[]`, `effort[]`. Note that `velocity` may be empty and you must fall back to differencing `position`:
  <https://docs.ros.org/en/jazzy/p/sensor_msgs/interfaces/msg/JointState.html>
- **`geometry_msgs/TransformStamped`** — the TF message you broadcast:
  <https://docs.ros.org/en/jazzy/p/geometry_msgs/interfaces/msg/TransformStamped.html>
- **Gz Sim `odometry_publisher` and `diff_drive` system plugins** — the simulator-side ground-truth and diff-drive plugins; the `OdometryPublisher` gives you the ground-truth pose to compare your node against:
  <https://gazebosim.org/api/sim/8/classgz_1_1sim_1_1systems_1_1OdometryPublisher.html>
- **`ros_gz_bridge`** — bridging Gz topics (ground-truth pose, joint states) into ROS2:
  <https://github.com/gazebosim/ros_gz/tree/jazzy/ros_gz_bridge>
- **Nav2 — why it plans in unicycle space** — the controller plugin docs show the `geometry_msgs/Twist` interface every base reduces to:
  <https://docs.nav2.org/>

## Tools

- **PlotJuggler — documentation and ROS2 plugin** — keyboard shortcuts, the ROS2 topic streamer, the time-series transforms, and layout save/load:
  <https://github.com/facontidavide/PlotJuggler>
- **`ackermann_msgs`** — the `AckermannDrive` and `AckermannDriveStamped` messages referenced in Lecture 2's car-like section:
  <https://github.com/ros-drivers/ackermann_msgs>
- **`tf2_tools` and `view_frames`** — generate a PDF of your TF tree to confirm `odom → base_link` is present and singly-parented:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Debugging-Tf2-Problems.html>
- **`evo` — trajectory evaluation toolkit** — `evo_traj` and `evo_ape` compute absolute pose error between your odometry and ground-truth trajectories; an optional, more rigorous alternative to the closure-error metric for the homework:
  <https://github.com/MichaelGrupp/evo>

## Talks worth watching (all free, no account)

- **"Mobile Robot Kinematics" — ETH Autonomous Mobile Robots MOOC (Siegwart, Scaramuzza), Lecture 3.** The video lectures that accompany the textbook chapter; the ICR and constraint-matrix derivations are worth the hour. Search YouTube for "ETH Autonomous Mobile Robots kinematics."
- **"Modern Robotics, Chapter 13: Wheeled Mobile Robots" — Northwestern (Kevin Lynch).** The author's own video walk-through of the omnidirectional and diff-drive kinematics in twist language. Search YouTube for "Modern Robotics wheeled mobile robots Lynch."
- **"ros2_control in 5 minutes" and the longer ROSCon `ros2_control` deep-dives.** Background for the production controller you are reimplementing by hand. Search YouTube for "ROSCon ros2_control."
- **"PlotJuggler — the time-series visualization tool" (Davide Faconti, ROSCon lightning talk).** The author demoing the layout and transform features you will use Thursday. Search YouTube for "PlotJuggler ROSCon."

## How to use this resource list

The lectures cite specific URLs from this page at decision points. When Lecture 1 says "see the UMBmark paper for the CW/CCW correction," the URL is above. You do not need to read every link this week. The links to read end-to-end are:

1. **REP-103 and REP-105** (Required reading). Non-negotiable. Half of all Week 6 bugs are frame-convention bugs the REPs would have prevented.
2. **The `nav_msgs/Odometry` message definition and the tf2 broadcaster tutorial.** You will reference both while writing the node.
3. **The UMBmark paper, Sections III–IV.** ~30 minutes; it is the basis of the challenge and the calibration step in the mini-project.
4. **Modern Robotics, Chapter 13.2–13.3.** ~45 minutes; the cleanest derivation of the diff-drive and omnidirectional kinematics in the twist language we integrate with.

The rest are reference material — bookmark them and return when a specific question arises.

---

*Bookmarks decay. If a link rots, search the title — the REPs, the UMBmark paper, and the textbook chapters are canonical and reappear on the authors' and ROS's new homes.*
