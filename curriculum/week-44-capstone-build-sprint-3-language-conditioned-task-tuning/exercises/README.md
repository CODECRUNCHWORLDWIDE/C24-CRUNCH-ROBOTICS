# Week 44 — Exercises

Three exercises that build the week's apparatus in order: curate the suite, measure the baseline, fine-tune and re-measure. Do them in sequence — exercise 2 consumes the suite from exercise 1, and exercise 3 consumes the baseline from exercise 2.

## Index

1. **[Exercise 1 — Curate the twenty-instruction eval suite](exercise-01-curate-the-eval-suite.md)** — author and freeze `eval_suite.yaml`: twenty stratified instructions, deterministic scene resets, a binary success rubric. Commit it. (~75 min)
2. **[Exercise 2 — Run the baseline VLA against the full suite](exercise-02-run-baseline-suite.py)** — a runnable `rclpy` eval-runner that resets the scene, issues each instruction to the policy action server, scores the outcome, and writes a per-instruction report. (~90 min)
3. **[Exercise 3 — Fine-tune on fifty demos and re-run](exercise-03-finetune-and-rerun.py)** — a runnable LoRA fine-tune over fifty LeRobot-format demos plus a re-run-and-diff harness that produces the baseline-vs-fine-tuned table. (~90 min + GPU time)

## How to work the exercises

- **Type the code yourself.** Do not copy-paste the runner. The point of exercise 2 is that you understand every line of your own eval harness, because you will defend its numbers in week 48.
- **Run on your capstone stack.** These exercises assume the ROS2 Jazzy workspace, the policy action server, and the perception stack you have built over the prior weeks. They are not standalone toys; they tune *your* robot.
- **Freeze before you train.** Finish exercise 1 and commit the suite *before* you start exercise 3's fine-tune. The whole methodology depends on the suite being frozen first.
- **Reserve GPU time for exercise 3 early.** The fine-tune is the long pole — an hour or two on a workstation GPU, overnight on an Orin. Do not start it Saturday night.

Every exercise ends with an artifact you commit: the frozen suite (1), the baseline report (2), the fine-tuned report and diff (3). Those three artifacts are also the spine of this week's mini-project.

There are no solutions checked in. After you finish, search GitHub for `c24-week-44` to compare with other learners' suites and runners.
