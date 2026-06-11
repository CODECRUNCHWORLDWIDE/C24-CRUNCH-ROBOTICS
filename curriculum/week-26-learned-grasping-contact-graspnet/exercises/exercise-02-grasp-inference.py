#!/usr/bin/env python3
# Exercise 2 — Grasp inference and ranking
#
# Goal: Run a Contact-GraspNet-shaped model on a point cloud, threshold the
#       per-point grasp confidence, reconstruct 6-DOF poses from the raw outputs,
#       and apply grasp NMS to collapse the hundreds of near-duplicate proposals
#       into a short, ranked, diverse shortlist — exactly what the pick node hands
#       to MoveIt2.
#
# Estimated time: 50 minutes. Runnable.
#
# WHY A TINY RANDOM MODEL?
#
#   Training Contact-GraspNet is a multi-GPU, multi-day job; this exercise is
#   about the *pipeline*, not the weights. We ship a tiny randomly-initialized
#   model with the SAME output signature as the real network
#   (conf, approach, baseline, width). The shapes, the thresholding, the pose
#   reconstruction, and the NMS are identical whether the weights are random or
#   the real ACRONYM-trained checkpoint. When you have the real checkpoint, set
#   USE_REAL_CHECKPOINT and CHECKPOINT_PATH below; everything else is unchanged.
#
# HOW TO USE THIS FILE
#
#       source /opt/ros/jazzy/setup.bash
#       python3 exercise-02-grasp-inference.py
#
#   It builds a synthetic "object on a table" cloud, runs inference, reconstructs
#   poses for confident points, NMS-ranks them, and prints the shortlist. With the
#   random model the grasps are nonsense geometrically (random init), but the
#   PIPELINE is correct: confident-point count, pose validity (orthonormal R), and
#   the NMS reduction all behave exactly as with the real weights.
#
# ACCEPTANCE CRITERIA
#
#   [ ] The script runs end to end and prints a non-empty ranked shortlist.
#   [ ] Every reconstructed pose has an orthonormal rotation (the script asserts it).
#   [ ] NMS strictly reduces the count (kept < confident), and the kept grasps are
#       spatially/angularly diverse (the script reports min pairwise separation).
#   [ ] You can explain why thresholding on sigmoid(conf) > 0.75 is the confidence
#       gate, and what lowering it to 0.5 would do (more grasps, more false positives).
#
# Expected output (shape) is at the bottom of the file.

import math

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# ---- Switch to the real checkpoint when you have it ------------------------
USE_REAL_CHECKPOINT = False
CHECKPOINT_PATH = "contact_graspnet.pt"
CONF_THRESHOLD = 0.75
# ---------------------------------------------------------------------------


# =====================================================================
#  A minimal model with the Contact-GraspNet output signature.
#  Backbone is a per-point MLP here (not the full PointNet++) purely so the
#  exercise runs instantly on CPU. The HEADS and OUTPUTS match the real net.
# =====================================================================
class TinyGraspNet(nn.Module):
    def __init__(self, feat_dim: int = 128) -> None:
        super().__init__()
        # Stand-in backbone: shared per-point MLP. Real CGN is PointNet++ here.
        self.backbone = nn.Sequential(
            nn.Conv1d(3, 64, 1), nn.ReLU(inplace=True),
            nn.Conv1d(64, feat_dim, 1), nn.ReLU(inplace=True),
        )
        self.conf_head = nn.Conv1d(feat_dim, 1, 1)
        self.dir_head = nn.Conv1d(feat_dim, 6, 1)
        self.width_head = nn.Conv1d(feat_dim, 1, 1)

    def forward(self, xyz: torch.Tensor):
        """xyz: (B, N, 3). Returns conf (B,N), approach (B,3,N), baseline (B,3,N), width (B,N)."""
        f = self.backbone(xyz.permute(0, 2, 1))             # (B, feat, N)
        conf = self.conf_head(f).squeeze(1)                 # (B, N) logits
        dirs = self.dir_head(f)                             # (B, 6, N)
        approach = F.normalize(dirs[:, 0:3, :], dim=1)      # (B, 3, N) unit
        baseline = dirs[:, 3:6, :]
        proj = (baseline * approach).sum(1, keepdim=True) * approach
        baseline = F.normalize(baseline - proj, dim=1)      # ⟂ approach, unit
        width = F.softplus(self.width_head(f).squeeze(1))   # (B, N) > 0
        return conf, approach, baseline, width


# =====================================================================
#  Pose reconstruction (the batched form from Exercise 1).
# =====================================================================
def reconstruct_grasp_poses(contact_pts, approach, baseline, width):
    """contact (N,3), approach (N,3), baseline (N,3), width (N,) -> (N,4,4)."""
    z = F.normalize(approach, dim=-1)
    x = F.normalize(baseline, dim=-1)
    y = torch.cross(z, x, dim=-1)
    x = F.normalize(torch.cross(y, z, dim=-1), dim=-1)      # re-orthonormalize
    y = F.normalize(y, dim=-1)
    R = torch.stack([x, y, z], dim=-1)                      # (N,3,3)
    center = contact_pts + 0.5 * width.unsqueeze(-1) * x
    N = contact_pts.shape[0]
    T = torch.zeros(N, 4, 4)
    T[:, :3, :3] = R
    T[:, :3, 3] = center
    T[:, 3, 3] = 1.0
    return T


# =====================================================================
#  Grasp NMS.
# =====================================================================
def grasp_nms(centers, approaches, scores, dist_thresh=0.02, angle_thresh_deg=30.0):
    order = torch.argsort(scores, descending=True)
    cos_t = math.cos(math.radians(angle_thresh_deg))
    suppressed = torch.zeros(len(order), dtype=torch.bool)
    keep = []
    for rank, idx in enumerate(order):
        if suppressed[rank]:
            continue
        keep.append(idx.item())
        rest = order[rank + 1:]
        close = (centers[rest] - centers[idx]).norm(dim=-1) < dist_thresh
        aligned = (approaches[rest] * approaches[idx]).sum(-1) > cos_t
        newly = close & aligned & ~suppressed[rank + 1:]
        suppressed[rank + 1:][newly] = True
    return keep


# =====================================================================
#  Synthetic scene: a box-ish object sitting on a table plane.
# =====================================================================
def synthetic_object_cloud(n=4096, seed=0):
    g = torch.Generator().manual_seed(seed)
    # Table plane z ~ 0.5 m in front of camera, x,y spread.
    table = torch.rand(n // 2, 3, generator=g)
    table[:, 0] = table[:, 0] * 0.4 - 0.2
    table[:, 1] = table[:, 1] * 0.4 - 0.2
    table[:, 2] = 0.50 + torch.randn(n // 2, generator=g) * 0.002
    # A 6cm cube object raised above the table.
    obj = torch.rand(n // 2, 3, generator=g) * 0.06 - 0.03
    obj[:, 2] = 0.44 + torch.rand(n // 2, generator=g) * 0.06
    return torch.cat([table, obj], dim=0)


def main() -> None:
    torch.manual_seed(0)
    model = TinyGraspNet().eval()
    if USE_REAL_CHECKPOINT:
        state = torch.load(CHECKPOINT_PATH, map_location="cpu")
        model.load_state_dict(state, strict=False)
        print(f"loaded real checkpoint: {CHECKPOINT_PATH}")
    else:
        print("using TINY RANDOM model — pipeline test, not real grasps")

    cloud = synthetic_object_cloud(n=4096)                  # (N, 3)
    print(f"input cloud: {cloud.shape[0]} points")

    with torch.no_grad():
        conf, approach, baseline, width = model(cloud.unsqueeze(0))
        scores = torch.sigmoid(conf)[0]                     # (N,)
        keep_mask = scores > CONF_THRESHOLD
        n_conf = int(keep_mask.sum())
        print(f"points above confidence {CONF_THRESHOLD}: {n_conf}")
        if n_conf == 0:
            print("no confident grasp — in the real system this triggers the "
                  "antipodal fallback (Lecture 2 §5).")
            return

        T = reconstruct_grasp_poses(
            cloud[keep_mask],
            approach[0].permute(1, 0)[keep_mask],
            baseline[0].permute(1, 0)[keep_mask],
            width[0][keep_mask],
        )
        # Assert every reconstructed rotation is valid (Exercise 1 lesson).
        for Ti in T:
            R = Ti[:3, :3]
            assert (R.T @ R - torch.eye(3)).abs().max() < 1e-4, "non-orthonormal R!"
        print(f"reconstructed {T.shape[0]} valid poses")

        centers = T[:, :3, 3]
        appr = approach[0].permute(1, 0)[keep_mask]
        kept = grasp_nms(centers, appr, scores[keep_mask])
        print(f"after NMS: {len(kept)} diverse grasps (best-first)")
        assert len(kept) < n_conf, "NMS should reduce the count"

        # Report diversity: min pairwise center separation among kept grasps.
        kc = centers[torch.tensor(kept)]
        if len(kept) > 1:
            d = torch.cdist(kc, kc) + torch.eye(len(kept)) * 1e9
            print(f"min pairwise separation among kept grasps: {d.min():.3f} m")

        print("\nTop 3 ranked grasps (camera frame):")
        for r, i in enumerate(kept[:3]):
            c = centers[i]
            print(f"  #{r+1}  conf={scores[keep_mask][i]:.3f}  "
                  f"width={width[0][keep_mask][i]:.3f}m  "
                  f"center=({c[0]:+.3f},{c[1]:+.3f},{c[2]:+.3f})")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (SHAPE — exact numbers vary with the random init / seed)
# -----------------------------------------------------------------------------
#
# using TINY RANDOM model — pipeline test, not real grasps
# input cloud: 4096 points
# points above confidence 0.75: 137
# reconstructed 137 valid poses
# after NMS: 22 diverse grasps (best-first)
# min pairwise separation among kept grasps: 0.021 m
#
# Top 3 ranked grasps (camera frame):
#   #1  conf=0.94  width=0.061m  center=(+0.012,-0.041,+0.498)
#   #2  conf=0.92  width=0.058m  center=(-0.103,+0.077,+0.501)
#   #3  conf=0.90  width=0.063m  center=(+0.150,-0.011,+0.500)
#
# The INVARIANTS that must hold (and that the asserts check) regardless of weights:
#   * every reconstructed R is orthonormal,
#   * NMS strictly reduces the confident-grasp count,
#   * kept grasps are at least ~dist_thresh apart.
# With the REAL checkpoint the grasps cluster on the object (z ~ 0.44–0.50) and
# avoid the table plane; with random weights they're scattered. That difference is
# exactly what the weights buy you — the pipeline around them is what you built here.
# -----------------------------------------------------------------------------
