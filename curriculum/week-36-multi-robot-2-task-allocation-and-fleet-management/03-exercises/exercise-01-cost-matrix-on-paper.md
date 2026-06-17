# Exercise 1 — The Cost Matrix on Paper

**Goal:** Build a cost matrix from robot and task poses by hand, solve the assignment two ways — greedy `argmin` and the Hungarian algorithm — and *prove to yourself* that greedy is sub-optimal on a matrix designed to break it. You will train the single most important instinct of the week: **task allocation is a joint optimization, not a per-task lookup.**

**Estimated time:** 50 minutes. Guided.

---

## Setup

No code required for Steps 1–4 — pencil and paper, or a text file. Step 5 checks your work with one `scipy` call:

```bash
python3 -c "import scipy, numpy; print('ok', scipy.__version__)"
```

---

## Step 1 — Build a cost matrix from poses

Three robots and three delivery tasks. Robot poses and task pickup locations, in meters:

```
robot r1 at (0, 0)      task t1 pickup at (1, 1)
robot r2 at (10, 0)     task t2 pickup at (9, 1)
robot r3 at (5, 8)      task t3 pickup at (4, 4)
```

Compute the cost matrix `C` where `C[i][j]` is the **Euclidean travel distance** from robot `i` to task `j`'s pickup. Round to 2 decimals. Fill in the table:

| | t1 (1,1) | t2 (9,1) | t3 (4,4) |
|---|---|---|---|
| **r1 (0,0)** | ? | ? | ? |
| **r2 (10,0)** | ? | ? | ? |
| **r3 (5,8)** | ? | ? | ? |

Reminder: `dist = sqrt((xr - xt)^2 + (yr - yt)^2)`.

<details>
<summary>Check your matrix</summary>

```
        t1     t2     t3
r1     1.41   9.06   5.66
r2     9.06   1.41   7.21
r3     8.06   8.06   4.12
```

</details>

> **Note the lie.** Euclidean distance assumes the robot can fly straight to the pickup. In a real building there are walls; `C[i][j]` should be the **path cost through the nav graph** (Lecture 1 §1.2). For this exercise Euclidean is fine; in the mini-project you'll use a graph distance. Write down, in one sentence, a case where Euclidean would pick the wrong robot (hint: a robot that's close *as the crow flies* but on the far side of a wall).

---

## Step 2 — Solve it greedily

Run the greedy algorithm by hand: repeatedly pick the single smallest remaining cell, assign it, cross out that row and column, repeat.

1. Smallest cell overall: `___ → ___` at cost `___`.
2. Next smallest remaining: `___ → ___` at cost `___`.
3. Last pair: `___ → ___` at cost `___`.

Greedy total: `___`.

<details>
<summary>Check greedy</summary>

1. Smallest is a tie at 1.41: r1→t1 and r2→t2. Take r1→t1 (1.41). Cross out r1, t1.
2. Remaining cells: r2→t2 (1.41), r2→t3 (7.21), r3→t2 (8.06), r3→t3 (4.12). Smallest is r2→t2 (1.41). Cross out r2, t2.
3. Last: r3→t3 (4.12).

Greedy total: 1.41 + 1.41 + 4.12 = **6.94**. (On *this* matrix greedy happens to be optimal — that's deliberate. The next step plants a matrix where it isn't.)

</details>

---

## Step 3 — The planted matrix where greedy loses

Now use this cost matrix (two robots, two tasks) — it's the §2 counterexample from Lecture 1, the decisive one:

```
        t1     t2
r1       1     2
r2       2    100
```

**Greedy:**
1. Smallest cell: `___ → ___` at cost `___`.
2. Forced last pair: `___ → ___` at cost `___`.
3. Greedy total: `___`.

**Optimal (enumerate both — there are only two assignments):**
- r1→t1, r2→t2: cost `___`
- r1→t2, r2→t1: cost `___`
- Optimal total: `___`.

How many times worse is greedy than optimal here? `___`×.

<details>
<summary>Check</summary>

Greedy grabs r1→t1 (1), forcing r2→t2 (100). Greedy total = **101**.
Optimal is r1→t2 (2) + r2→t1 (2) = **4**.
Greedy is **25.25×** worse. The locally cheap r1→t1=1 stranded r2 on the catastrophic 100. This is the whole argument against greedy for ST-SR-IA: a locally cheap choice can force a globally ruinous one.

</details>

---

## Step 4 — The Hungarian algorithm by hand on Step 1's matrix

Run the four steps from Lecture 1 §3.1 on the Step 1 matrix (round to 2 decimals throughout):

```
        t1     t2     t3
r1     1.41   9.06   5.66
r2     9.06   1.41   7.21
r3     8.06   8.06   4.12
```

1. **Row reduction.** Subtract each row's min. (Row mins: r1=1.41, r2=1.41, r3=4.12.) Write the reduced matrix.
2. **Column reduction.** Subtract each column's min from the row-reduced matrix.
3. **Cover the zeros** with the minimum number of lines. If it equals 3, read off the assignment of independent zeros.

<details>
<summary>Check</summary>

After row reduction:
```
        t1     t2     t3
r1     0.00   7.65   4.25
r2     7.65   0.00   5.80
r3     3.94   3.94   0.00
```
Column mins are now 0.00 / 0.00 / 0.00 — column reduction changes nothing. The zeros sit at r1→t1, r2→t2, r3→t3, which are already independent (distinct rows, distinct columns). Three lines cover them; an optimal assignment exists: **r1→t1, r2→t2, r3→t3**, total `1.41 + 1.41 + 4.12 = 6.94`. Matches greedy here — but you proved in Step 3 that's luck, not a guarantee.

</details>

---

## Step 5 — Confirm with `scipy`

Now, and only now, check your Step 1 and Step 3 work with the solver:

```python
import numpy as np
from scipy.optimize import linear_sum_assignment

C1 = np.array([[1.41, 9.06, 5.66],
               [9.06, 1.41, 7.21],
               [8.06, 8.06, 4.12]])
r, c = linear_sum_assignment(C1)
print("step 1:", list(zip(r, c)), "total", round(C1[r, c].sum(), 2))   # total 6.94

C3 = np.array([[1, 2],
               [2, 100]])
r, c = linear_sum_assignment(C3)
print("step 3:", list(zip(r, c)), "total", C3[r, c].sum())             # total 4
```

Your hand-worked assignments must match the solver's. If they don't, find your arithmetic error before moving on — debugging your own hand-solve is the learning.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] Your Step 1 cost matrix matches the check (within rounding).
- [ ] You can state, in one sentence, a case where Euclidean cost picks the wrong robot versus a nav-graph cost.
- [ ] Your Step 3 greedy total is 101, optimal is 4, and you can say *why* greedy lost (it stranded r2 on the 100-cost cell).
- [ ] Your hand-run Hungarian assignment on Step 1 matches `scipy`'s.
- [ ] You can explain in one sentence why subtracting a row's minimum doesn't change which assignment is optimal (each assignment uses exactly one cell per row).

---

## Stretch

- **Make a 3×3 where greedy loses.** Construct a cost matrix where greedy and Hungarian give *different* assignments, and compute how much worse greedy is. (Hint: put one very cheap cell that, when taken, strands a robot on an expensive-only row.)
- **Maximize instead.** Re-cast the Step 1 matrix as a *reward* (negate it) and confirm `linear_sum_assignment(C, maximize=True)` gives the assignment that *maximizes* total reward — useful when the matrix is utility, not cost.
- **Add a fourth task** (more tasks than robots) and run `linear_sum_assignment` on the 3×4 matrix. Which task goes unassigned, and why? (It returns only `min(N,M)=3` pairs.) Confirm the leftover task is the one no robot is cheap on.

---

When this feels comfortable, move to [Exercise 2 — The Hungarian allocator](./exercise-02-hungarian-allocator.py).
