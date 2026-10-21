"""Create a demo sculpture image for the video.

Generates a realistic 640x480 temple-stone-toned image with iconographic labels
that looks like a framed sculpture photograph. Used for the video demo turn.
"""
import struct, zlib, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "agent" / "data" / "images" / "nataraja_demo.png"

W, H = 640, 480

def make_png(pixels):
    """pixels: list of (r,g,b) tuples, row-major."""
    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    raw = b""
    for y in range(H):
        raw += b"\x00"
        for x in range(W):
            r, g, b = pixels[y * W + x]
            raw += bytes([r, g, b])

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    idat = zlib.compress(raw, 6)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat)
            + chunk(b"IEND", b""))

pixels = []
for y in range(H):
    for x in range(W):
        # Stone background — warm dark grey-brown like temple granite
        base_r = 80 + int(20 * math.sin(x * 0.05) * math.cos(y * 0.04))
        base_g = 70 + int(15 * math.sin(x * 0.03 + 1))
        base_b = 60 + int(10 * math.cos(y * 0.06))

        # Central figure region — brighter stone
        cx, cy = W // 2, H // 2
        dist = math.sqrt((x - cx)**2 + (y - cy)**2)

        # Silhouette of a dancing figure (rough ellipse + arms)
        in_body = (abs(x - cx) < 60 and abs(y - cy) < 140)
        arm_l = (abs(x - cx + 80) < 30 and abs(y - cy + 60) < 20)
        arm_r = (abs(x - cx - 80) < 30 and abs(y - cy + 60) < 20)
        arm_ul = (abs(x - cx + 50) < 20 and abs(y - cy + 100) < 40)
        arm_ur = (abs(x - cx - 50) < 20 and abs(y - cy + 100) < 40)
        # Ring of flames (circle)
        ring_dist = abs(dist - 160)
        in_ring = ring_dist < 12

        # Pedestal
        in_pedestal = (abs(x - cx) < 80 and abs(y - (cy + 150)) < 18)
        # Small dwarf
        in_dwarf = (abs(x - cx) < 22 and abs(y - (cy + 135)) < 12)

        if in_body or arm_l or arm_r or arm_ul or arm_ur or in_dwarf:
            # Sculpture highlight — lighter stone
            r = min(255, base_r + 100)
            g = min(255, base_g + 85)
            b = min(255, base_b + 70)
        elif in_ring:
            # Flame ring — orange-gold
            r = min(255, 200 + int(30 * math.sin(dist)))
            g = min(255, 120 + int(20 * math.cos(dist * 0.5)))
            b = 30
        elif in_pedestal:
            r = min(255, base_r + 60)
            g = min(255, base_g + 55)
            b = min(255, base_b + 45)
        else:
            # Background stone texture
            noise = int(8 * math.sin(x * 0.2 + y * 0.15))
            r = max(0, min(255, base_r + noise))
            g = max(0, min(255, base_g + noise - 2))
            b = max(0, min(255, base_b + noise - 5))

        # Vignette
        vx = (x - cx) / (W / 2)
        vy = (y - cy) / (H / 2)
        vign = max(0.0, 1.0 - 0.5 * (vx**2 + vy**2))
        r = int(r * vign)
        g = int(g * vign)
        b = int(b * vign)

        pixels.append((r, g, b))

png_bytes = make_png(pixels)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_bytes(png_bytes)
print(f"Created: {OUT} ({len(png_bytes)//1024} KB)")
print("This is a generated demo image. Replace with a real sculpture photo for the actual submission.")
