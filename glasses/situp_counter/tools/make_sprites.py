#!/usr/bin/env python3
"""Generate the Sit-up Counter animation sprites.

Writes ../sprites.h (4-bit indexed images for the glasses) and, when the phone
plugin sits in the usual place, PNG previews for its style picker.

Requires Pillow:  py -m pip install pillow
Run from anywhere:  py GlassSDK/examples/situp_counter/tools/make_sprites.py
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
OUT_HEADER = HERE.parent / "sprites.h"
PHONE_PREVIEWS = HERE.parents[3] / "PhoneSDK" / "examples" / "situp-tracker" / "img"
SS = 4  # supersampling factor for smooth edges

# Gray levels used in the art (0 = transparent black, 255 = brightest)
SKIN, SKIN_EDGE, BAND, DETAIL, BODY, MAT, SWEAT = 120, 230, 255, 25, 90, 70, 200


def finish(img_l, size):
    """Downsample a supersampled grayscale canvas to the final size."""
    return img_l.resize(size, Image.LANCZOS)


# ------------------------------------------------------------------ head --
HEAD_W, HEAD_H = 144, 152
HEAD_TILT_FRAMES = 11   # keeps the glasses package under its install size limit
REST_ANGLE = 18


def draw_head_layer(expression, tier=0):
    """Side-profile head facing right, drawn unrotated on a supersampled
    canvas. tier 0 = normal coach; 1 = jawline + shades; 2 = swole;
    3 = ascended. Returns (L image, neck pivot)."""
    S = SS
    img = Image.new("L", (HEAD_W * S, HEAD_H * S), 0)
    d = ImageDraw.Draw(img)
    cx, cy, r = 74 * S, 72 * S, 40 * S

    # Headband tails flying out the back
    d.polygon([(cx - 30 * S, cy - 20 * S), (cx - 54 * S, cy - 8 * S),
               (cx - 50 * S, cy + 2 * S), (cx - 30 * S, cy - 8 * S)], fill=BAND)
    d.polygon([(cx - 32 * S, cy - 14 * S), (cx - 52 * S, cy + 12 * S),
               (cx - 45 * S, cy + 16 * S), (cx - 30 * S, cy - 4 * S)], fill=200)

    # Skull, jaw and nose: all outlines first, then all fills, so the
    # shapes merge into one silhouette without inner edges.
    skull = [cx - r, cy - r, cx + r, cy + r]
    jaw = [cx - 10 * S, cy + 8 * S, cx + 42 * S, cy + 46 * S]
    if tier >= 1:  # chiseled: a big square jaw
        jaw = [cx - 14 * S, cy + 4 * S, cx + 46 * S, cy + 52 * S]
    nose = [(cx + 34 * S, cy - 6 * S), (cx + 51 * S, cy + 11 * S), (cx + 34 * S, cy + 16 * S)]
    e = 3 * S
    d.ellipse(skull, fill=SKIN_EDGE)
    jaw_shape = (lambda box, **kw: d.rounded_rectangle(box, radius=10 * S, **kw)) \
        if tier >= 1 else d.ellipse
    jaw_shape(jaw, fill=SKIN_EDGE)
    d.polygon(nose, fill=SKIN_EDGE)
    d.ellipse([skull[0] + e, skull[1] + e, skull[2] - e, skull[3] - e], fill=SKIN)
    jaw_shape([jaw[0] + e, jaw[1] + e, jaw[2] - e, jaw[3] - e], fill=SKIN)
    d.polygon([(cx + 33 * S, cy - 2 * S), (cx + 46 * S, cy + 10 * S),
               (cx + 33 * S, cy + 12 * S)], fill=SKIN)
    # Ear
    d.ellipse([cx - 12 * S, cy - 2 * S, cx + 2 * S, cy + 18 * S], fill=SKIN_EDGE)
    d.ellipse([cx - 9 * S, cy + 2 * S, cx - 1 * S, cy + 14 * S], fill=SKIN)

    # Headband across the forehead
    d.polygon([(cx - 36 * S, cy - 26 * S), (cx + 30 * S, cy - 30 * S),
               (cx + 36 * S, cy - 18 * S), (cx - 32 * S, cy - 12 * S)], fill=BAND)

    ex, ey = cx + 22 * S, cy - 4 * S  # eye position
    w = 3 * S
    if tier >= 3:  # halo hovering over the head, tilts along with it
        d.ellipse([cx - 22 * S, cy - r - 14 * S, cx + 26 * S, cy - r - 2 * S], outline=255, width=3 * S)
    if tier >= 1 and expression != "sleepy":
        # Shades replace the eye; tier 3's lenses glow.
        lens = 255 if tier >= 3 else DETAIL
        d.rounded_rectangle([ex - 12 * S, ey - 7 * S, ex + 10 * S, ey + 7 * S], radius=4 * S, fill=lens)
        d.line([(ex - 34 * S, ey - 4 * S), (ex - 12 * S, ey - 2 * S)], fill=DETAIL, width=w)
        if expression == "effort":
            d.rounded_rectangle([cx + 12 * S, cy + 23 * S, cx + 38 * S, cy + 34 * S], radius=3 * S, fill=245)
            d.line([(cx + 12 * S, cy + 28 * S), (cx + 38 * S, cy + 28 * S)], fill=DETAIL, width=S * 2)
        elif expression == "happy":
            d.chord([cx + 8 * S, cy + 16 * S, cx + 40 * S, cy + 42 * S], 0, 180, fill=DETAIL)
            d.chord([cx + 12 * S, cy + 26 * S, cx + 36 * S, cy + 40 * S], 20, 160, fill=200)
        else:  # confident smirk
            d.line([(cx + 14 * S, cy + 32 * S), (cx + 36 * S, cy + 28 * S)], fill=DETAIL, width=w)
        return img, (cx - 4 * S, cy + 42 * S)
    if expression == "neutral":
        d.ellipse([ex - 5 * S, ey - 5 * S, ex + 5 * S, ey + 5 * S], fill=255)
        d.ellipse([ex - 1 * S, ey - 4 * S, ex + 6 * S, ey + 4 * S], fill=DETAIL)
        d.line([(cx + 12 * S, cy + 28 * S), (cx + 32 * S, cy + 26 * S)], fill=DETAIL, width=w)
    elif expression == "effort":
        # squeezed eye ">" and gritted teeth, sweat drop
        d.line([(ex - 6 * S, ey - 6 * S), (ex + 4 * S, ey), (ex - 6 * S, ey + 5 * S)],
               fill=DETAIL, width=w, joint="curve")
        d.rounded_rectangle([cx + 12 * S, cy + 21 * S, cx + 36 * S, cy + 32 * S],
                            radius=3 * S, fill=245)
        d.line([(cx + 12 * S, cy + 26 * S), (cx + 36 * S, cy + 26 * S)], fill=DETAIL, width=S * 2)
        for x in (19, 26, 32):
            d.line([(cx + x * S, cy + 21 * S), (cx + x * S, cy + 32 * S)], fill=DETAIL, width=S * 2)
    elif expression == "happy":
        d.arc([ex - 7 * S, ey - 4 * S, ex + 7 * S, ey + 8 * S], 200, 340, fill=DETAIL, width=w)
        d.chord([cx + 8 * S, cy + 12 * S, cx + 38 * S, cy + 38 * S], 0, 180, fill=DETAIL)
        d.chord([cx + 12 * S, cy + 22 * S, cx + 34 * S, cy + 36 * S], 20, 160, fill=200)
    elif expression == "sleepy":
        d.arc([ex - 7 * S, ey - 8 * S, ex + 7 * S, ey + 4 * S], 20, 160, fill=DETAIL, width=w)
        d.ellipse([cx + 20 * S, cy + 24 * S, cx + 28 * S, cy + 32 * S], fill=DETAIL)
    return img, (cx - 4 * S, cy + 42 * S)


def draw_shoulders(tier=0):
    S = SS
    img = Image.new("L", (HEAD_W * S, HEAD_H * S), 0)
    d = ImageDraw.Draw(img)
    if tier >= 3:  # radiant rays behind everything
        ox, oy = 70 * S, 72 * S
        for k in range(12):
            a = math.radians(k * 30 + 15)
            d.line([(ox + 54 * S * math.cos(a), oy + 50 * S * math.sin(a)),
                    (ox + 68 * S * math.cos(a), oy + 60 * S * math.sin(a))], fill=70, width=4 * S)
    if tier >= 2:  # swole: huge traps up to the ears
        d.polygon([(10 * S, 172 * S), (20 * S, 116 * S), (58 * S, 96 * S), (86 * S, 96 * S),
                   (130 * S, 116 * S), (142 * S, 172 * S)], fill=SKIN_EDGE)
        d.polygon([(14 * S, 172 * S), (24 * S, 119 * S), (59 * S, 100 * S), (85 * S, 100 * S),
                   (127 * S, 119 * S), (138 * S, 172 * S)], fill=BODY)
        d.rounded_rectangle([52 * S, 98 * S, 88 * S, 124 * S], radius=8 * S, fill=SKIN)  # thick neck
        return img
    d.rounded_rectangle([36 * S, 116 * S, 118 * S, 172 * S], radius=26 * S, fill=SKIN_EDGE)
    d.rounded_rectangle([39 * S, 119 * S, 115 * S, 172 * S], radius=24 * S, fill=BODY)
    d.rounded_rectangle([58 * S, 104 * S, 82 * S, 124 * S], radius=6 * S, fill=SKIN)  # neck
    return img


def head_frame(angle, expression, zz=False, sparkle=False, tier=0):
    base = draw_shoulders(tier)
    layer, pivot = draw_head_layer(expression, tier)
    rotated = layer.rotate(angle, resample=Image.BICUBIC, center=pivot)
    mask = rotated.point(lambda v: 255 if v > 0 else 0)
    base.paste(rotated, (0, 0), mask)
    d = ImageDraw.Draw(base)
    S = SS
    if expression == "effort":  # sweat drop, drawn upright after the tilt
        sx, sy = 126 * S, 26 * S
        d.ellipse([sx - 5 * S, sy, sx + 5 * S, sy + 10 * S], fill=SWEAT)
        d.polygon([(sx - 4 * S, sy + 3 * S), (sx, sy - 8 * S), (sx + 4 * S, sy + 3 * S)], fill=SWEAT)
    if zz:
        d.text((110 * S, 20 * S), "z", fill=230, font_size=22 * S)
        d.text((126 * S, 12 * S), "z", fill=160, font_size=15 * S)
    if sparkle:
        for (x, y, s) in ((118, 26, 9), (22, 30, 6), (134, 56, 5)):
            star(d, x * S, y * S, s * S)
    return finish(base, (HEAD_W, HEAD_H))


def star(d, x, y, s):
    d.polygon([(x, y - s), (x + s * 0.3, y - s * 0.3), (x + s, y), (x + s * 0.3, y + s * 0.3),
               (x, y + s), (x - s * 0.3, y + s * 0.3), (x - s, y), (x - s * 0.3, y - s * 0.3)],
              fill=255)


def head_frames(tier=0):
    frames = []
    for i in range(HEAD_TILT_FRAMES):
        p = i / (HEAD_TILT_FRAMES - 1)
        angle = REST_ANGLE - p * 48  # leaning back -> curling forward
        frames.append(head_frame(angle, "effort" if p >= 0.5 else "neutral", tier=tier))
    # Rep done / paused: same pose as frame 0, so the swap is seamless.
    frames.append(head_frame(REST_ANGLE, "happy", sparkle=True, tier=tier))
    frames.append(head_frame(REST_ANGLE, "sleepy", zz=True, tier=tier))
    return frames


# ---------------------------------------------------------------- aura --
def aura_frames(figs):
    """The stick figure wrapped in a soft glowing aura."""
    out = []
    for f in figs:
        mask = f.point(lambda v: 255 if v > 30 else 0)
        glow = mask.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(4))
        glow = glow.point(lambda v: int(v * 0.42))
        out.append(Image.composite(f, glow, mask))
    return out


# ----------------------------------------------------------------- cat --
CAT_W, CAT_H = 140, 140
FUR, FUR_EDGE = 110, 225


def cat_frame(eyes="meh", nod=0, extra=None):
    """Original sitting cat, front view. eyes: meh | up | blink | stare | happy."""
    S = SS
    img = Image.new("L", (CAT_W * S, CAT_H * S), 0)
    d = ImageDraw.Draw(img)
    e = 3 * S
    # tail curling round the front
    d.arc([60 * S, 96 * S, 136 * S, 138 * S], 180, 330, fill=FUR_EDGE, width=10 * S)
    d.arc([60 * S, 96 * S, 136 * S, 138 * S], 182, 328, fill=FUR, width=4 * S)
    body = [24 * S, 66 * S, 116 * S, 138 * S]
    d.ellipse(body, fill=FUR_EDGE)
    d.ellipse([body[0] + e, body[1] + e, body[2] - e, body[3] - e], fill=FUR)
    d.ellipse([52 * S, 84 * S, 88 * S, 132 * S], fill=150)  # chest
    hy = nod * S
    cx, cy, r = 70 * S, 52 * S + hy, 36 * S
    for side in (-1, 1):  # ears
        tip = (cx + side * 30 * S, cy - 46 * S)
        d.polygon([(cx + side * 8 * S, cy - 28 * S), tip, (cx + side * 36 * S, cy - 4 * S)], fill=FUR_EDGE)
        d.polygon([(cx + side * 12 * S, cy - 24 * S), (tip[0] - side * 2 * S, tip[1] + 8 * S),
                   (cx + side * 31 * S, cy - 6 * S)], fill=170)
    d.ellipse([cx - r, cy - r, cx + r, cy + r * 0.9], fill=FUR_EDGE)
    d.ellipse([cx - r + e, cy - r + e, cx + r - e, cy + r * 0.9 - e], fill=FUR)
    # eyes
    for side in (-1, 1):
        ex, ey = cx + side * 15 * S, cy - 2 * S
        if eyes in ("blink", "happy"):
            d.arc([ex - 9 * S, ey - 6 * S, ex + 9 * S, ey + 6 * S], 20 if eyes == "blink" else 200,
                  160 if eyes == "blink" else 340, fill=DETAIL, width=3 * S)
            continue
        rad = 10 * S if eyes == "stare" else 9 * S
        d.ellipse([ex - rad, ey - rad, ex + rad, ey + rad], fill=235)
        py = -4 * S if eyes == "up" else 0
        pr = 3 * S if eyes == "stare" else 4 * S
        d.ellipse([ex - pr, ey - pr * 1.6 + py, ex + pr, ey + pr * 1.6 + py], fill=DETAIL)
        if eyes in ("meh", "up"):  # heavy, unimpressed upper lid
            d.rectangle([ex - rad - S, ey - rad - S, ex + rad + S, ey - 1 * S], fill=FUR)
            d.line([(ex - rad, ey - 1 * S), (ex + rad, ey - 1 * S)], fill=DETAIL, width=3 * S)
    # nose + mouth
    d.polygon([(cx - 4 * S, cy + 10 * S), (cx + 4 * S, cy + 10 * S), (cx, cy + 15 * S)], fill=230)
    if eyes == "happy":
        d.arc([cx - 10 * S, cy + 10 * S, cx, cy + 20 * S], 0, 180, fill=DETAIL, width=2 * S)
        d.arc([cx, cy + 10 * S, cx + 10 * S, cy + 20 * S], 0, 180, fill=DETAIL, width=2 * S)
    else:
        d.line([(cx - 7 * S, cy + 20 * S), (cx + 7 * S, cy + 20 * S)], fill=DETAIL, width=2 * S)
    for side in (-1, 1):  # whiskers
        for k in (-1, 1):
            d.line([(cx + side * 22 * S, cy + 12 * S), (cx + side * 46 * S, cy + (12 + k * 5) * S)],
                   fill=200, width=S)
    if extra == "dots":
        for k in range(3):
            d.ellipse([(100 + k * 10) * S, 8 * S, (106 + k * 10) * S, 14 * S], fill=230)
    if extra == "bang":
        d.rectangle([110 * S, 4 * S, 116 * S, 22 * S], fill=255)
        d.rectangle([110 * S, 26 * S, 116 * S, 32 * S], fill=255)
    return finish(img, (CAT_W, CAT_H))


def cat_frames():
    # 0 unimpressed, 1 watching you (eyes up) -- the two "tilt" steps;
    # 2 slow blink (rep done), 3 judging stare (paused), 4 approving nod (new best)
    return [cat_frame("meh"), cat_frame("up"), cat_frame("blink"),
            cat_frame("stare", extra="dots"), cat_frame("happy", nod=6, extra="bang")]


# ---------------------------------------------------------------- figure --
FIG_W, FIG_H = 130, 110
FIG_FRAMES = 12


def limb(d, a, b, width, fill):
    d.line([a, b], fill=fill, width=width)
    r = width / 2
    for (x, y) in (a, b):
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def figure_frame(p, pose="rep", zz=False):
    S = SS
    img = Image.new("L", (FIG_W * S, FIG_H * S), 0)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4 * S, 98 * S, 126 * S, 104 * S], radius=3 * S, fill=MAT)
    hip = (62 * S, 90 * S)
    knee = (88 * S, 62 * S)
    foot = (110 * S, 92 * S)
    W = 8 * S
    limb(d, hip, knee, W, SKIN_EDGE)
    limb(d, knee, foot, W, SKIN_EDGE)
    d.rounded_rectangle([104 * S, 89 * S, 120 * S, 97 * S], radius=3 * S, fill=SKIN_EDGE)  # shoe

    theta = math.radians(172 - p * 98)  # lying (left) -> upright, leaning to knees
    torso_len = 33 * S
    shoulder = (hip[0] + torso_len * math.cos(theta), hip[1] - torso_len * math.sin(theta))
    limb(d, hip, shoulder, 10 * S, SKIN_EDGE)
    # arms
    if pose == "cheer":
        for a in (math.radians(68), math.radians(104)):  # arms up at the ceiling
            hand = (shoulder[0] + 30 * S * math.cos(a), shoulder[1] - 30 * S * math.sin(a))
            limb(d, shoulder, hand, 6 * S, 255)
    else:
        reach = math.radians(25 - 32 * p)  # reaching toward the knees
        hand = (shoulder[0] + 28 * S * math.cos(reach), shoulder[1] - 28 * S * math.sin(reach))
        limb(d, shoulder, hand, 6 * S, 255)
    # head + headband
    hc = (shoulder[0] + 13 * S * math.cos(theta), shoulder[1] - 13 * S * math.sin(theta))
    r = 11 * S
    d.ellipse([hc[0] - r, hc[1] - r, hc[0] + r, hc[1] + r], fill=SKIN_EDGE)
    d.ellipse([hc[0] - r + 2 * S, hc[1] - r + 2 * S, hc[0] + r - 2 * S, hc[1] + r - 2 * S], fill=SKIN)
    band_a = theta
    bx, by = hc[0] + 4 * S * math.cos(band_a), hc[1] - 4 * S * math.sin(band_a)
    perp = band_a + math.pi / 2
    dx, dy = 11 * S * math.cos(perp), -11 * S * math.sin(perp)
    d.line([(bx - dx, by - dy), (bx + dx, by + dy)], fill=BAND, width=4 * S)
    if pose == "cheer":
        for (x, y, s) in ((20, 46, 7), (66, 30, 6), (44, 22, 4)):
            star(d, x * S, y * S, s * S)
    if zz:
        d.text((84 * S, 10 * S), "z", fill=230, font_size=20 * S)
        d.text((100 * S, 2 * S), "z", fill=160, font_size=14 * S)
    return finish(img, (FIG_W, FIG_H))


def figure_frames():
    frames = [figure_frame(i / (FIG_FRAMES - 1)) for i in range(FIG_FRAMES)]
    frames.append(figure_frame(0.0, pose="cheer"))  # same pose as frame 0
    frames.append(figure_frame(0.0, zz=True))
    return frames


# --------------------------------------------------------------- encoding --
def to_indexed(img):
    """GRAY_4 payload: 16 BGRA palette entries then packed 4-bit pixels.
    Index 0 is transparent so the black screen shows through."""
    palette = bytearray()
    for i in range(16):
        v = i * 17
        palette += bytes((v, v, v, 0 if i == 0 else 255))
    w, h = img.size
    px = img.load()
    out = bytearray()
    for y in range(h):
        row = [min(15, (px[x, y] + 8) // 17) for x in range(w)]
        if w % 2:
            row.append(0)
        for x in range(0, len(row), 2):
            out.append((row[x] << 4) | row[x + 1])
    return bytes(palette + out)


def gray_values(img):
    w, h = img.size
    px = img.load()
    return [min(15, (px[x, y] + 8) // 17) for y in range(h) for x in range(w)]


def rle_values(vals):
    """Run-length encode 4-bit values, one byte per run:
         high nibble = value 0..15
         low nibble  = 0..14 -> run of 1..15 pixels
                       15    -> run of 16 + next byte (16..271 pixels)
    Soft anti-aliased edges cost one byte per pixel; flat areas almost nothing."""
    out = bytearray()
    i = 0
    while i < len(vals):
        v, n = vals[i], 1
        while i + n < len(vals) and vals[i + n] == v and n < 271:
            n += 1
        if n <= 15:
            out.append((v << 4) | (n - 1))
        else:
            out += bytes(((v << 4) | 15, n - 16))
        i += n
    return bytes(out)


def rle(img):
    return rle_values(gray_values(img))


def rle_delta(img, base):
    """Store only what differs from `base` (same size): each pixel XOR the base
    pixel, so unchanged areas become long runs of zero."""
    return rle_values([a ^ b for a, b in zip(gray_values(img), gray_values(base))])


def emit(name, frames, w, h, lines, stats, base=None):
    """One flat byte blob per animation plus a table of offsets.
    No pointer tables: on the glasses every pointer table costs RAM and a
    relocation, and the loader's address table is small."""
    lines.append(f"#define {name.upper()}_WIDTH {w}U")
    lines.append(f"#define {name.upper()}_HEIGHT {h}U")
    lines.append(f"#define {name.upper()}_FRAMES {len(frames)}U")
    blob = bytearray()
    offsets = []
    for f in frames:
        assert f.size == (w, h), (name, f.size)
        offsets.append(len(blob))
        blob += rle(f) if base is None else rle_delta(f, base[len(offsets) - 1])
    offsets.append(len(blob))  # end marker: frame i is offsets[i]..offsets[i+1]
    lines.append(f"static const uint8_t {name}_data[{len(blob)}] = {{")
    for off in range(0, len(blob), 24):
        lines.append("    " + ", ".join(f"0x{b:02X}" for b in blob[off:off + 24]) + ",")
    lines.append("};")
    lines.append(f"static const uint32_t {name}_offsets[{len(offsets)}] = {{")
    lines.append("    " + ", ".join(str(o) for o in offsets) + ",")
    lines.append("};")
    lines.append("")
    stats.append((name, len(frames), len(blob), len(frames) * (64 + (w + 1) // 2 * h)))


def ring_preview(p=0.7):
    S = SS
    img = Image.new("L", (140 * S, 140 * S), 0)
    d = ImageDraw.Draw(img)
    box = [10 * S, 10 * S, 130 * S, 130 * S]
    d.arc(box, 135, 405, fill=70, width=12 * S)
    d.arc(box, 135, 135 + 270 * p, fill=255, width=12 * S)
    d.text((70 * S, 70 * S), "12", fill=255, font_size=44 * S, anchor="mm")
    return finish(img, (140, 140))


def save_preview(img, path):
    """Tint the gray art green like the glasses' display for the phone UI."""
    w, h = img.size
    rgb = Image.merge("RGB", (img.point(lambda v: v * 0.35), img, img.point(lambda v: v * 0.55)))
    bg = Image.new("RGB", (w, h), (11, 15, 12))
    bg.paste(rgb, (0, 0), img.point(lambda v: 255 if v > 0 else 0))
    bg.save(path, optimize=True)


def placeholder(frames):
    """Same number of frames, but 8x8 and blank: for install-size testing."""
    return [Image.new("L", (8, 8), 0) for _ in frames]


def main(keep=None, out_header=None, previews=True):
    """keep: set of animation names to keep at full size; others become tiny
    placeholders (used to build install-diagnosis variants). None = keep all."""
    full = lambda n: keep is None or n in keep
    heads = head_frames()
    tiers = [head_frames(t) for t in (1, 2, 3)]
    figs = figure_frames()
    auras = aura_frames(figs)
    cats = cat_frames()
    sizes = {}
    stats = []
    lines = [
        "/* Generated by tools/make_sprites.py - do not edit by hand. */",
        "/* Frames are run-length encoded, see rle_values() in tools/make_sprites.py.",
        " * glow1-3 and aura store only the difference (XOR) from head / figure. */",
        "#ifndef SITUP_SPRITES_H",
        "#define SITUP_SPRITES_H",
        "",
        "/* Head (also glow-up tier 0): lean back -> curl forward, then happy, sleepy */",
    ]
    lines.append(f"#define HEAD_TILT_FRAMES {HEAD_TILT_FRAMES}U  /* then happy, sleepy */")
    def put(name, frames, w, h, base=None):
        if not full(name):
            frames, w, h, base = placeholder(frames), 8, 8, None
        sizes[name] = w * h
        emit(name, frames, w, h, lines, stats, base)
    put("head", heads, HEAD_W, HEAD_H)
    for t, frames in zip((1, 2, 3), tiers):
        lines.append(f"/* Glow-up tier {t}: same layout as head, stored as the difference from it */")
        put(f"glow{t}", frames, HEAD_W, HEAD_H, base=heads)
    lines.append(f"/* Figure: 0..{FIG_FRAMES - 1} lying -> sitting up, then cheer, sleepy */")
    lines.append(f"#define FIGURE_TILT_FRAMES {FIG_FRAMES}U")
    put("figure", figs, FIG_W, FIG_H)
    lines.append("/* Aura: the figure frames with a glowing aura, stored as the difference from them */")
    put("aura", auras, FIG_W, FIG_H, base=figs)
    lines.append("/* Cat: 0 unimpressed, 1 watching, 2 slow blink, 3 judging stare, 4 approving nod */")
    put("cat", cats, CAT_W, CAT_H)
    biggest = max(sizes.values())
    lines.append(f"#define SPRITE_MAX_PIXELS {biggest}U")
    lines.append("#endif")
    target = out_header or OUT_HEADER
    target.write_text("\n".join(lines) + "\n")
    print(f"wrote {target}")
    for name, n, packed, raw in stats:
        print(f"  {name:7s} {n:2d} frames  {packed:6d} B packed  ({raw} B raw)")
    print(f"  total {sum(s[2] for s in stats)} B")

    if previews and PHONE_PREVIEWS.parent.is_dir():
        PHONE_PREVIEWS.mkdir(exist_ok=True)
        save_preview(ring_preview(), PHONE_PREVIEWS / "style-ring.png")
        save_preview(heads[6].crop((2, 6, 144, 148)).resize((140, 140), Image.LANCZOS), PHONE_PREVIEWS / "style-head.png")
        save_preview(figs[5].crop((0, -15, 130, 115)).resize((140, 140), Image.LANCZOS), PHONE_PREVIEWS / "style-figure.png")
        save_preview(tiers[2][3].crop((2, 6, 144, 148)).resize((140, 140), Image.LANCZOS), PHONE_PREVIEWS / "style-glowup.png")
        save_preview(auras[6].crop((0, -15, 130, 115)).resize((140, 140), Image.LANCZOS), PHONE_PREVIEWS / "style-aura.png")
        save_preview(cats[0], PHONE_PREVIEWS / "style-cat.png")
        save_preview(stonks_preview(), PHONE_PREVIEWS / "style-stonks.png")
        print(f"wrote previews to {PHONE_PREVIEWS}")

    if keep is not None:
        return
    # contact sheet for eyeballing the art
    rows = [heads] + tiers + [[f.crop((0, 0, 140, 110)) for f in figs],
                              [f.crop((0, 0, 140, 110)) for f in auras], cats]
    sheet = Image.new("L", (144 * 16, sum(r[0].height for r in rows)), 0)
    y = 0
    for r in rows:
        for i, f in enumerate(r):
            sheet.paste(f, (i * 144, y))
        y += r[0].height
    sheet.save(HERE / "contact-sheet.png")


def stonks_preview():
    S = SS
    img = Image.new("L", (140 * S, 140 * S), 0)
    d = ImageDraw.Draw(img)
    d.line([(14 * S, 20 * S), (14 * S, 120 * S), (130 * S, 120 * S)], fill=90, width=3 * S)
    pts = [(14, 108), (32, 96), (48, 100), (66, 78), (84, 70), (100, 48), (120, 26)]
    d.line([(x * S, y * S) for x, y in pts], fill=255, width=5 * S, joint="curve")
    d.text((22 * S, 14 * S), "STONKS", fill=255, font_size=18 * S)
    return finish(img, (140, 140))


if __name__ == "__main__":
    main()
