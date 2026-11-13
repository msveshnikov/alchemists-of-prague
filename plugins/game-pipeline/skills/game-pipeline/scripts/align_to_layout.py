"""Align a painted image (e.g. a ChatGPT map) to the layout render it was painted from.

    python align_to_layout.py painted.png layout.png out.png [--landmarks x,y x,y ...]

Both images show the same area with the same framing (the painting is a repaint of the layout).
The painting is warped (affine) so its edges match the layout's edges: OpenCV ECC on blurred gradient
maps, coarse to fine. Optional --landmarks (pixel spots in the painting, e.g. bridge ends, fortress
corners) first estimate a robust affine from local patch matches, which helps when ECC alone drifts.
Prints the edge-correlation score before and after; keep the result only if it went up, then check an
edge overlay by eye. Output keeps the painting's size; borders are mirrored, not smeared.
Requires: pip install numpy opencv-python
"""
import sys

import cv2
import numpy as np


def grad(im, blur=2.0):
    g = cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), blur)
    return cv2.magnitude(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))


def score(a, r, mask):
    return float(np.corrcoef(grad(a)[mask], grad(r)[mask])[0, 1])


def landmark_affine(art, ref, pts, radius=70, search=30):
    a, r = grad(art), grad(ref)
    src, dst = [], []
    for x, y in pts:
        pa = a[y - radius:y + radius, x - radius:x + radius]
        best = None
        for dy in range(-search, search + 1):
            for dx in range(-search, search + 1):
                pr = r[y - radius + dy:y + radius + dy, x - radius + dx:x + radius + dx]
                if pr.shape != pa.shape:
                    continue
                c = np.corrcoef(pa.ravel(), pr.ravel())[0, 1]
                if best is None or c > best[0]:
                    best = (c, dx, dy)
        if best:
            src.append((x, y)); dst.append((x + best[1], y + best[2]))
            print(f"landmark ({x},{y}) offset {best[1]:+d},{best[2]:+d} corr {best[0]:.2f}")
    m, inl = cv2.estimateAffine2D(np.float32(src), np.float32(dst), ransacReprojThreshold=8)
    print("landmark affine inliers", int(inl.sum()), "/", len(src))
    return cv2.warpAffine(art, m, (art.shape[1], art.shape[0]), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT101)


def ecc_refine(art, ref, mask):
    warp, ok = np.eye(2, 3, dtype=np.float32), False
    m8 = mask.astype(np.uint8) * 255      # ignore the outer band (mirrored borders would attract ECC)
    for sig in (8, 4, 2):
        pp = lambda im: cv2.GaussianBlur(grad(im), (0, 0), sig)
        try:
            cc, warp = cv2.findTransformECC(pp(ref), pp(art), warp, cv2.MOTION_AFFINE,
                                            (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), m8, 1)
            ok = True
            print(f"ECC blur {sig}: cc {cc:.3f}")
        except cv2.error:
            print(f"ECC blur {sig}: no convergence")
    if not ok:
        return art
    print("ECC affine:\n", np.round(warp, 4))
    return cv2.warpAffine(art, warp, (art.shape[1], art.shape[0]),
                          flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT101)


def main():
    args = sys.argv[1:]
    if len(args) < 3:
        sys.exit(__doc__)
    art, ref = cv2.imread(args[0]), cv2.imread(args[1])
    w, h = art.shape[1], art.shape[0]
    ref = cv2.resize(ref, (w, h), interpolation=cv2.INTER_AREA)
    mask = np.zeros((h, w), bool); mask[h // 16:-h // 16, w // 32:-w // 32] = True
    print(f"before: {score(art, ref, mask):.4f}")
    out, best = art, score(art, ref, mask)
    if "--landmarks" in args:
        pts = [tuple(int(v) for v in p.split(",")) for p in args[args.index("--landmarks") + 1:]]
        cand = landmark_affine(out, ref, pts)
        s = score(cand, ref, mask)
        print(f"after landmarks: {s:.4f}" + ("" if s > best else "  (worse, dropped)"))
        if s > best:
            out, best = cand, s
    cand = ecc_refine(out, ref, mask)
    s = score(cand, ref, mask)
    print(f"after ECC: {s:.4f}" + ("" if s > best else "  (worse, dropped)"))
    if s > best:
        out, best = cand, s
    print(f"final: {best:.4f}")
    cv2.imwrite(args[2], out)


if __name__ == "__main__":
    main()
