import os
import pathlib
from dotenv import load_dotenv
import replicate
import requests

def ensure_dir(p):
    pathlib.Path(p).mkdir(parents=True, exist_ok=True)

def download(url, path):
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)

def build_prompts(theme):
    base_style = "minimal clean UI, elegant card layout, soft shadows, crisp, high quality, professional, branding poseidon ocean"
    color = "ocean teal and azure gradient" if theme == "light" else "deep navy and teal glow"
    return {
        "encuesta": f"discord poll interface, buttons and options, {base_style}, {color}",
        "sorteo": f"giveaway card with ticket icon, prize highlight, CTA button, {base_style}, {color}",
        "tienda": f"shop product card with price and buy button, {base_style}, {color}",
        "rss": f"rss feed panel with list items and wave icon, {base_style}, {color}",
        "moderacion": f"moderation dashboard with action buttons, shield motif, {base_style}, {color}",
        "ayuda": f"help panel with command list, info icon, {base_style}, {color}",
        "planes": f"pricing tiers cards row, badges per tier, {base_style}, {color}",
    }

def run():
    load_dotenv()
    token = os.getenv("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError("Falata REPLICATE_API_TOKEN en .env")
    os.environ["REPLICATE_API_TOKEN"] = token
    out_dir = os.path.join("assets", "generated")
    ensure_dir(out_dir)
    model = os.getenv("REPLICATE_MODEL", "black-forest-labs/flux-1.1-pro")
    theme = os.getenv("GALLERY_THEME", "light")
    prompts = build_prompts(theme)
    for name, prompt in prompts.items():
        result = replicate.run(model, input={"prompt": prompt, "image_size": "1024x576"})
        url = result[0] if isinstance(result, list) else result
        path = os.path.join(out_dir, f"{name}.png")
        download(url, path)

if __name__ == "__main__":
    run()
