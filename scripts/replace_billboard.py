"""
Replace the billboard content in a street photo with a provided overlay image.

This script detects the largest purple-ish quadrilateral (the billboard),
computes a perspective transform, warps the overlay onto that surface, and
exports both a master composite and a 1080x1920 Instagram Story version.

Usage (paths default to project data files if not provided):
  python3 scripts/replace_billboard.py \
      --background /absolute/path/to/1.jpeg \
      --overlay /absolute/path/to/2.png \
      --out-master /absolute/path/to/1_billboard_replaced.jpg \
      --out-story /absolute/path/to/1_billboard_story_1080x1920.jpg

Requires: opencv-python-headless, Pillow, numpy
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image, ImageFilter


Point = Tuple[float, float]


def order_points_clockwise(points: np.ndarray) -> np.ndarray:
    """Return points ordered as top-left, top-right, bottom-right, bottom-left.

    Args:
        points: Array of shape (4, 2)
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = points.sum(axis=1)
    rect[0] = points[np.argmin(s)]  # top-left
    rect[2] = points[np.argmax(s)]  # bottom-right

    diff = np.diff(points, axis=1)
    rect[1] = points[np.argmin(diff)]  # top-right
    rect[3] = points[np.argmax(diff)]  # bottom-left
    return rect


def approximate_quad_from_contour(contour: np.ndarray) -> np.ndarray | None:
    """Approximate a contour to a 4-point polygon if possible."""
    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
    if len(approx) == 4:
        return approx.reshape(4, 2).astype(np.float32)
    # Fallback to minimum area rectangle
    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    return box.astype(np.float32)


@dataclass
class DetectionResult:
    quad: np.ndarray  # 4x2 float32 ordered tl,tr,br,bl
    mask: np.ndarray  # binary mask of the billboard area


def detect_billboard_quad(image_bgr: np.ndarray) -> DetectionResult:
    """Detect the billboard as a large purple-ish quadrilateral.

    We use color thresholding in HSV to isolate the purple background,
    then choose the largest 4-point contour. Falls back to edge-based
    detection if no suitable purple region is found.
    """
    h, w = image_bgr.shape[:2]

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)

    # Purple range(s) in OpenCV HSV (0-180 for H). These ranges are broad
    # to capture the billboard's bright purple tone.
    lower1 = np.array([120, 40, 40])
    upper1 = np.array([165, 255, 255])
    mask_purple = cv2.inRange(hsv, lower1, upper1)

    # Clean up the mask
    kernel = np.ones((5, 5), np.uint8)
    mask_purple = cv2.morphologyEx(mask_purple, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask_purple = cv2.morphologyEx(mask_purple, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(
        mask_purple, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    candidates: List[Tuple[float, np.ndarray]] = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < (w * h) * 0.05:  # discard tiny areas
            continue
        quad = approximate_quad_from_contour(cnt)
        if quad is None or quad.shape[0] != 4:
            continue
        candidates.append((area, quad))

    if candidates:
        # Choose the largest area candidate; order its points
        best_quad = max(candidates, key=lambda x: x[0])[1]
        ordered = order_points_clockwise(best_quad)
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [ordered.astype(np.int32)], 255)
        return DetectionResult(quad=ordered.astype(np.float32), mask=mask)

    # Fallback: edge-based detection looking for the largest 4-point shape
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.dilate(edges, kernel, iterations=1)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < (w * h) * 0.05:
            continue
        quad = approximate_quad_from_contour(cnt)
        if quad is None or quad.shape[0] != 4:
            continue
        # Prefer regions near the top half (where the billboard is)
        cy = np.mean(quad[:, 1])
        score = area * (1.5 if cy < h * 0.65 else 1.0)
        candidates.append((score, quad))

    if not candidates:
        raise RuntimeError("Unable to detect a suitable billboard quadrilateral.")

    best_quad = max(candidates, key=lambda x: x[0])[1]
    ordered = order_points_clockwise(best_quad)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [ordered.astype(np.int32)], 255)
    return DetectionResult(quad=ordered.astype(np.float32), mask=mask)


def warp_overlay_to_quad(
    overlay_bgr: np.ndarray, target_shape: Tuple[int, int], quad_tl_tr_br_bl: np.ndarray
) -> np.ndarray:
    """Warp the overlay image into the target quadrilateral area.

    Returns a full-size image (same size as target) with the warped overlay.
    """
    h, w = target_shape
    src_h, src_w = overlay_bgr.shape[:2]
    src_pts = np.array(
        [[0, 0], [src_w - 1, 0], [src_w - 1, src_h - 1], [0, src_h - 1]],
        dtype=np.float32,
    )
    M = cv2.getPerspectiveTransform(src_pts, quad_tl_tr_br_bl.astype(np.float32))
    warped = cv2.warpPerspective(
        overlay_bgr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return warped


def composite_overlay(
    background_bgr: np.ndarray, warped_overlay_bgr: np.ndarray, mask: np.ndarray
) -> np.ndarray:
    """Composite the warped overlay onto the background using a soft mask."""
    mask_float = mask.astype(np.float32) / 255.0
    # Feather edges to blend better
    feather = cv2.GaussianBlur(mask_float, (21, 21), 10)
    feather = np.clip(feather, 0.0, 1.0)
    overlay = warped_overlay_bgr.astype(np.float32)
    background = background_bgr.astype(np.float32)
    composite = overlay * feather[..., None] + background * (1.0 - feather[..., None])
    return np.clip(composite, 0, 255).astype(np.uint8)


def export_story(image_bgr: np.ndarray, out_path: str) -> None:
    """Export an image as a 1080x1920 progressive JPEG with mild sharpening."""
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    im = Image.fromarray(rgb)
    im = im.resize((1080, 1920), Image.Resampling.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=130, threshold=3))
    im.save(
        out_path,
        format="JPEG",
        quality=92,
        subsampling=1,
        optimize=True,
        progressive=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replace billboard image with overlay."
    )
    parser.add_argument(
        "--background", default="/Users/cornel/workspace/mulai_web/data/1.jpeg"
    )
    parser.add_argument(
        "--overlay", default="/Users/cornel/workspace/mulai_web/data/2.png"
    )
    parser.add_argument(
        "--out-master",
        default="/Users/cornel/workspace/mulai_web/data/1_billboard_replaced.jpg",
    )
    parser.add_argument(
        "--out-story",
        default="/Users/cornel/workspace/mulai_web/data/1_billboard_story_1080x1920.jpg",
    )
    args = parser.parse_args()

    bg = cv2.imread(args.background, cv2.IMREAD_COLOR)
    if bg is None:
        raise FileNotFoundError(f"Background not found: {args.background}")
    ov = cv2.imread(args.overlay, cv2.IMREAD_COLOR)
    if ov is None:
        raise FileNotFoundError(f"Overlay not found: {args.overlay}")

    detection = detect_billboard_quad(bg)
    warped = warp_overlay_to_quad(ov, (bg.shape[0], bg.shape[1]), detection.quad)
    composite = composite_overlay(bg, warped, detection.mask)

    # Slight contrast boost for realism
    lab = cv2.cvtColor(composite, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.equalizeHist(l)
    lab = cv2.merge((l, a, b))
    composite = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    cv2.imwrite(args.out_master, composite, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

    export_story(composite, args.out_story)


if __name__ == "__main__":
    main()
