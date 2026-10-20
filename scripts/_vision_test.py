"""Test Ollama vision with a real-sized image (create a 100x100 PNG programmatically)."""
import base64, io, json, struct, urllib.request, urllib.error, zlib

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "qwen3.5:4b"

def make_png(width=100, height=100):
    """Create a valid PNG with a simple gradient pattern."""
    def chunk(name, data):
        c = struct.pack('>I', len(data)) + name + data
        return c + struct.pack('>I', zlib.crc32(name + data) & 0xFFFFFFFF)

    raw_rows = b""
    for y in range(height):
        row = b"\x00"  # filter type none
        for x in range(width):
            r = int(x * 255 / width)
            g = int(y * 255 / height)
            b = 128
            row += bytes([r, g, b])
        raw_rows += row

    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    idat_data = zlib.compress(raw_rows)
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', ihdr_data)
           + chunk(b'IDAT', idat_data)
           + chunk(b'IEND', b''))
    return png

png_bytes = make_png(100, 100)
img_b64 = base64.b64encode(png_bytes).decode()
print(f"Image size: {len(png_bytes)} bytes, b64: {len(img_b64)} chars")

payload = json.dumps({
    "model": MODEL,
    "messages": [{"role": "user", "content": "Describe this image in one sentence.", "images": [img_b64]}],
    "stream": False,
    "think": False,
    "options": {"num_predict": 60, "temperature": 0},
}).encode()

print(f"Sending {len(payload)} byte payload to {OLLAMA_URL}/api/chat ...")
try:
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        result = json.loads(r.read())
        reply = result.get("message", {}).get("content", "").strip()
        print(f"\n✅ Vision API works! Response: {reply[:200]}")
except urllib.error.HTTPError as e:
    print(f"\n❌ HTTP {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"\n❌ {type(e).__name__}: {e}")
