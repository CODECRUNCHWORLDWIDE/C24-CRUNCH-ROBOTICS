# Week 4 — Resources

Every resource on this page is **free**. The ROS2 documentation is free and open. The `ros2/`, `ros2/rclcpp`, `ros2/rclpy`, and `ros2/demos` repositories are Apache-2.0 and public on GitHub. The design articles at `design.ros2.org` are free. The Open Navigation (Nav2) docs and blog are free. No paywalled material is linked.

We target **ROS2 Jazzy Jalisco** on **Ubuntu 24.04** throughout. Where a doc page has per-distro variants, the links below point at the Jazzy version. If a link 404s after a distro EOL, swap `jazzy` for the current LTS in the URL.

## Required reading (work it into your week)

- **ROS2 Jazzy — "Understanding services"** (the canonical service tutorial):
  <https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Services/Understanding-ROS2-Services.html>
- **ROS2 Jazzy — "Understanding actions"**:
  <https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Actions/Understanding-ROS2-Actions.html>
- **ROS2 Jazzy — "Writing an action server and client (Python)"** (the `Fibonacci` walkthrough you adapt for Spin90):
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-an-Action-Server-Client/Py.html>
- **ROS2 Jazzy — "Creating an action"** (the `.action` file + `rosidl` build):
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Creating-an-Action.html>
- **ROS2 Jazzy — "Using callback groups"** (read this twice — it is the deadlock fix):
  <https://docs.ros.org/en/jazzy/How-To-Guides/Using-callback-groups.html>
- **ROS2 Jazzy — "About executors" (the concepts page)**:
  <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html>
- **ROS2 Jazzy — "Managed nodes" / lifecycle concept**:
  <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Node-Lifecycle.html>
- **ROS2 Jazzy — "Composing multiple nodes in a single process"**:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Composition.html>

## Authoritative design articles (the "why")

The `design.ros2.org` articles are how the ROS2 core team documented their decisions. They are the closest thing to a specification and explain *why* the APIs are shaped the way they are.

- **ROS2 design — "Actions"** — the protocol from first principles: goal IDs, the result cache, why feedback is separate from result, why an action is built on services + topics:
  <https://design.ros2.org/articles/actions.html>
- **ROS2 design — "Node lifecycle"** — the managed-node state machine, the transitions, the rationale for `inactive` vs `active`:
  <https://design.ros2.org/articles/node_lifecycle.html>
- **ROS2 design — "ROS QoS and DDS"** — read the executors-relevant parts now; the full QoS treatment is Week 5:
  <https://design.ros2.org/articles/qos.html>
- **ROS2 design — "Topics vs Services vs Actions"** — the original articulation of the decision ladder:
  <https://design.ros2.org/articles/ros_on_dds.html>

## Official API references

- **`rclpy` API — `ActionServer`**:
  <https://docs.ros.org/en/jazzy/p/rclpy/rclpy.action.server.html>
- **`rclpy` API — `ActionClient`**:
  <https://docs.ros.org/en/jazzy/p/rclpy/rclpy.action.client.html>
- **`rclpy` API — executors (`SingleThreadedExecutor`, `MultiThreadedExecutor`)**:
  <https://docs.ros.org/en/jazzy/p/rclpy/rclpy.executors.html>
- **`rclpy` API — callback groups**:
  <https://docs.ros.org/en/jazzy/p/rclpy/rclpy.callback_groups.html>
- **`rclpy` API — lifecycle (`rclpy.lifecycle.LifecycleNode`)**:
  <https://docs.ros.org/en/jazzy/p/rclpy/rclpy.lifecycle.html>
- **`rclcpp` API — `rclcpp_action`**:
  <https://docs.ros.org/en/jazzy/p/rclcpp_action/>
- **`rclcpp` API — `rclcpp_lifecycle`**:
  <https://docs.ros.org/en/jazzy/p/rclcpp_lifecycle/>
- **`rclcpp` API — `rclcpp_components`** (composition):
  <https://docs.ros.org/en/jazzy/p/rclcpp_components/>
- **`lifecycle_msgs` interface reference** (the `Transition` and `State` enums):
  <https://docs.ros2.org/latest/api/lifecycle_msgs/index-msg.html>

## CLI reference (you live here this week)

- **`ros2 action` verbs** — `list`, `info`, `send_goal` (with `--feedback`):
  <https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Actions/Understanding-ROS2-Actions.html>
- **`ros2 lifecycle` verbs** — `list`, `get`, `set` (the manual transition driver):
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Composition.html>
- **`ros2 service` verbs** — `list`, `type`, `call`:
  <https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Services/Understanding-ROS2-Services.html>

## Source repos worth skimming

- **`ros2/demos`** — the reference action, lifecycle, and composition demos. Read `action_tutorials/` (Fibonacci), `lifecycle/` (the talker/listener managed-node demo), and `composition/`:
  <https://github.com/ros2/demos>
- **`ros2/examples`** — the minimal `rclpy` and `rclcpp` examples, including action servers/clients and callback-group usage:
  <https://github.com/ros2/examples>
- **`ros2/rclpy`** — the Python client library. The `rclpy/action/server.py` file is the action server implementation; read it once to see how the goal handle, the executor, and the callback groups interact:
  <https://github.com/ros2/rclpy>
- **`ros2/rclcpp`** — the C++ client library. `rclcpp/src/rclcpp/executors/multi_threaded_executor.cpp` is the multi-threaded executor; trace `spin()` to see how it dispatches ready callbacks across threads:
  <https://github.com/ros2/rclcpp>
- **`ros-navigation/navigation2` (Nav2)** — the canonical large lifecycle-node codebase. Look at `nav2_lifecycle_manager/` to see how a supervisor brings dozens of lifecycle nodes to `active` in order:
  <https://github.com/ros-navigation/navigation2>

## Talks worth watching (all free, no account)

- **ROSCon — "Demystifying ROS2 executors"** — the canonical talk on what spin actually does and why callback groups exist. Search "ROSCon executors" on the official ROSCon YouTube channel (`roscon.ros.org` lists every talk with slides + video).
- **ROSCon — "Lifecycle nodes and managed startup"** — search the ROSCon talk index for the Nav2 lifecycle-manager session; it walks the supervisor pattern end-to-end.
- **ROSCon — "Composition and intra-process communication"** — the talk that explains the zero-copy benefit and when composition is worth it. On the ROSCon talk index.
- **Open Navigation (Steve Macenski) — Nav2 architecture talks** — Macenski maintains Nav2; his talks on the lifecycle-manager pattern are the production reference. On the ROSCon index and the Open Navigation YouTube.

## Books and long-form

- **"A Concise Introduction to Robot Programming with ROS2"** (Fairchild & Harman / and the newer Jazzy editions) — the actions and lifecycle chapters are the most accessible book-length treatment. Library or O'Reilly; not required.
- **The Nav2 documentation site** — `navigation.ros.org` — the "Concepts" and "Lifecycle" pages are the best free explanation of *why* a production stack is built from managed nodes:
  <https://navigation.ros.org/concepts/index.html>

## How to use this resource list

The lectures cite specific URLs from this page at decision points. The links you should read end-to-end **this week** are:

1. **ROS2 design — "Actions"** (design articles section). Foundational; do not skip. It is the difference between using actions and understanding them.
2. **ROS2 Jazzy — "Using callback groups"** (required reading). This is the deadlock fix; read it twice.
3. **ROS2 design — "Node lifecycle"** (design articles section). The rationale for the managed-node state machine; decisive for the challenge.
4. **ROS2 Jazzy — "Writing an action server and client (Python)"** (required reading). You adapt this Fibonacci walkthrough into Spin90 in Exercise 2.

The rest are reference material — bookmark them and return when a specific question arises. Even senior ROS2 engineers re-read the executors and callback-groups pages when they touch concurrent node code; the model is genuinely subtle.

---

*Bookmarks decay. If a ROS2 doc link rots after a distro reaches end-of-life, replace `jazzy` in the URL path with the current LTS codename — the page structure has been stable across distros.*
