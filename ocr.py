"""Lightweight, CPU-only OCR for scans and phone photos (optional; the app works without it).

    OCR_BACKEND = auto | rapidocr | tesseract | none        (default: auto)

    rapidocr   RapidOCR (PaddleOCR PP-OCRv4 models run by onnxruntime): `pip install -r requirements-ocr.txt`, about
               16 MB of models bundled in the wheel, about 70 MB extra RAM once loaded. The default.
    tesseract  pytesseract + the `tesseract` binary (apt install tesseract-ocr). Used by `auto` only when RapidOCR is
               not installed.
    none       switch the lightweight OCR off (an installed Docling still OCRs, see core.scan_text).

The engine is created on first use (not at import), one page is processed at a time under a lock, and big photos are
shrunk first so a 12-megapixel phone picture cannot blow the memory budget of a 512 MB host.

Public API: backend(), available(), label(), read_pages(pngs) -> (text, mean confidence 0-1 or None).
"""
from __future__ import annotations

import importlib.util
import io
import os
import re
import shutil
import threading
from typing import List, Optional, Tuple

BACKENDS = ("rapidocr", "tesseract")
# Detector memory grows with the pixel count (about 135 MB per megapixel), so pages are shrunk to a pixel budget
# before OCR: ~1 MP keeps the whole process under ~350 MB. Raise OCR_MAX_PIXELS on a machine with more RAM.
MAX_PIXELS = int(float(os.getenv("OCR_MAX_PIXELS", "1000000")))
MAX_SIDE = int(os.getenv("OCR_MAX_SIDE", "1800"))      # ... and the longest side stays under this many pixels
LABELS = {"rapidocr": "RapidOCR", "tesseract": "Tesseract", "none": "off"}

Box = Tuple[float, float, float, float, str, float]   # x0, y0, x1, y1, text, score

_engine = None
_lock = threading.Lock()


# ---------------------------------------------------------------- backend selection
def _choice() -> str:
    want = os.getenv("OCR_BACKEND", "auto").strip().lower()
    return want if want in BACKENDS + ("none",) else "auto"


def _ready(name: str) -> bool:
    if name == "rapidocr":
        return importlib.util.find_spec("rapidocr_onnxruntime") is not None
    return importlib.util.find_spec("pytesseract") is not None and shutil.which("tesseract") is not None


def backend() -> str:
    """The OCR engine that will be used: 'rapidocr', 'tesseract' or 'none' (switched off or nothing installed)."""
    want = _choice()
    if want == "none":
        return "none"
    return next((b for b in ((want,) if want in BACKENDS else BACKENDS) if _ready(b)), "none")


def available() -> bool:
    return backend() != "none"


def label() -> str:
    return LABELS[backend()]


# ---------------------------------------------------------------- text from boxes
_RESPACE = [
    (re.compile(r"(?<=[a-z]{2})(?=[A-Z][a-z])"), " "),       # PierRoad       -> Pier Road (McDonald, eBay stay)
    (re.compile(r"(?<=\d)(?=[A-Za-z]{2})"), " "),            # 1Clam, 7:48PM  -> 1 Clam, 7:48 PM
    (re.compile(r"(?<=[,:;!?])(?=[A-Za-z])"), " "),          # Server:Dana    -> Server: Dana
    (re.compile(r"(?<=\b\d),(?=\d{4}\b)|(?<=\b\d\d),(?=\d{4}\b)"), ", "),   # Jun 21,2025 -> Jun 21, 2025
]


def respace(text: str) -> str:
    """The bundled PaddleOCR recogniser often drops the spaces between words ('Clam Chowder' fine, 'PierRoad' not).
    Put back the ones that are safe to infer; an LLM reading the text repairs the rest."""
    for rx, rep in _RESPACE:
        text = rx.sub(rep, text)
    return text


def boxes_to_text(boxes: List[Box]) -> str:
    """Group detected text boxes into reading-order rows: boxes whose vertical centres agree share a line, ordered
    left to right; a wide horizontal gap becomes three spaces (a table column), which is the layout the heuristic
    parser and the model prompt expect from a text-layer PDF."""
    boxes = [b for b in boxes if b[4].strip()]
    if not boxes:
        return ""
    heights = sorted(b[3] - b[1] for b in boxes)
    med = max(heights[len(heights) // 2], 1.0)
    rows: List[List[Box]] = []
    centres: List[float] = []
    for b in sorted(boxes, key=lambda b: (b[1] + b[3]) / 2):
        yc = (b[1] + b[3]) / 2
        if rows and abs(yc - centres[-1]) <= 0.6 * med:
            rows[-1].append(b)
            centres[-1] = sum((x[1] + x[3]) / 2 for x in rows[-1]) / len(rows[-1])
        else:
            rows.append([b])
            centres.append(yc)
    lines = []
    for row in rows:
        row.sort(key=lambda b: b[0])
        line = row[0][4].strip()
        for prev, b in zip(row, row[1:]):
            line += ("   " if b[0] - prev[2] > 1.2 * med else " ") + b[4].strip()
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------- engines
def _load_image(png: bytes):
    """PIL RGB image, shrunk so its longest side is at most MAX_SIDE."""
    from PIL import Image, ImageOps
    img = Image.open(io.BytesIO(png))
    k = _scale(img.size)
    if k < 1:
        img.draft("RGB", (round(img.width * k), round(img.height * k)))    # JPEG: decode at 1/2, 1/4 or 1/8 size
    img = ImageOps.exif_transpose(img).convert("RGB")
    k = _scale(img.size)
    if k < 1:
        img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)
    return img


def _scale(size) -> float:
    """Factor (<= 1) that brings an image inside both the pixel budget and the longest-side limit."""
    w, h = size
    return min(1.0, MAX_SIDE / max(w, h), (MAX_PIXELS / (w * h)) ** 0.5)


def _no_mem_pattern() -> None:
    """onnxruntime's memory-pattern cache keeps a plan per input shape and made peak RSS creep up by 60-90 MB on
    every later page of a different size (measured). Switching it off keeps the peak flat for a small speed cost.
    Best effort: it patches a private helper of the pinned rapidocr-onnxruntime and is skipped if that moves."""
    try:
        from rapidocr_onnxruntime.utils import infer_engine
        make = infer_engine.OrtInferSession._init_sess_opts

        def patched(config):
            opts = make(config)
            opts.enable_mem_pattern = False
            return opts
        infer_engine.OrtInferSession._init_sess_opts = staticmethod(patched)
    except Exception:
        pass


def _rapidocr_boxes(img) -> List[Box]:
    global _engine
    import numpy as np
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _no_mem_pattern()
        threads = int(os.getenv("OCR_THREADS") or min(4, os.cpu_count() or 1))
        _engine = RapidOCR(intra_op_num_threads=threads, inter_op_num_threads=1)
    result, _ = _engine(np.ascontiguousarray(np.asarray(img)[:, :, ::-1]))      # RGB -> BGR
    out: List[Box] = []
    for pts, text, score in result or []:
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        out.append((min(xs), min(ys), max(xs), max(ys), respace(str(text)), float(score)))
    return out


def _tesseract_boxes(img) -> List[Box]:
    import pytesseract
    d = pytesseract.image_to_data(img, lang=os.getenv("OCR_LANG", "eng"), output_type=pytesseract.Output.DICT)
    out: List[Box] = []
    for i, text in enumerate(d["text"]):
        try:
            conf = float(d["conf"][i])
        except (TypeError, ValueError):
            continue
        if text.strip() and conf >= 0:
            x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
            out.append((x, y, x + w, y + h, text, conf / 100))
    return out


def read_pages(pngs: List[bytes]) -> Tuple[str, Optional[float]]:
    """OCR page images (PNG bytes) one at a time. Returns (text, mean confidence of the recognised text, or None if
    nothing was recognised). Raises RuntimeError when no OCR backend is available."""
    which = backend()
    if which == "none":
        raise RuntimeError("no OCR backend available")
    read = _rapidocr_boxes if which == "rapidocr" else _tesseract_boxes
    texts, scores = [], []
    with _lock:                                       # one page at a time, across all sessions
        for png in pngs:
            boxes = read(_load_image(png))
            texts.append(boxes_to_text(boxes))
            scores += [b[5] for b in boxes]
    return "\n".join(t for t in texts if t), (round(sum(scores) / len(scores), 3) if scores else None)
