import asyncio
import io
import os
import random
import subprocess
import time
import zlib
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import StudioConfig
from net import request, request_json
from text_utils import HAS_RAQM, for_pil

FONT_CANDIDATES = [
    "fonts/Cairo-Bold.ttf", "fonts/Cairo-SemiBold.ttf", "fonts/Cairo-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/amiri/Amiri-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
]


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


@lru_cache(maxsize=16)
def load_font(size: int):
    paths = ([StudioConfig.FONT_PATH] if StudioConfig.FONT_PATH else []) + \
            [str(StudioConfig.BASE_DIR / p) if not p.startswith("/") else p for p in FONT_CANDIDATES]
    engine = ImageFont.Layout.RAQM if HAS_RAQM else ImageFont.Layout.BASIC
    for p in paths:
        if p and os.path.exists(p):
            return ImageFont.truetype(p, size, layout_engine=engine)
    return ImageFont.load_default()


# ------------------------------------------------------------ خلفيات
def _motif(draw, motif, W, H, acc, rng):
    a = (*acc, 55)
    if motif == "grid":
        st = max(40, W // 24)
        for x in range(0, W, st):
            draw.line([(x, 0), (x, H)], fill=a, width=1)
        for y in range(0, H, st):
            draw.line([(0, y), (W, y)], fill=a, width=1)
    elif motif == "stars":
        for _ in range(180):
            x, y, r = rng.randint(0, W), rng.randint(0, H), rng.choice([1, 1, 2, 3])
            draw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, rng.randint(90, 230)))
    elif motif == "rays":
        import math
        cx, cy = rng.randint(W // 4, 3 * W // 4), rng.randint(H // 4, 3 * H // 4)
        for k in range(18):
            ang = k * math.pi / 9 + rng.random() * 0.1
            sp = 0.08
            R = max(W, H) * 1.5
            draw.polygon([(cx, cy), (cx + R * math.cos(ang - sp), cy + R * math.sin(ang - sp)),
                          (cx + R * math.cos(ang + sp), cy + R * math.sin(ang + sp))],
                         fill=(*acc, 28 if k % 2 else 0))
    elif motif == "dots":
        st = max(28, W // 32)
        for y in range(0, H, st):
            for x in range(0, W, st):
                r = st * 0.2 * (0.3 + y / H)
                draw.ellipse([x - r, y - r, x + r, y + r], fill=a)
    elif motif == "stripes":
        st = max(60, W // 16)
        for x in range(-H, W, st):
            draw.line([(x, H), (x + H, 0)], fill=a, width=st // 3)
    elif motif == "waves":
        import math
        for k in range(9):
            ph = rng.random() * 6
            pts = [(x, H * (0.1 + k * 0.1) + 30 * math.sin(x / 90 + ph + k)) for x in range(0, W + 20, 20)]
            draw.line(pts, fill=(*acc, 70), width=3)
    elif motif == "rings":
        cx, cy = rng.randint(0, W), rng.randint(0, H)
        for r in range(40, max(W, H), 70):
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*acc, 60), width=3)
    elif motif == "blocks":
        for _ in range(14):
            w, h = rng.randint(W // 12, W // 4), rng.randint(H // 10, H // 3)
            x, y = rng.randint(-20, W), rng.randint(-20, H)
            draw.rectangle([x, y, x + w, y + h], fill=(*acc, 40))
    elif motif == "lines":
        for k in range(6):
            y = rng.randint(0, H)
            draw.line([(0, y), (W, y)], fill=(*acc, 90), width=2)
    elif motif == "paper":
        for _ in range(8):
            x, y = rng.randint(0, W), rng.randint(0, H)
            draw.rectangle([x, y, x + rng.randint(100, 400), y + rng.randint(40, 160)], fill=(*acc, 22))


def make_background(style: dict, idx: int, size) -> Image.Image:
    W, H = size
    rng = random.Random(zlib.crc32(f"{style['name']}{idx}".encode()))
    c1, c2, acc = np.array(_hex(style["c1"])), np.array(_hex(style["c2"])), _hex(style["accent"])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    t = (xx / W * 0.4 + yy / H * 0.6) if idx % 2 == 0 else ((1 - xx / W) * 0.4 + yy / H * 0.6)
    arr = (c1[None, None, :] * (1 - t[..., None]) + c2[None, None, :] * t[..., None])
    if style["motif"] in ("noise", "paper"):
        arr = arr + np.random.default_rng(idx).normal(0, 7, (H, W, 1))
    img = Image.fromarray(np.clip(arr, 0, 255).astype("uint8")).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _motif(ImageDraw.Draw(layer), style["motif"], W, H, acc, rng)
    if style["motif"] in ("blocks", "rings", "waves"):
        layer = layer.filter(ImageFilter.GaussianBlur(1.2))
    return Image.alpha_composite(img, layer).convert("RGB")


def fit_cover(img: Image.Image, size) -> Image.Image:
    W, H = size
    s = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * s) + 1, int(img.height * s) + 1), Image.LANCZOS)
    l, t = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((l, t, l + W, t + H))


def darken_bottom(img: Image.Image) -> Image.Image:
    W, H = img.size
    g = np.zeros((H, W), dtype=np.uint8)
    start = int(H * 0.40)
    g[start:] = (np.linspace(0, 150, H - start)[:, None]).astype(np.uint8)
    return Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, Image.fromarray(g))


async def fetch_ai_image(prompt: str):
    """Replicate: إنشاء prediction ثم polling حتى succeeded ثم تنزيل الصورة."""
    token = StudioConfig.REPLICATE_API_TOKEN
    if not token:
        return None, "REPLICATE_API_TOKEN غير مضبوط"
    base = StudioConfig.REPLICATE_BASE_URL
    hdr = {"Authorization": f"Bearer {token}", "Prefer": "wait=30"}
    body = {"input": {"prompt": prompt, "aspect_ratio": "16:9", "output_format": "jpg"}}
    st, data = await request_json("POST", f"{base}/v1/models/{StudioConfig.REPLICATE_MODEL}/predictions",
                                  hdr, body, timeout=60)
    if st not in (200, 201):
        return None, f"Replicate HTTP {st}: {str(data)[:100]}"
    deadline = time.monotonic() + 120
    while data.get("status") not in ("succeeded", "failed", "canceled"):
        if time.monotonic() > deadline:
            return None, "Replicate timeout"
        await asyncio.sleep(StudioConfig.REPLICATE_POLL_SECONDS)
        st, data = await request_json("GET", data["urls"]["get"], hdr, timeout=30)
        if st != 200:
            return None, f"Replicate poll HTTP {st}"
    if data["status"] != "succeeded":
        return None, f"Replicate {data['status']}: {data.get('error')}"
    out = data.get("output")
    url = out[0] if isinstance(out, list) else out
    st, raw = await request("GET", url, timeout=60)
    if st != 200:
        return None, f"تنزيل الصورة HTTP {st}"
    return raw, ""


# ------------------------------------------------------------ نص
def _wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for w in text.split():
        trial = (cur + " " + w).strip()
        disp, kw = for_pil(trial)
        if cur and draw.textlength(disp, font=font, **kw) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def render_text_png(text: str, style: dict, size, dest: str):
    W, H = size
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fs = int(H * 0.075)
    while True:
        font = load_font(fs)
        lines = _wrap(d, text, font, W * 0.82)
        if len(lines) <= 3 or fs <= 28:
            break
        fs -= 4
    lh = int(fs * 1.5)
    y0 = H - lh * len(lines) - int(H * 0.09)
    txt, acc, c1 = _hex(style["text"]), _hex(style["accent"]), _hex(style["c1"])
    widths = [d.textlength(for_pil(l)[0], font=font, **for_pil(l)[1]) for l in lines]
    ts = style["tstyle"]
    if ts == "box":
        pad = int(fs * 0.45)
        d.rounded_rectangle([W / 2 - max(widths) / 2 - pad, y0 - pad / 2, W / 2 + max(widths) / 2 + pad,
                             y0 + lh * len(lines) + pad / 2 - fs * 0.2], radius=pad, fill=(*c1, 215))
    if ts == "glow":
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for i, l in enumerate(lines):
            disp, kw = for_pil(l)
            gd.text((W / 2, y0 + i * lh), disp, font=font, fill=(*acc, 255), anchor="ma", **kw)
        img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(fs * 0.22)))
        img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(fs * 0.07)))
        d = ImageDraw.Draw(img)
    for i, l in enumerate(lines):
        disp, kw = for_pil(l)
        pos = (W / 2, y0 + i * lh)
        if ts == "shadow":
            d.text((pos[0] + 3, pos[1] + 4), disp, font=font, fill=(0, 0, 0, 190), anchor="ma", **kw)
        if ts == "outline":
            d.text(pos, disp, font=font, fill=(*acc, 255), anchor="ma", stroke_width=max(3, fs // 9),
                   stroke_fill=(0, 0, 0, 255), **kw)
        else:
            d.text(pos, disp, font=font, fill=(*txt, 255), anchor="ma", **kw)
    img.save(dest)


# ------------------------------------------------------------ صوت
async def synth_voice(text: str, dest: str, rate: str = "+0%") -> bool:
    try:
        import edge_tts
    except ImportError:
        return False
    try:
        await asyncio.wait_for(edge_tts.Communicate(text, StudioConfig.TTS_VOICE, rate=rate).save(dest), 60)
        return os.path.exists(dest) and os.path.getsize(dest) > 500
    except Exception as e:
        print(f"[TTS] failed: {e}")
        return False


def probe_duration(path: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                          "default=nw=1:nk=1", path], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0
