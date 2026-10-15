"""Tiny file makers for WinUx: pixel grids -> PNG / ICO / CUR / ANI, notes -> WAV.
Standard library only."""

import math
import random
import struct
import zlib


# ---------------------------------------------------------------- pixels

def render(rows, palette, scale=1):
    """Text grid -> (w, h, rgba bytes). Each character is looked up in `palette`
    ({char: (r, g, b, a)}); '.' and unknown characters are transparent."""
    h0, w0 = len(rows), max(len(r) for r in rows)
    w, h = w0 * scale, h0 * scale
    out = bytearray(w * h * 4)
    for y in range(h):
        row = rows[y // scale]
        for x in range(w):
            ch = row[x // scale] if x // scale < len(row) else "."
            px = palette.get(ch)
            if px:
                i = (y * w + x) * 4
                out[i:i + 4] = bytes(px if len(px) == 4 else (*px, 255))
    return w, h, bytes(out)


def hex_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# ---------------------------------------------------------------- PNG / ICO

def png(w, h, rgba):
    raw = b"".join(b"\x00" + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def ico(images):
    """images: list of (w, h, rgba). Stored as PNGs (fine on Windows Vista and newer)."""
    blobs = [png(w, h, d) for w, h, d in images]
    head = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    for (w, h, _), blob in zip(images, blobs):
        entries += struct.pack("<BBBBHHII", w % 256, h % 256, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    return head + entries + b"".join(blobs)


# ---------------------------------------------------------------- CUR / ANI

def _dib(w, h, rgba):
    """32-bit bottom-up DIB with an AND mask, the classic cursor image format."""
    header = struct.pack("<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0, 0, 0, 0, 0, 0)
    pixels = bytearray()
    for y in range(h - 1, -1, -1):
        for x in range(w):
            r, g, b, a = rgba[(y * w + x) * 4:(y * w + x) * 4 + 4]
            pixels += bytes((b, g, r, a))
    row_bytes = ((w + 31) // 32) * 4
    mask = bytearray()
    for y in range(h - 1, -1, -1):
        bits = bytearray(row_bytes)
        for x in range(w):
            if rgba[(y * w + x) * 4 + 3] == 0:
                bits[x // 8] |= 0x80 >> (x % 8)
        mask += bits
    return header + bytes(pixels) + bytes(mask)


def cur(images, hotspot):
    """images: list of (w, h, rgba) at different sizes of the same cursor.
    hotspot: (x, y) as a fraction of the size (0..1), so it scales with each image."""
    blobs = [_dib(w, h, d) for w, h, d in images]
    head = struct.pack("<HHH", 0, 2, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    for (w, h, _), blob in zip(images, blobs):
        hx, hy = round(hotspot[0] * (w - 1)), round(hotspot[1] * (h - 1))
        entries += struct.pack("<BBBBHHII", w % 256, h % 256, 0, 0, hx, hy, len(blob), offset)
        offset += len(blob)
    return head + entries + b"".join(blobs)


def ani(frames, jiffies=8):
    """Animated cursor from a list of .cur file bytes. jiffies = 1/60 s per frame."""
    def chunk(kind, data):
        return kind + struct.pack("<I", len(data)) + data + (b"\x00" if len(data) % 2 else b"")

    anih = struct.pack("<9I", 36, len(frames), len(frames), 0, 0, 0, 0, jiffies, 1)
    fram = b"fram" + b"".join(chunk(b"icon", f) for f in frames)
    body = b"ACON" + chunk(b"anih", anih) + chunk(b"LIST", fram)
    return b"RIFF" + struct.pack("<I", len(body)) + body


# ---------------------------------------------------------------- sound

RATE = 22050


def note_freq(name):
    """'C5', 'A#4', 'Eb3' -> Hz."""
    names = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    n = names[name[0]]
    i = 1
    if name[1:2] in ("#", "b"):
        n += 1 if name[1] == "#" else -1
        i = 2
    octave = int(name[i:])
    return 440.0 * 2 ** ((n + 12 * (octave + 1) - 69) / 12)


def tone(freq, dur, vol=0.35, duty=0.5, slide=0.0, wave="square", decay=6.0):
    """One chiptune note. slide = Hz per second pitch bend. Returns a list of floats."""
    n = int(RATE * dur)
    out, phase = [], 0.0
    for i in range(n):
        f = max(20.0, freq + slide * i / RATE)
        phase = (phase + f / RATE) % 1.0
        if wave == "square":
            s = 1.0 if phase < duty else -1.0
        elif wave == "triangle":
            s = 4 * abs(phase - 0.5) - 1
        else:  # noise
            s = random.uniform(-1, 1)
        attack = min(1.0, i / (RATE * 0.004))
        env = attack * math.exp(-decay * i / n)
        out.append(s * vol * env)
    return out


def rest(dur):
    return [0.0] * int(RATE * dur)


def mix(*tracks):
    n = max(len(t) for t in tracks)
    return [sum(t[i] for t in tracks if i < len(t)) for i in range(n)]


def wav(samples):
    data = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32000)) for s in samples)
    fmt = struct.pack("<HHIIHH", 1, 1, RATE, RATE * 2, 2, 16)
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", len(data)) + data
    return b"RIFF" + struct.pack("<I", len(body)) + body
