#!/usr/bin/env python3
# Exercise 3 — A ROS2 detection node (vision_msgs/Detection2DArray publisher)
#
# Goal: Wrap an inference runtime in a ROS2 node that consumes /camera/image_raw
#       and publishes /detections as vision_msgs/Detection2DArray — applying THREE
#       Week 5 lessons that make or break a real inference node:
#         1. sensor QoS (BEST_EFFORT) on both image sub and detection pub,
#         2. the ACQUISITION-TIME stamp carried through (not now()),
#         3. the standard vision_msgs message (not a custom one).
#       The decode/NMS/rescale postprocessing is the Lecture 1 §7 path.
#
# THIS IS FILL-IN-THE-BLANK STARTER CODE.
#   The structure and the hard parts (QoS, stamping, decode) are given. The TODOs
#   are the spots where YOU wire the specifics. Search for "# TODO" — each is one
#   focused decision. The node is correct and complete except for those blanks.
#
# HOW TO RUN
#   This needs a ROS2 Jazzy environment with rclpy, cv_bridge, vision_msgs, and an
#   inference runtime. Drop it in an ament_python package and:
#       ros2 run <your_pkg> detection_node
#   Feed it a camera (real, Gz Sim, or `ros2 run image_publisher image_publisher`).
#   Verify:
#       ros2 topic echo /detections
#       ros2 topic info /detections -v     # both ends BEST_EFFORT (Week 5)
#
# ACCEPTANCE CRITERIA
#   [ ] /detections publishes Detection2DArray when objects are in view.
#   [ ] ros2 topic info confirms BEST_EFFORT on the image sub and detection pub.
#   [ ] Each detection's header.stamp equals the IMAGE's stamp (not now()).
#   [ ] Boxes are rescaled back to the original image pixels (letterbox undone).
#   [ ] The node degrades gracefully (no crash) when no objects are detected.

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from vision_msgs.msg import (
    Detection2D,
    Detection2DArray,
    ObjectHypothesisWithPose,
)
from cv_bridge import CvBridge
import cv2


# ---------------------------------------------------------------------------
# Inference runtime wrapper. On Path B this is ONNX Runtime on CPU; on Path A it
# is TensorRT. The NODE does not care which — it calls .infer(tensor).
# ---------------------------------------------------------------------------
class OrtRuntime:
    """ONNX Runtime wrapper (Path-B CPU default; pass a GPU provider for Path A)."""

    def __init__(self, onnx_path: str, providers=None):
        import onnxruntime as ort
        if providers is None:
            providers = ["CPUExecutionProvider"]
        self.sess = ort.InferenceSession(onnx_path, providers=providers)
        self.input_name = self.sess.get_inputs()[0].name

    def infer(self, tensor: np.ndarray) -> np.ndarray:
        return self.sess.run(None, {self.input_name: tensor})[0]


def letterbox(img, size=640):
    """Resize keeping aspect ratio, pad to square. Returns (blob, scale, pad)."""
    h, w = img.shape[:2]
    scale = size / max(h, w)
    nh, nw = int(round(h * scale)), int(round(w * scale))
    resized = cv2.resize(img, (nw, nh))
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)   # gray pad
    pad_y, pad_x = (size - nh) // 2, (size - nw) // 2
    canvas[pad_y:pad_y + nh, pad_x:pad_x + nw] = resized
    blob = canvas[:, :, ::-1].transpose(2, 0, 1)             # BGR->RGB, HWC->CHW
    blob = np.ascontiguousarray(blob, dtype=np.float32) / 255.0
    return blob[None], scale, (pad_x, pad_y)


def decode_and_nms(output, scale, pad, conf=0.25, iou=0.45):
    """YOLOv8 output (1,84,8400) -> list of (cx,cy,w,h,score,cls) in ORIGINAL px."""
    pred = output[0].transpose(1, 0)                # (8400, 84) — the §7 transpose
    boxes = pred[:, :4].copy()                      # cx,cy,w,h in 640-space
    scores_all = pred[:, 4:]
    class_ids = scores_all.argmax(1)
    scores = scores_all.max(1)
    keep = scores > conf
    boxes, scores, class_ids = boxes[keep], scores[keep], class_ids[keep]
    if len(boxes) == 0:
        return []

    # NMS in top-left form.
    xywh = boxes.copy()
    xywh[:, 0] -= xywh[:, 2] / 2
    xywh[:, 1] -= xywh[:, 3] / 2
    idxs = cv2.dnn.NMSBoxes(xywh.tolist(), scores.tolist(), conf, iou)
    if len(idxs) == 0:
        return []
    idxs = np.array(idxs).flatten()

    results = []
    pad_x, pad_y = pad
    for i in idxs:
        cx, cy, bw, bh = boxes[i]
        # Undo the letterbox: subtract pad, divide by scale -> original image px.
        cx = (cx - pad_x) / scale
        cy = (cy - pad_y) / scale
        bw, bh = bw / scale, bh / scale
        results.append((cx, cy, bw, bh, float(scores[i]), int(class_ids[i])))
    return results


class DetectionNode(Node):
    def __init__(self) -> None:
        super().__init__("detection_node")
        self.bridge = CvBridge()

        # TODO 1: declare an "onnx_path" parameter (default "yolov8n.onnx") and read
        #         it, so the model is configurable from the launch file. Then build
        #         the runtime:  self.engine = OrtRuntime(onnx_path)
        onnx_path = "yolov8n.onnx"
        self.engine = OrtRuntime(onnx_path)

        self.input_size = 640

        # TODO 2: subscribe to "/camera/image_raw" with qos_profile_sensor_data.
        #         Using the DEFAULT (RELIABLE) QoS here is the Week 5 silent failure:
        #         the camera publishes BEST_EFFORT and you'd receive NOTHING.
        self.sub = self.create_subscription(
            Image, "/camera/image_raw", self.on_image, qos_profile_sensor_data
        )

        # TODO 3: create a publisher of Detection2DArray on "/detections" with
        #         qos_profile_sensor_data (match the consumer's expectation).
        self.pub = self.create_publisher(
            Detection2DArray, "/detections", qos_profile_sensor_data
        )

        self.get_logger().info(f"detection_node up, model={onnx_path}")

    def on_image(self, msg: Image) -> None:
        # TODO 4: capture the IMAGE's acquisition stamp and frame_id NOW, before any
        #         processing, and carry them onto the output. Stamping the output
        #         with self.get_clock().now() instead injects tens of ms of motion
        #         error downstream (Week 5 §3.1). This is the load-bearing line.
        acquired_stamp = msg.header.stamp
        frame_id = msg.header.frame_id

        img = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        blob, scale, pad = letterbox(img, self.input_size)

        raw = self.engine.infer(blob)
        detections = decode_and_nms(raw, scale, pad)

        out = Detection2DArray()
        out.header.stamp = acquired_stamp           # <- the acquisition stamp
        out.header.frame_id = frame_id
        for cx, cy, bw, bh, score, cls in detections:
            det = Detection2D()
            det.bbox.center.position.x = float(cx)
            det.bbox.center.position.y = float(cy)
            det.bbox.size_x = float(bw)
            det.bbox.size_y = float(bh)
            hyp = ObjectHypothesisWithPose()
            # TODO 5: set hyp.hypothesis.class_id (str) and hyp.hypothesis.score.
            hyp.hypothesis.class_id = str(cls)
            hyp.hypothesis.score = float(score)
            det.results.append(hyp)
            out.detections.append(det)

        # Publishing an EMPTY array when nothing is detected is correct and
        # graceful — downstream consumers see "no detections this frame", not a gap.
        self.pub.publish(out)


def main() -> None:
    rclpy.init()
    node = DetectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# What "done" looks like
# -----------------------------------------------------------------------------
#
#   $ ros2 topic info /detections -v
#   Type: vision_msgs/msg/Detection2DArray
#   Publisher count: 1
#     QoS profile:
#       Reliability: BEST_EFFORT      <- matches the camera class (Week 5)
#       Durability:  VOLATILE
#       History (Depth): KEEP_LAST (5)
#
#   $ ros2 topic echo /detections --once
#   header:
#     stamp: {sec: 1718000000, nanosec: ...}   <- equals the IMAGE stamp, not now()
#     frame_id: "camera_optical_frame"
#   detections:
#   - bbox: {center: {position: {x: 412.0, y: 233.0}}, size_x: 88.0, size_y: 140.0}
#     results:
#     - hypothesis: {class_id: "0", score: 0.91}      <- class 0 = person (COCO)
#
# The five TODOs are the only blanks. Everything else — the letterbox, the §7
# decode, the NMS, the rescale-to-original-pixels — is given and correct. The point
# of the exercise is to internalize WHY each TODO matters: QoS (or you get nothing),
# the acquisition stamp (or you lie about timing), the standard message (or nothing
# downstream understands you). Those three are the Week 5 lessons made load-bearing
# on a learned-perception node.
# -----------------------------------------------------------------------------
