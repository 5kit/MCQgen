"""
Renders $...$ math segments (matplotlib "mathtext" - a LaTeX-like subset, no
full LaTeX/TeX install required) mixed with plain text into small transparent
images, for display inside customtkinter widgets that can't render math natively.

Usage pattern in the rest of the app:
    if contains_math(line):
        img = render_line_image(line, fontsize=15, color="#DCE4EE")
        # img is a CTkImage, or None if the LaTeX failed to parse
    else:
        # display `line` as normal text, no change needed

For a full block of text (e.g. a question with multiple statements on
separate lines), use build_multiline_display() which handles the
line-by-line math/plain-text decision and returns a ready-to-pack frame.
"""

import io
import re
from functools import lru_cache

import matplotlib
matplotlib.use("Agg")  # headless backend - required, and must be set before pyplot import
import matplotlib.pyplot as plt
from PIL import Image

import customtkinter as ctk

_MATH_PATTERN = re.compile(r'\$[^$\n]+\$')

_BASE_DPI = 110
_SCALE = 2  # render at 2x then downscale on display for crisper anti-aliased text


def contains_math(text):
    """True if the text has at least one $...$ segment worth rendering as math."""
    return bool(_MATH_PATTERN.search(text or ""))


@lru_cache(maxsize=512)
def _render_pil(text, fontsize, color):
    """Render one line of (possibly mixed plain-text + $...$ mathtext) text to a
    tightly-cropped, transparent PIL image. Cached, since the same question/option
    text gets re-rendered every time the quiz UI redraws (e.g. after every click)."""
    dpi = _BASE_DPI * _SCALE

    # First pass: throwaway figure just to measure the rendered text's bounding box.
    probe_fig = plt.figure(figsize=(0.1, 0.1), dpi=dpi)
    probe_fig.patch.set_alpha(0)
    try:
        artist = probe_fig.text(0, 0, text, fontsize=fontsize, color=color)
        probe_fig.canvas.draw()
        bbox = artist.get_window_extent()
        width_in = bbox.width / dpi + 0.2
        height_in = bbox.height / dpi + 0.12
    finally:
        plt.close(probe_fig)

    # Second pass: a figure sized to fit the text tightly, then save to PNG bytes.
    fig = plt.figure(figsize=(max(width_in, 0.2), max(height_in, 0.2)), dpi=dpi)
    fig.patch.set_alpha(0)
    fig.text(0.015, 0.18, text, fontsize=fontsize, color=color)
    buf = io.BytesIO()
    try:
        fig.savefig(buf, format="png", transparent=True)
    finally:
        plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


def render_line_image(text, fontsize=15, color="#DCE4EE"):
    """Render a line of text to a CTkImage. Returns None if the LaTeX/mathtext
    failed to parse (e.g. an unsupported command), so the caller can fall back
    to plain text instead of crashing."""
    try:
        pil_img = _render_pil(text, fontsize, color)
    except Exception:
        return None

    display_size = (pil_img.width / _SCALE, pil_img.height / _SCALE)
    return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=display_size)


def build_multiline_display(parent, text, fontsize=14, font_weight="normal",
                             text_color="#DCE4EE", wraplength=800, justify="left"):
    """Build a transparent container frame with one row per line of `text`.
    Lines containing $...$ are rendered as math images; plain lines are shown
    as normal wrapped CTkLabels (so plain quiz content pays no rendering cost).

    Returns the container frame, ready to .pack()/.grid(). The frame holds its
    own reference to any CTkImages it created (container.math_image_refs) so
    they aren't garbage-collected while the frame is on screen - the caller
    doesn't need to do anything extra, just don't discard the returned frame
    until you're done with it (destroy() is fine, that's normal cleanup).
    """
    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.math_image_refs = []

    lines = text.split("\n") if text else [""]
    font = ctk.CTkFont(size=fontsize, weight=font_weight)

    for line in lines:
        if contains_math(line):
            img = render_line_image(line, fontsize=fontsize, color=text_color)
            if img is not None:
                lbl = ctk.CTkLabel(container, image=img, text="")
                lbl.pack(anchor="w", pady=1)
                container.math_image_refs.append(img)
                continue
            # fall through to plain text if rendering failed

        ctk.CTkLabel(
            container, text=line, font=font, text_color=text_color,
            wraplength=wraplength, justify=justify, anchor="w"
        ).pack(anchor="w", fill="x", pady=1)

    return container
