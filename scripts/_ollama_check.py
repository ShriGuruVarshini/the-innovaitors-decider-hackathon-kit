"""Check Ollama models and test vision capability."""
import base64, json, urllib.request

OLLAMA_URL = "http://127.0.0.1:11434"

# List models
with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as r:
    data = json.loads(r.read())
    models = data.get("models", [])
    print(f"Models installed ({len(models)}):")
    for m in models:
        print(f"  {m.get('name')}  {round(m.get('size',0)/1e9,2)} GB  details={m.get('details',{})}")

# Check which models have vision via /api/show
print()
for m in models:
    name = m.get("name")
    try:
        payload = json.dumps({"name": name}).encode()
        req = urllib.request.Request(f"{OLLAMA_URL}/api/show", data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            info = json.loads(r.read())
            caps = info.get("capabilities", [])
            print(f"  {name}: capabilities = {caps}")
    except Exception as e:
        print(f"  {name}: error = {e}")
