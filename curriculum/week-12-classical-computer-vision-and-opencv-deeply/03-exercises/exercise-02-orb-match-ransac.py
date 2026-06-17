#!/usr/bin/env python3
# Exercise 2 — ORB matching with RANSAC outlier rejection
#
# Goal: Run the full classical feature pipeline on two views of a scene —
#       detect ORB features, describe them, match with Lowe's ratio test, then
#       reject the surviving outliers with a RANSAC homography — and read the
#       INLIER RATIO as a trust metric. This is the "the geometry closed" promise
#       for matching (Lecture 2 §3): a high inlier ratio means the recovered
#       geometry is trustworthy; a low one means your matches are mostly noise.
#
# WHY SYNTHETIC
#
#   We generate a textured scene and warp it by a KNOWN homography, so we have
#   ground truth: a correct match pipeline must recover that homography and report
#   a high inlier ratio. Then we inject random WRONG matches and show RANSAC
#   rejects them — the lesson is that RANSAC tells you whether the data supported a
#   model at all, the same diagnostic value as the reprojection error and NEES.
#
# HOW TO USE THIS FILE
#
#       pip install opencv-python numpy
#       python3 exercise-02-orb-match-ransac.py
#
#   Optionally pass --save to write match-visualization PNGs.
#
# ACCEPTANCE CRITERIA
#
#   [ ] ORB finds hundreds of features on the textured scene.
#   [ ] After Lowe's ratio test, a few hundred good matches remain.
#   [ ] RANSAC reports a HIGH inlier ratio (> 80% on this clean synthetic pair).
#   [ ] When 30% deliberately-wrong matches are injected, the ratio-test + RANSAC
#       pipeline still recovers a high-inlier model and rejects the planted noise.
#   [ ] You can state why the ratio is a TRUST metric (Lecture 2 §3).
#
# Expected output is at the bottom of the file.

import argparse

import cv2
import numpy as np

RNG = np.random.default_rng(12)
W, H = 640, 480

# A known homography: small rotation + translation + slight perspective.
H_TRUE = np.array([
    [0.98, -0.10, 25.0],
    [0.10, 0.98, -15.0],
    [1e-5, 5e-5, 1.0],
])


def make_textured_scene() -> np.ndarray:
    """A grayscale scene full of corners ORB can latch onto."""
    img = np.full((H, W), 40, np.uint8)
    for _ in range(120):
        x, y = int(RNG.integers(20, W - 20)), int(RNG.integers(20, H - 20))
        r = int(RNG.integers(5, 20))
        c = int(RNG.integers(120, 255))
        cv2.rectangle(img, (x - r, y - r), (x + r, y + r), c, -1)
    for _ in range(60):
        x, y = int(RNG.integers(20, W - 20)), int(RNG.integers(20, H - 20))
        cv2.circle(img, (x, y), int(RNG.integers(4, 12)), int(RNG.integers(120, 255)), -1)
    return img


def match_and_ransac(img1, img2, label):
    orb = cv2.ORB_create(nfeatures=1500)
    kp1, des1 = orb.detectAndCompute(img1, None)
    kp2, des2 = orb.detectAndCompute(img2, None)

    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    knn = bf.knnMatch(des1, des2, k=2)

    # Lowe's ratio test: keep a match only if the best is clearly better than 2nd.
    good = [m for m, n in knn if m.distance < 0.75 * n.distance]

    pts1 = np.float32([kp1[m.queryIdx].pt for m in good])
    pts2 = np.float32([kp2[m.trainIdx].pt for m in good])

    Hm, mask = cv2.findHomography(pts1, pts2, cv2.RANSAC, ransacReprojThreshold=3.0)
    inliers = int(mask.sum())
    ratio = 100.0 * inliers / max(len(good), 1)
    print(f"[{label}] kp1={len(kp1)} kp2={len(kp2)} | ratio-test good={len(good)} | "
          f"RANSAC inliers={inliers} ({ratio:.0f}%)")
    return Hm, ratio, kp1, kp2, good, mask


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    img1 = make_textured_scene()
    img2 = cv2.warpPerspective(img1, H_TRUE, (W, H))

    print("==================== ORB + RANSAC ====================")
    # 1. Clean pair.
    Hm, ratio_clean, kp1, kp2, good, mask = match_and_ransac(img1, img2, "clean")

    # 2. How close is the recovered homography to the truth? Compare where the
    #    image corners map under each.
    corners = np.float32([[0, 0], [W, 0], [W, H], [0, H]]).reshape(-1, 1, 2)
    true_proj = cv2.perspectiveTransform(corners, H_TRUE).reshape(-1, 2)
    est_proj = cv2.perspectiveTransform(corners, Hm).reshape(-1, 2)
    corner_err = float(np.mean(np.linalg.norm(true_proj - est_proj, axis=1)))
    print(f"[clean] recovered-homography corner error vs truth: {corner_err:.2f} px")

    # 3. Inject 30% deliberately-wrong matches and show RANSAC survives them.
    #    We simulate this at the point-correspondence level for clarity.
    orb = cv2.ORB_create(nfeatures=1500)
    k1, d1 = orb.detectAndCompute(img1, None)
    k2, d2 = orb.detectAndCompute(img2, None)
    knn = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(d1, d2, k=2)
    good2 = [m for m, n in knn if m.distance < 0.75 * n.distance]
    p1 = np.float32([k1[m.queryIdx].pt for m in good2])
    p2 = np.float32([k2[m.trainIdx].pt for m in good2])
    n_bad = int(0.30 * len(p2))
    bad_idx = RNG.choice(len(p2), n_bad, replace=False)
    p2_contaminated = p2.copy()
    p2_contaminated[bad_idx] = RNG.uniform(0, [W, H], size=(n_bad, 2)).astype(np.float32)
    _, mask2 = cv2.findHomography(p1, p2_contaminated, cv2.RANSAC, 3.0)
    inl2 = int(mask2.sum())
    rejected = len(p1) - inl2
    print(f"[contaminated] injected {n_bad} wrong matches into {len(p1)} | "
          f"RANSAC kept {inl2} inliers, rejected {rejected}")
    print("======================================================")
    print("Lesson: the inlier RATIO is a trust metric. A clean pair gives a high "
          "ratio and a recovered homography within ~1 px of truth. RANSAC rejects "
          "the planted wrong matches without ever being told which they were — the "
          "geometric sibling of the Week 11 robust kernel (Lecture 2 §3).")

    if args.save:
        vis = cv2.drawMatches(img1, kp1, img2, kp2, good[:40], None,
                              matchesMask=mask.ravel()[:40].tolist(),
                              flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
        cv2.imwrite("orb_matches.png", vis)
        print("saved orb_matches.png")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (deterministic seed; exact counts depend on your OpenCV build)
# -----------------------------------------------------------------------------
#
# ==================== ORB + RANSAC ====================
# [clean] kp1=15xx kp2=15xx | ratio-test good=6xx | RANSAC inliers=6xx (9x%)
# [clean] recovered-homography corner error vs truth: 0.xx px
# [contaminated] injected 1xx wrong matches into 6xx | RANSAC kept 4xx inliers,
#                rejected 2xx
# ======================================================
# Lesson: the inlier RATIO is a trust metric. ...
#
# The INVARIANT shape, not the exact counts: the clean pair gives a high inlier
# ratio (> 80%) and a recovered homography within ~1 px of the true one; with 30%
# wrong matches injected, RANSAC rejects ~all of them and keeps the true inliers.
# If your clean-pair ratio is LOW (< 50%), your matching is broken — check that
# you applied the ratio test and used NORM_HAMMING for the binary ORB descriptors.
# -----------------------------------------------------------------------------
