# Week 27 — Resources

Every resource here is **free**. The imitation-learning papers are open-access (arXiv); the PyTorch docs and tutorials are open; the robot-learning course materials are public. No paywalled book is required for this week.

## Required reading (work it into your week)

- **DAgger — "A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning"** (Ross, Gordon, Bagnell, AISTATS 2011) — *the* DAgger paper, and the source of the covariate-shift and `O(εT²)` (BC) vs. `O(εT)` (DAgger) error-growth analysis. Read §1–3 and the algorithm box:
  <https://arxiv.org/abs/1011.0686>
- **"Efficient Reductions for Imitation Learning"** (Ross & Bagnell, AISTATS 2010) — the earlier paper that frames why naive behavior cloning has the compounding-error problem; the intellectual setup for DAgger:
  <https://proceedings.mlr.press/v9/ross10a.html>
- **PyTorch — "Training a Classifier" / the 60-minute blitz** — if your training-loop muscle memory is rusty, this is the refresher; the loop you write this week is exactly this shape:
  <https://pytorch.org/tutorials/beginner/blitz/cifar10_tutorial.html>
- **CS285 (Berkeley Deep RL) — "Imitation Learning" lecture** (Levine) — the canonical lecture-note treatment of behavior cloning, distributional shift, and DAgger; the slides and the lecture video are free:
  <https://rail.eecs.berkeley.edu/deeprlcourse/>

## Imitation learning, deeper

- **"An Algorithmic Perspective on Imitation Learning"** (Osa et al., 2018) — a free survey that situates BC and DAgger among the broader imitation-learning family (inverse RL, GAIL); read the BC and DAgger sections for context:
  <https://arxiv.org/abs/1811.06711>
- **ALVINN — "An Autonomous Land Vehicle in a Neural Network"** (Pomerleau, 1988) — the original behavior-cloning robot (a neural net that learned to steer a van from camera input). Read it to see BC's structural flaw appear in 1988 and stay unsolved until DAgger:
  <https://proceedings.neurips.cc/paper/1988/hash/812b4ba287f5ee0bc9d43bbf5bbe87fb-Abstract.html>
- **LeRobot (Hugging Face)** — the open robot-learning library that ships BC, ACT, and Diffusion Policy with a common dataset format; read its BC implementation to see a production-quality training loop, and note its dataset format (you can adopt it for the mini-project so Weeks 29–30 reuse your demos):
  <https://github.com/huggingface/lerobot>

## The methods you motivate this week (forward references)

- **ACT — "Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware"** (Zhao et al., RSS 2023) — action chunking, the direct answer to the diffusion-of-error problem you meet this week. Read the abstract and the action-chunking section now; you implement it in Week 30:
  <https://tonyzhaozh.github.io/aloha/>
- **Diffusion Policy — "Visuomotor Policy Learning via Action Diffusion"** (Chi et al., RSS 2023) — the method that eats the multimodal-action problem BC's MSE loss can't handle. Read the abstract now; you train it in Week 29 on these demos:
  <https://diffusion-policy.cs.columbia.edu/>

## PyTorch and training references

- **PyTorch — Datasets & DataLoaders** — the `Dataset` / `DataLoader` you wrap your demos in:
  <https://pytorch.org/tutorials/beginner/basics/data_tutorial.html>
- **PyTorch — `nn.Module` and the optimization loop** — the policy network and the train step:
  <https://pytorch.org/tutorials/beginner/basics/optimization_tutorial.html>
- **PyTorch — saving and loading models** — checkpoint the policy so DAgger rounds resume from the last one:
  <https://pytorch.org/tutorials/beginner/saving_loading_models.html>
- **scikit-learn — train_test_split and metrics** — the held-out split and the success-rate confidence interval for honest evaluation:
  <https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html>

## Demo collection and sim

- **`teleop_twist_keyboard`** — keyboard teleop for collecting demonstrations; the simplest expert:
  <https://github.com/ros2/teleop_twist_keyboard>
- **`joy` and `teleop_twist_joy`** — gamepad teleop, a smoother expert than the keyboard for collecting clean demos:
  <https://docs.ros.org/en/jazzy/p/teleop_twist_joy/>
- **`ros2 bag` (rosbag2)** — record synchronized observation + action topics during teleop; replay to build the dataset. The honest way to capture demos with correct timestamps:
  <https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Recording-And-Playing-Back-Data/Recording-And-Playing-Back-Data.html>
- **Gz Sim (Harmonic)** — the sim your reach task lives in; the ground-truth block pose comes from the model state:
  <https://gazebosim.org/docs/harmonic>

## Tools you'll use this week

- **PyTorch** — `pip install torch`. The policy network and the training loop. CPU is fine for this week's small MLP.
- **NumPy** — observation/action normalization, the dataset arrays.
- **Matplotlib** — the loss curves (train vs. val) and the success-rate-vs-DAgger-round plot.
- **`ros2 bag`** — record and replay demonstrations.
- **rviz2** — watch the policy roll out and drift; the visual signature of covariate shift.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Behavior cloning (BC)** | Imitation as supervised learning: train a policy to map observations to the expert's actions. |
| **Policy** | A function (here, a neural net) mapping observation → action. |
| **Demonstration** | An (observation, action) trajectory from an expert (teleop or scripted). |
| **Covariate shift** | The mismatch between the states the training data covered and the states the policy actually visits when it acts. BC's structural flaw. |
| **Compounding error** | One small action error → an unfamiliar state → a bigger error; errors grow over a trajectory (`O(εT²)` for BC). |
| **DAgger** | Dataset Aggregation: roll out the policy, query the expert at the *visited* states, aggregate, retrain. The covariate-shift fix. |
| **β (beta) schedule** | The DAgger mixing weight: early rounds execute more expert action, later rounds more policy action. |
| **Diffusion of error** | Per-step errors accumulating over a multi-step task; motivates action chunking. |
| **Action chunking** | Predicting a *sequence* of future actions at once (ACT) to reduce compounding error. |
| **Success predicate** | The crisp, pre-stated condition that counts a trial as a success (e.g., gripper within X cm of the block). |
| **Eval protocol** | The fixed procedure (same starts, N seeds) that makes a success rate comparable across policies. |

---

*If a link 404s, please open an issue so we can replace it. The arXiv papers and the course pages are canonical and reappear on the same hosts.*
