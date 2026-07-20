# Week 4 — Quiz

Thirteen questions on the decision ladder, services, actions, executors, callback groups, lifecycle, and composition. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 5. Answer key at the bottom — don't peek.

---

**Q1.** State the decision ladder in order, bottom rung to top.

- A) Service → topic → action → behavior tree
- B) Topic → service → action → behavior tree
- C) Topic → action → service → behavior tree
- D) Behavior tree → action → service → topic

---

**Q2.** Which single capability most clearly separates an action from a service?

- A) Actions can carry larger payloads.
- B) Actions are faster.
- C) Actions can be cancelled and stream feedback; services cannot.
- D) Services are deprecated in ROS2 Jazzy.

---

**Q3.** You are writing a "drive forward two metres" capability. The caller wants progress and must be able to stop it. Which rung?

- A) Topic — publish a distance and forget it.
- B) Service — request the distance, block until done.
- C) Action — long-running, cancellable, with feedback.
- D) Behavior tree — it's a single motion, so wrap it in a tree.

---

**Q4.** Inside a node callback, you need to call a service. Which form is correct, and why?

- A) `call(request)` — synchronous is simpler and always safe.
- B) `call_async(request)` and handle the `Future` — synchronous `call()` from a callback deadlocks the executor.
- C) Either works identically; the distinction is stylistic.
- D) Neither — you cannot call a service from inside a callback.

---

**Q5.** What are the three terminal statuses of a ROS2 action goal?

- A) `OK`, `ERROR`, `TIMEOUT`
- B) `SUCCEEDED`, `CANCELED`, `ABORTED`
- C) `DONE`, `STOPPED`, `FAILED`
- D) `ACCEPTED`, `REJECTED`, `EXECUTING`

---

**Q6.** Under the hood, a ROS2 action is implemented as:

- A) A fourth, dedicated DDS primitive separate from topics and services.
- B) A combination of services (goal, cancel, result) and topics (feedback, status).
- C) A single reliable topic with a special QoS.
- D) A shared-memory segment between client and server.

---

**Q7.** A `SingleThreadedExecutor` runs callbacks:

- A) Concurrently across all CPU cores.
- B) One at a time, on one thread, each to completion before the next.
- C) In priority order, preempting lower-priority callbacks.
- D) Only timer callbacks; subscriptions need a separate executor.

---

**Q8.** You swap `rclpy.spin(node)` for a `MultiThreadedExecutor` but your cancel still does not interrupt the running goal. The most likely cause is:

- A) Multi-threaded executors do not support actions.
- B) The execute and cancel callbacks are in the same (default) mutually-exclusive callback group, so they still cannot run concurrently.
- C) You need at least 8 CPU cores.
- D) The cancel request was never sent.

---

**Q9.** Which callback-group assignment is the canonical fix for the action-server cancel deadlock?

- A) Everything in one `ReentrantCallbackGroup`.
- B) Everything in one `MutuallyExclusiveCallbackGroup`.
- C) Execute in a `MutuallyExclusiveCallbackGroup`; cancel callback and sensor subscription in a `ReentrantCallbackGroup`.
- D) Execute in a `ReentrantCallbackGroup`; cancel in a `MutuallyExclusiveCallbackGroup`.

---

**Q10.** What does a `ReentrantCallbackGroup` introduce that a `MutuallyExclusiveCallbackGroup` does not?

- A) Lower latency for all callbacks.
- B) The possibility of data races, because callbacks in it may run concurrently — including with themselves.
- C) Automatic message serialization.
- D) Guaranteed single-threaded execution.

---

**Q11.** In the ROS2 managed-node lifecycle, what is true of a node in the `inactive` state?

- A) Its process has not yet started.
- B) Resources are allocated (publishers/subscriptions/servers exist) but the node is dormant and does no work.
- C) It is identical to `active` but with lower priority.
- D) It has been finalized and cannot transition further.

---

**Q12.** Why does a lifecycle node use `create_lifecycle_publisher` for `cmd_vel` rather than an ordinary publisher?

- A) It is faster.
- B) The lifecycle publisher silently drops messages unless the node is `active`, so a stray publish while inactive never reaches the motors — a hardware-level safety backstop.
- C) Ordinary publishers cannot publish `geometry_msgs/Twist`.
- D) It compresses the messages.

---

**Q13.** When is composing multiple nodes into one process with `component_container_mt` genuinely worth it?

- A) Always — it is strictly better than separate processes.
- B) Never — separate processes are always preferable.
- C) When nodes exchange large messages (intra-process zero-copy pays off) or must share a deployment/lifecycle; otherwise separate processes give fault isolation that is usually worth more.
- D) Only when you have exactly two nodes.

---

## Answer key

> Stop here unless you have answered all thirteen.

| Q | Answer | One-line why |
|---|--------|--------------|
| Q1 | **B** | Topic → service → action → behavior tree; climb only when forced. |
| Q2 | **C** | Cancellation + feedback is the defining capability; it is a safety property. |
| Q3 | **C** | Long-running, cancellable, feedback-worthy actuator command — textbook action. |
| Q4 | **B** | Synchronous `call()` from a callback deadlocks the executor; always `call_async`. |
| Q5 | **B** | `SUCCEEDED`, `CANCELED`, `ABORTED`. |
| Q6 | **B** | Three services (goal/cancel/result) + two topics (feedback/status). |
| Q7 | **B** | One thread, one callback at a time, to completion — hence the cancel deadlock. |
| Q8 | **B** | Same default mutually-exclusive group serializes them even with more threads. |
| Q9 | **C** | Execute mutually-exclusive; cancel + sensor reentrant so they run concurrently. |
| Q10 | **B** | Concurrency at the cost of data races; guard shared compound state. |
| Q11 | **B** | "Ready but holding" — allocated, discoverable, dormant. |
| Q12 | **B** | Lifecycle publishers drop messages while inactive — a motor-level safety net. |
| Q13 | **C** | Large-message graphs or shared deployment; otherwise prefer fault isolation. |

**Scoring.** 11–13: you can architect a ROS2 node. 8–10: re-read the callback-groups and lifecycle sections of Lecture 2. Below 8: re-read both lectures before the mini-project — the project will surface every gap.
