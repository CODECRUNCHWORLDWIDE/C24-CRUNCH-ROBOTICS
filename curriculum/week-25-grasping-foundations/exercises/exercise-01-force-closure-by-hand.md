# Exercise 1 — Force Closure by Hand

**Goal:** Determine, with nothing but the friction-cone rule, whether four 2D two-contact grasps achieve force closure. Then check your hand answers against a tiny `force_closure_2d` function. The point is to make the friction-cone verdict something you compute in your head — because that intuition is what lets you tell a stable grasp from an unstable one when you're staring at a robot that keeps dropping things.

**Estimated time:** 45 minutes. Guided.

---

## The rule (from Lecture 1 §3)

Two point contacts with friction force-close a 2D object **if and only if the line segment joining the two contact points lies inside both friction cones.** The friction cone at a contact has half-angle `alpha = arctan(mu)` about the *inward* surface normal. So for each contact, measure the angle between the closing line and the inward normal; if it is `<= alpha` at *both* contacts, you have force closure.

```
alpha = arctan(mu)
mu = 0.2  -> alpha ~ 11 deg   (slick: narrow cone, unforgiving)
mu = 0.5  -> alpha ~ 27 deg   (rubber-on-plastic: wide cone, forgiving)
mu = 1.0  -> alpha ~ 45 deg   (very grippy)
```

---

## The four grasps

For each grasp you are given two contacts, each with a position and an **inward** normal (already pointing into the object), and a friction coefficient. Decide force closure by hand, then check in code.

**Grasp 1 — opposed faces, aligned.**
- Contact A at (0, 0), inward normal (1, 0).
- Contact B at (1, 0), inward normal (-1, 0).
- `mu = 0.3`.

The line A→B is (1, 0), exactly along A's inward normal (angle 0) and exactly opposite B's, with B's inward normal (-1,0) and the line B→A = (-1,0) (angle 0). Both angles are 0 ≤ `arctan(0.3) ≈ 16.7°`. **Force closure?** Work it out, then confirm.

**Grasp 2 — tilted, wide cone.**
- Contact A at (0, 0), inward normal (1, 0).
- Contact B at (1, 0.4), inward normal (-1, -0.4) (normalized).
- `mu = 0.5`.

The line A→B is (1, 0.4) normalized; its angle to A's inward normal (1,0) is `arctan(0.4/1) ≈ 21.8°`. Compare to `arctan(0.5) ≈ 26.6°`. Then check B's side. **Force closure?**

**Grasp 3 — same tilt, slick.**
- Same contacts as Grasp 2, but `mu = 0.2`.

Now `alpha = arctan(0.2) ≈ 11.3°`, and the line is 21.8° off A's normal. **Force closure?** (This is the lesson: same geometry, less friction, different verdict.)

**Grasp 4 — both contacts on the same side.**
- Contact A at (0, 0), inward normal (0, 1).
- Contact B at (0.3, 0), inward normal (0, 1).
- `mu = 0.5`.

Both inward normals point the same way (0, 1); the line A→B is (1, 0), perpendicular to both normals (angle 90°). Compare to `alpha ≈ 26.6°`. **Force closure?** (This is the "both fingers on the same face" non-grasp.)

---

## Step 1 — Decide all four by hand

Fill in a small table in `force-closure-by-hand.md`:

| Grasp | angle(line, A normal) | angle(line, B normal) | alpha = arctan(mu) | Force closure? |
|---|---|---|---|---|
| 1 | 0° | 0° | 16.7° | ? |
| 2 | 21.8° | ? | 26.6° | ? |
| 3 | 21.8° | ? | 11.3° | ? |
| 4 | 90° | 90° | 26.6° | ? |

---

## Step 2 — Check in code

Save and run this. It uses the `force_closure_2d` from Lecture 1 §3 (note: it takes **inward** normals, exactly as given above).

```python
import numpy as np

def line_in_cone(contact_pt, other_pt, inward_normal, mu) -> bool:
    d = np.asarray(other_pt, float) - np.asarray(contact_pt, float)
    d = d / (np.linalg.norm(d) + 1e-12)
    n = np.asarray(inward_normal, float) / (np.linalg.norm(inward_normal) + 1e-12)
    angle = np.arccos(np.clip(np.dot(d, n), -1.0, 1.0))
    return angle <= np.arctan(mu), np.degrees(angle)

def force_closure_2d(ptA, nA, ptB, nB, mu):
    okA, angA = line_in_cone(ptA, ptB, nA, mu)
    okB, angB = line_in_cone(ptB, ptA, nB, mu)
    return (okA and okB), angA, angB

grasps = [
    ("Grasp 1", (0, 0), (1, 0),   (1, 0),  (-1, 0),     0.3),
    ("Grasp 2", (0, 0), (1, 0),   (1, 0.4),(-1, -0.4),  0.5),
    ("Grasp 3", (0, 0), (1, 0),   (1, 0.4),(-1, -0.4),  0.2),
    ("Grasp 4", (0, 0), (0, 1),   (0.3, 0),(0, 1),      0.5),
]
for name, pA, nA, pB, nB, mu in grasps:
    fc, angA, angB = force_closure_2d(pA, nA, pB, nB, mu)
    print(f"{name}: angleA={angA:5.1f} angleB={angB:5.1f} "
          f"alpha={np.degrees(np.arctan(mu)):5.1f} -> "
          f"{'FORCE CLOSURE' if fc else 'NO closure'}")
```

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `force-closure-by-hand.md` has your hand verdict for all four grasps, with the angles you computed.
- [ ] Your hand verdicts match the code output. (Expected: Grasp 1 closes; Grasp 2 closes; Grasp 3 does **not** close; Grasp 4 does **not** close.)
- [ ] You can state in one sentence why Grasp 2 and Grasp 3 differ despite identical geometry (the friction cone shrank with `mu`, and the same tilt fell outside it).
- [ ] You can state why Grasp 4 fails (both contacts on the same face — the closing line is perpendicular to the normals, far outside the cones; the fingers push the object away, not squeeze it).

---

## Stretch

- For Grasp 2, find the maximum tilt of contact B (the angle of the line off A's normal) that still force-closes at `mu = 0.5`. (It is exactly `alpha = arctan(0.5) ≈ 26.6°` — the cone boundary.) This is the "how much pose error can I tolerate" number, and it is why high-friction objects forgive sloppy grasps.
- Add a third contact and ask whether *form closure* (no friction needed) is achievable — and confirm that two contacts can never form-close a 2D object (you need ≥ 4 frictionless contacts).

---

When the friction-cone verdict feels automatic, move to [Exercise 2 — The antipodal sampler](exercise-02-antipodal-sampler.py).
