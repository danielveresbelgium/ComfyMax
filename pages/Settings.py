from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
APP_CONFIG_PATH = CONFIG_DIR / "app.json"
SETTINGS_PATH = CONFIG_DIR / "settings.json"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else dict(default)
    except (OSError, json.JSONDecodeError):
        return dict(default)


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def request_json(url: str, timeout: int = 10) -> dict:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, dict) else {}


def get_comfyui_model_options(comfyui_url: str, class_type: str, input_name: str) -> list[str]:
    base = comfyui_url.rstrip("/")
    try:
        data = request_json(f"{base}/object_info/{class_type}")
    except requests.RequestException:
        data = request_json(f"{base}/object_info")

    node_info: dict[str, Any] = {}
    if class_type in data and isinstance(data[class_type], dict):
        node_info = data[class_type]
    elif len(data) == 1:
        only = next(iter(data.values()))
        if isinstance(only, dict):
            node_info = only

    inputs = node_info.get("input", {})
    if not isinstance(inputs, dict):
        return []

    for section_name in ("required", "optional"):
        section = inputs.get(section_name, {})
        if not isinstance(section, dict):
            continue
        spec = section.get(input_name)
        if isinstance(spec, (list, tuple)) and spec:
            options = spec[0]
            if isinstance(options, list):
                return [str(x) for x in options]
    return []


def select_saved(label: str, options: list[str], saved_value: str | None, key: str) -> str | None:
    if not options:
        st.selectbox(label, ["No models found"], disabled=True, key=f"{key}_empty")
        return None
    index = options.index(saved_value) if saved_value in options else 0
    return st.selectbox(label, options, index=index, key=key)


app_config = load_json(APP_CONFIG_PATH, {
    "lmstudio_url": "http://127.0.0.1:1234",
    "comfyui_url": "http://127.0.0.1:8188",
    "temperature": 0.7,
})

saved = load_json(SETTINGS_PATH, {
    "comfyui_url": app_config.get("comfyui_url", "http://127.0.0.1:8188"),
    "lmstudio_url": app_config.get("lmstudio_url", "http://127.0.0.1:1234"),
    "minimax_h3": {"unet": "", "video_vae": "", "audio_vae": "", "clip": ""},
})

st.set_page_config(page_title="ComfyMax Settings", page_icon="⚙️", layout="wide")
st.title("⚙️ ComfyMax Settings")
st.caption("This page stores ComfyMax settings separately. The main page is not modified by this page.")
st.info("Settings are saved in config/settings.json. The main App.py currently continues to use config/app.json for its base configuration.")

st.subheader("Local services")
c1, c2 = st.columns(2)
with c1:
    comfyui_url = st.text_input("ComfyUI URL", value=saved.get("comfyui_url", app_config.get("comfyui_url", "http://127.0.0.1:8188")))
with c2:
    lmstudio_url = st.text_input("LM Studio URL", value=saved.get("lmstudio_url", app_config.get("lmstudio_url", "http://127.0.0.1:1234")))

t1, t2 = st.columns(2)
with t1:
    if st.button("Test ComfyUI", use_container_width=True):
        try:
            request_json(f"{comfyui_url.rstrip('/')}/object_info")
            st.success("ComfyUI is reachable.")
        except (requests.RequestException, ValueError) as exc:
            st.error(f"ComfyUI is unreachable: {exc}")
with t2:
    if st.button("Test LM Studio", use_container_width=True):
        try:
            r = requests.get(f"{lmstudio_url.rstrip('/')}/v1/models", timeout=10)
            r.raise_for_status()
            st.success("LM Studio is reachable.")
        except requests.RequestException as exc:
            st.error(f"LM Studio is unreachable: {exc}")

st.divider()
st.subheader("MiniMax H3 model defaults")
st.caption("The model lists are read directly from ComfyUI, so ComfyMax does not need to know where the models folder is located.")

if st.button("Refresh model lists from ComfyUI", type="primary"):
    st.session_state.pop("settings_model_lists", None)

if "settings_model_lists" not in st.session_state:
    try:
        st.session_state.settings_model_lists = {
            "unet": get_comfyui_model_options(comfyui_url, "UNETLoader", "unet_name"),
            "vae": get_comfyui_model_options(comfyui_url, "VAELoader", "vae_name"),
            "clip": get_comfyui_model_options(comfyui_url, "CLIPLoader", "clip_name"),
        }
    except (requests.RequestException, ValueError):
        st.session_state.settings_model_lists = {"unet": [], "vae": [], "clip": []}

lists = st.session_state.settings_model_lists
saved_h3 = saved.get("minimax_h3", {})

m1, m2 = st.columns(2)
with m1:
    selected_unet = select_saved("MiniMax H3 video model / UNET", lists.get("unet", []), saved_h3.get("unet"), "settings_unet")
    selected_video_vae = select_saved("Video VAE", lists.get("vae", []), saved_h3.get("video_vae"), "settings_video_vae")
with m2:
    selected_clip = select_saved("Text encoder / CLIP", lists.get("clip", []), saved_h3.get("clip"), "settings_clip")
    selected_audio_vae = select_saved("Audio VAE", lists.get("vae", []), saved_h3.get("audio_vae"), "settings_audio_vae")

st.divider()
if st.button("Save settings", type="primary", use_container_width=True):
    new_settings = {
        "comfyui_url": comfyui_url.strip(),
        "lmstudio_url": lmstudio_url.strip(),
        "minimax_h3": {
            "unet": selected_unet or "",
            "video_vae": selected_video_vae or "",
            "audio_vae": selected_audio_vae or "",
            "clip": selected_clip or "",
        },
    }
    try:
        save_json(SETTINGS_PATH, new_settings)
        st.success(f"Settings saved to {SETTINGS_PATH}")
    except OSError as exc:
        st.error(f"Settings could not be saved: {exc}")
