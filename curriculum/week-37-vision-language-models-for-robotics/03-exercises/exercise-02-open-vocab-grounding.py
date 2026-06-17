#!/usr/bin/env python3
# Exercise 2 — Open-vocab grounding (the explicit grounding the gate consumes)
#
# Goal: Build the EXPLICIT grounding that the VLA safety gate checks against.
#       Given an instruction, extract the target noun phrase, run an open-vocab
#       detector over the scene, and return the best box + confidence. This is
#       the INDEPENDENT second opinion (Lecture 1 §5.2) the gate uses to catch
#       a VLA grounding to the wrong object.
#
# Estimated time: 50 minutes. Runnable TODAY — no GPU, no weights.
#
# HOW IT RUNS WITHOUT A GPU
#
#   The detector is behind ONE function, `detect_open_vocab`. This file ships a
#   deterministic STUB detector over a hand-built scene so the GROUNDING LOGIC
#   (phrase extraction, scoring, pick-the-target) is testable now. To use the
#   real OWL-ViT, replace the stub at the marked "# TODO 1" — the rest is
#   unchanged. The contract is: (image, phrase) -> list of (box, score).
#
#       python3 exercise-02-open-vocab-grounding.py
#
# ACCEPTANCE CRITERIA
#
#   [ ] extract_target_phrase turns "bring the red cup" into "red cup".
#   [ ] ground() returns the highest-confidence box for the phrase, or None when
#       the phrase's object is not confidently in the scene (score < threshold).
#   [ ] An absent-object instruction ("bring the green bottle") returns None
#       with a "not in scene" reason — the gate's first rejection path.
#   [ ] You can state why this explicit grounding is gateable but the VLA's
#       internal grounding is not.
#
# Expected output is at the bottom of the file.

from __future__ import annotations

import re
from dataclasses import dataclass

# A "box" is (x1, y1, x2, y2) in pixels. We keep this pure-Python (no numpy
# needed) so it runs anywhere.
Box = tuple[float, float, float, float]

GROUND_CONF_MIN = 0.30      # below this, the object isn't confidently present.

# Stop-words we strip when pulling the target phrase out of an instruction.
_STOP = {"the", "a", "an", "bring", "me", "pick", "up", "grab", "get",
         "move", "to", "left", "right", "please", "put", "place"}


@dataclass
class Detection:
    phrase: str
    box: Box
    score: float

    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.box
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def extract_target_phrase(instruction: str) -> str:
    """Pull the target object phrase out of an instruction.

    "bring the red cup"            -> "red cup"
    "move the blue block to the left" -> "blue block"
    "pick up the tool"             -> "tool"

    This is deliberately simple (strip stop-words / trailing relations). A
    production system would use a proper parser or ask the VLM to name the
    target; for the gate, the object noun phrase is what we need.
    """
    words = re.findall(r"[a-z]+", instruction.lower())
    # Keep the contiguous run of content words before any relation word.
    kept: list[str] = []
    for w in words:
        if w in {"to", "left", "right", "behind", "front", "near", "onto"}:
            break          # a relation marks the end of the target phrase
        if w not in _STOP:
            kept.append(w)
    return " ".join(kept).strip()


# --- The scene + stub detector (replace with OWL-ViT for the real thing) -----

# A hand-built tabletop scene: object name -> (box, "true" detectability).
# In reality these come from the detector running on the camera image.
_SCENE = {
    "red cup":    ((400, 280, 460, 360), 0.88),
    "blue block": ((180, 300, 240, 360), 0.81),
    "tool":       ((600, 260, 700, 320), 0.66),   # a screwdriver, say
    "red stapler":((600, 270, 690, 330), 0.55),   # a DISTRACTOR near the tool
}


def detect_open_vocab(image, phrase: str) -> list[tuple[Box, float]]:
    """STUB open-vocab detector: (image, phrase) -> [(box, score), ...].

    Returns boxes for scene objects whose name overlaps the query phrase, with a
    score that decays for partial matches. Deterministic, GPU-free.
    """
    # TODO 1: replace this whole function body with a real OWL-ViT call:
    #   from transformers import OwlViTProcessor, OwlViTForObjectDetection
    #   inputs = processor(text=[[phrase]], images=image, return_tensors="pt")
    #   outputs = model(**inputs); results = post_process(...)
    #   return [(box, score) for box, score in zip(results["boxes"], results["scores"])]
    query_words = set(phrase.lower().split())
    out: list[tuple[Box, float]] = []
    for name, (box, base_score) in _SCENE.items():
        name_words = set(name.split())
        overlap = query_words & name_words
        if not overlap:
            continue
        # Score scales with how much of the query the object name covers.
        match_frac = len(overlap) / max(1, len(query_words))
        out.append((box, round(base_score * match_frac, 2)))
    # Sort best-first.
    out.sort(key=lambda bs: bs[1], reverse=True)
    return out


def ground(image, instruction: str) -> tuple[Detection | None, str]:
    """Ground an instruction to the best-matching scene object.

    Returns (Detection, reason) on success, or (None, reason) when the target
    object is not confidently in the scene — the gate's first rejection path.
    """
    phrase = extract_target_phrase(instruction)
    if not phrase:
        return None, "could not extract a target phrase from the instruction"
    dets = detect_open_vocab(image, phrase)
    if not dets:
        return None, f"'{phrase}' not detected in the scene at all"
    best_box, best_score = dets[0]
    if best_score < GROUND_CONF_MIN:
        return None, (f"'{phrase}' best score {best_score:.2f} < "
                      f"{GROUND_CONF_MIN} — not confidently present")
    return (Detection(phrase, best_box, best_score),
            f"grounded '{phrase}' at conf {best_score:.2f}")


def main() -> None:
    image = None     # the stub ignores it; the real detector takes a PIL image.

    instructions = [
        "bring the red cup",
        "move the blue block to the left",
        "pick up the tool",
        "bring the green bottle",      # ABSENT object -> should return None
    ]

    print("phrase extraction:")
    for ins in instructions:
        print(f"  '{ins}' -> target phrase '{extract_target_phrase(ins)}'")

    print("\ngrounding:")
    for ins in instructions:
        det, reason = ground(image, ins)
        if det is None:
            print(f"  '{ins}' -> NONE ({reason})")
        else:
            cx, cy = det.center()
            print(f"  '{ins}' -> box {det.box} center ({cx:.0f},{cy:.0f}) "
                  f"conf {det.score:.2f}")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (stub detector)
# -----------------------------------------------------------------------------
#
# phrase extraction:
#   'bring the red cup' -> target phrase 'red cup'
#   'move the blue block to the left' -> target phrase 'blue block'
#   'pick up the tool' -> target phrase 'tool'
#   'bring the green bottle' -> target phrase 'green bottle'
#
# grounding:
#   'bring the red cup' -> box (400, 280, 460, 360) center (430,320) conf 0.88
#   'move the blue block to the left' -> box (180, 300, 240, 360) center (210,330) conf 0.81
#   'pick up the tool' -> box (600, 260, 700, 320) center (650,290) conf 0.66
#   'bring the green bottle' -> NONE ('green bottle' not detected in the scene at all)
#
# THE LESSON: this grounding is INSPECTABLE — a box, a center, a confidence you
# can threshold, and a clean None when the named object isn't present. That is
# exactly what the VLA's internal grounding does NOT give you, and it's why this
# explicit grounding is the gate's "second opinion" (Exercise 3 consumes it).
# Note 'pick up the tool' grounds the tool (0.66) over the red-stapler distractor
# (which never matched the phrase) — but a real OWL-ViT might score them closer,
# which is exactly the kind of near-miss your threshold has to handle.
# -----------------------------------------------------------------------------
