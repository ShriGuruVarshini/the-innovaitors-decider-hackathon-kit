"""Pre-video checks: ffmpeg, Playwright/Chromium, TTS, bench results."""
import sys, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 1. ffmpeg
try:
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"ffmpeg: {ff}")
except Exception as e:
    print(f"ffmpeg: MISSING ({e})")

# 2. Playwright chromium
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        b.close()
    print("playwright/chromium: OK")
except Exception as e:
    print(f"playwright/chromium: MISSING ({e})")

# 3. TTS options
import subprocess
# Windows SAPI (pyttsx3 or PowerShell)
ps = shutil.which("powershell") or shutil.which("pwsh")
if ps:
    r = subprocess.run([ps, "-Command",
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }"],
        capture_output=True, text=True, timeout=10)
    voices = [v.strip() for v in r.stdout.strip().splitlines() if v.strip()]
    print(f"Windows TTS voices: {voices}")
else:
    print("Windows TTS: PowerShell not found")

# 4. AWS Polly
try:
    import boto3
    from decider_kit.config import settings
    s = settings()
    polly = boto3.client("polly", region_name=s.aws_region)
    polly.describe_voices()
    print("AWS Polly: OK")
except Exception as e:
    print(f"AWS Polly: unavailable ({type(e).__name__})")

# 5. Bench results
bench = ROOT / "submission" / "bench" / "results.json"
print(f"bench results: {'present' if bench.exists() else 'MISSING (run kit bench first)'}")

# 6. Demo server running?
import urllib.request
try:
    urllib.request.urlopen("http://127.0.0.1:8501/api/info", timeout=2)
    print("demo server: running on :8501")
except Exception:
    print("demo server: not running (will be started by kit video)")

# 7. Sculpture image
img_dir = ROOT / "agent" / "data" / "images"
images = list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png")) + list(img_dir.glob("*.jpeg"))
if images:
    print(f"sculpture images: {[i.name for i in images]}")
else:
    print("sculpture images: NONE in agent/data/images/ (will download one)")
