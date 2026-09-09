from __future__ import annotations

import json
import random
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import streamlit as st

from modules.comfyui import (
    ComfyUIClient,
    ComfyUIError,
    apply_mapping,
    load_api_workflow,
)
from modules.lmstudio import LMStudioClient, LMStudioError
from modules.prompt_enhancer import get_h3_system_prompt


# =========================================================
# Paden en basisconfiguratie
# =========================================================

ROOT = Path(__file__).parent
CONFIG_DIR = ROOT / "config"
WORKFLOWS_DIR = ROOT / "workflows"
WORKFLOW_MAPPINGS_DIR = CONFIG_DIR / "workflow_mappings"
SETTINGS_PATH = CONFIG_DIR / "settings.json"
JS_SAFE_INTEGER = (1 << 53) - 1

APP_CONFIG_PATH = CONFIG_DIR / "app.json"
APP_CONFIG_EXAMPLE_PATH = CONFIG_DIR / "app.example.json"

if not APP_CONFIG_PATH.exists():
    if not APP_CONFIG_EXAMPLE_PATH.exists():
        raise FileNotFoundError(
            "Missing configuration files: config/app.json and config/app.example.json."
        )
    shutil.copyfile(APP_CONFIG_EXAMPLE_PATH, APP_CONFIG_PATH)

APP_CONFIG = json.loads(APP_CONFIG_PATH.read_text(encoding="utf-8"))

if SETTINGS_PATH.exists():
    try:
        USER_SETTINGS = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        USER_SETTINGS = {}
else:
    USER_SETTINGS = {}


# =========================================================
# Helpers
# =========================================================

def get_available_workflows() -> list[Path]:
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(WORKFLOWS_DIR.glob("*.json"), key=lambda path: path.name.lower())


def workflow_display_name(path: Path) -> str:
    return path.stem.replace("_", " ")


def get_mapping_path(workflow_path: Path) -> Path:
    return WORKFLOW_MAPPINGS_DIR / workflow_path.name


def load_workflow_mapping(workflow_path: Path) -> dict:
    mapping_path = get_mapping_path(workflow_path)

    if not mapping_path.exists():
        raise FileNotFoundError(
            "No mapping found for this workflow:\n\n"
            f"{mapping_path}"
        )

    try:
        return json.loads(mapping_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            "The workflow mapping contains invalid JSON:\n\n"
            f"{mapping_path}\n\n{exc}"
        ) from exc


def probe_video_bytes(video_bytes: bytes, filename: str) -> dict:
    """Lees echte video-eigenschappen via ffprobe, met veilige fallback."""
    metadata = {
        "filename": filename,
        "format": Path(filename).suffix.lstrip(".").upper() or "-",
        "file_size_bytes": len(video_bytes),
    }

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return metadata

    suffix = Path(filename).suffix or ".mp4"
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(video_bytes)
            temp_path = Path(tmp.name)

        result = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-show_entries",
                "stream=width,height:format=duration,format_name,size",
                "-of", "json",
                str(temp_path),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        data = json.loads(result.stdout or "{}")

        video_stream = next(
            (
                stream
                for stream in data.get("streams", [])
                if stream.get("width") and stream.get("height")
            ),
            None,
        )

        if video_stream:
            metadata["width"] = int(video_stream["width"])
            metadata["height"] = int(video_stream["height"])

        fmt = data.get("format", {})
        if fmt.get("duration"):
            metadata["duration_seconds"] = float(fmt["duration"])
        if fmt.get("format_name"):
            metadata["format_name"] = fmt["format_name"]
        if fmt.get("size"):
            metadata["file_size_bytes"] = int(fmt["size"])

    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
        pass
    finally:
        if temp_path:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    return metadata


def human_file_size(size_bytes: int | None) -> str:
    if size_bytes is None:
        return "-"
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size_bytes} B"


def get_setting_value(path: str, default=None):
    """Lees een puntgescheiden waarde uit config/settings.json."""
    current = USER_SETTINGS
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def read_nvidia_gpu_stats() -> dict:
    """Lees GPU-status rechtstreeks via nvidia-smi, zonder extra Python-package."""
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        fallback = Path(r"C:\Windows\System32\nvidia-smi.exe")
        if fallback.exists():
            nvidia_smi = str(fallback)

    if not nvidia_smi:
        raise RuntimeError("nvidia-smi was not found.")

    query = ",".join(
        [
            "name",
            "utilization.gpu",
            "memory.used",
            "memory.total",
            "temperature.gpu",
            "power.draw",
        ]
    )

    result = subprocess.run(
        [
            nvidia_smi,
            f"--query-gpu={query}",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )

    first_line = next(
        (line.strip() for line in result.stdout.splitlines() if line.strip()),
        "",
    )
    if not first_line:
        raise RuntimeError("nvidia-smi returned no GPU information.")

    parts = [part.strip() for part in first_line.split(",")]
    if len(parts) < 6:
        raise RuntimeError("Unexpected response from nvidia-smi.")

    return {
        "name": parts[0],
        "gpu_util": _to_float(parts[1]),
        "memory_used_mb": _to_float(parts[2]),
        "memory_total_mb": _to_float(parts[3]),
        "temperature_c": _to_float(parts[4]),
        "power_w": _to_float(parts[5]),
    }


def _draw_gpu_monitor_values() -> None:
    try:
        gpu = read_nvidia_gpu_stats()
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        st.caption(f"GPU status unavailable: {exc}")
        return

    gpu_util = gpu.get("gpu_util")
    used_mb = gpu.get("memory_used_mb")
    total_mb = gpu.get("memory_total_mb")
    temp_c = gpu.get("temperature_c")
    power_w = gpu.get("power_w")

    memory_fraction = 0.0
    if used_mb is not None and total_mb:
        memory_fraction = max(0.0, min(used_mb / total_mb, 1.0))

    gpu_name = gpu.get("name", "NVIDIA GPU")
    gpu_name = gpu_name.replace("NVIDIA GeForce ", "")
    st.caption(gpu_name)

    status = []
    if gpu_util is not None:
        status.append(f"GPU **{gpu_util:.0f}%**")
    if temp_c is not None:
        status.append(f"**{temp_c:.0f} °C**")
    if power_w is not None:
        status.append(f"**{power_w:.0f} W**")
    if status:
        st.markdown(" · ".join(status))

    memory_text = "VRAM"
    if used_mb is not None and total_mb:
        used_gb = used_mb / 1024.0
        total_gb = total_mb / 1024.0
        memory_text += (
            f" · {used_gb:.1f} / {total_gb:.1f} GB"
            f" · {memory_fraction * 100:.0f}%"
        )

    st.progress(memory_fraction, text=memory_text)


def unload_comfyui_models(comfy_url: str) -> None:
    """Vraag ComfyUI om geladen modellen te ontladen en VRAM-cache vrij te geven."""
    url = comfy_url.rstrip("/") + "/free"
    payload = json.dumps(
        {
            "unload_models": True,
            "free_memory": True,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(
                    f"ComfyUI returned HTTP status {response.status}."
                )
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"ComfyUI returned HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ComfyUI is unreachable: {exc.reason}") from exc


def unload_all_lmstudio_models(lm_url: str) -> int:
    """Unload every model instance currently loaded in LM Studio."""
    base_url = lm_url.rstrip("/")

    # ComfyMax may be configured with either the LM Studio server root
    # or the OpenAI-compatible /v1 base URL. Model management uses /api/v1.
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]

    models_url = base_url + "/api/v1/models"

    try:
        request = urllib.request.Request(models_url, method="GET")
        with urllib.request.urlopen(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(
                    f"LM Studio returned HTTP status {response.status}."
                )
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"LM Studio returned HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LM Studio is unreachable: {exc.reason}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("LM Studio returned an invalid model list.") from exc

    instance_ids: list[str] = []

    for model in data.get("models", []):
        for instance in model.get("loaded_instances", []) or []:
            instance_id = instance.get("id")
            if instance_id:
                instance_ids.append(str(instance_id))

    if not instance_ids:
        return 0

    unload_url = base_url + "/api/v1/models/unload"
    unloaded_count = 0

    for instance_id in instance_ids:
        payload = json.dumps({"instance_id": instance_id}).encode("utf-8")
        request = urllib.request.Request(
            unload_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if not 200 <= response.status < 300:
                    raise RuntimeError(
                        f"LM Studio returned HTTP status {response.status} "
                        f"while unloading {instance_id}."
                    )
            unloaded_count += 1
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"LM Studio returned HTTP {exc.code} while unloading "
                f"{instance_id}."
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"LM Studio became unreachable while unloading {instance_id}: "
                f"{exc.reason}"
            ) from exc

    return unloaded_count


def refresh_gpu_monitor_now() -> None:
    """Werk dezelfde GPU-kaart onmiddellijk bij tijdens een blokkerende taak."""
    slot = globals().get("GPU_MONITOR_SLOT")
    if slot is None:
        return

    with slot.container():
        _draw_gpu_monitor_values()


def run_with_live_gpu(func, *, interval: float = 1.0):
    """Voer een blokkerende functie uit terwijl de GPU-monitor live blijft."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)

        while not future.done():
            refresh_gpu_monitor_now()
            time.sleep(interval)

        # Nog één meting zodra de taak klaar is.
        refresh_gpu_monitor_now()
        return future.result()


# =========================================================
# Streamlit pagina
# =========================================================

st.set_page_config(
    page_title="ComfyMax",
    page_icon="🎬",
    layout="wide",
)

st.title("ComfyMax v0.2")
st.caption(
    "From idea to a reviewed MiniMax H3 prompt, then on to ComfyUI."
)

# =========================================================
# Session state
# =========================================================

# Deze waarden moeten bestaan vóór fragments/threads of knoppen ze gebruiken.
# Vooral model_instance_id kan bij een handmatige prompt nog nooit gezet zijn.
_SESSION_DEFAULTS = {
    "prompt": "",
    "prompt_approved": False,
    "model_instance_id": None,
    "model_name": None,
    "model_unloaded": True,
}

for _key, _default in _SESSION_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default


# =========================================================
# Sidebar en clients
# =========================================================

with st.sidebar:
    st.header("Local services")
    lm_url = st.text_input("LM Studio", APP_CONFIG["lmstudio_url"])
    comfy_url = st.text_input("ComfyUI", APP_CONFIG["comfyui_url"])
    st.caption("Start LM Studio and ComfyUI locally before using the connection.")
    st.divider()

    with st.container(border=True):
        st.markdown("##### GPU monitor")
        GPU_MONITOR_SLOT = st.empty()

        if hasattr(st, "fragment"):
            @st.fragment(run_every="1s")
            def render_gpu_monitor_fragment() -> None:
                with GPU_MONITOR_SLOT.container():
                    _draw_gpu_monitor_values()

            render_gpu_monitor_fragment()
        else:
            with GPU_MONITOR_SLOT.container():
                _draw_gpu_monitor_values()

        unload_comfy_clicked = st.button(
            "Unload model from ComfyUI",
            use_container_width=True,
            key="unload_comfyui_models",
        )
        st.caption(
            "Unloads the currently loaded ComfyUI model and frees the VRAM cache. "
            "Use this when you no longer need the model."
        )

        unload_lmstudio_clicked = st.button(
            "Unload all models from LM Studio",
            use_container_width=True,
            key="unload_all_lmstudio_models",
        )
        st.caption(
            "Unloads every model currently loaded in LM Studio and frees the "
            "memory used by those models."
        )

    if unload_comfy_clicked:
        try:
            unload_comfyui_models(comfy_url)
            time.sleep(0.75)
            refresh_gpu_monitor_now()
            st.success("ComfyUI model unload requested.")
        except RuntimeError as exc:
            st.error(str(exc))

    if unload_lmstudio_clicked:
        try:
            unloaded_count = unload_all_lmstudio_models(lm_url)

            st.session_state.model_instance_id = None
            st.session_state.model_name = None
            st.session_state.model_unloaded = True

            time.sleep(0.75)
            refresh_gpu_monitor_now()

            if unloaded_count == 0:
                st.info("No models are currently loaded in LM Studio.")
            elif unloaded_count == 1:
                st.success("1 LM Studio model was unloaded.")
            else:
                st.success(f"{unloaded_count} LM Studio models were unloaded.")
        except RuntimeError as exc:
            st.error(str(exc))

lm_client = LMStudioClient(lm_url)
comfy_client = ComfyUIClient(comfy_url)


# =========================================================
# Hoofdindeling
# =========================================================

left_col, right_col = st.columns([1.55, 1.0], gap="large")

with left_col:
    st.subheader("Workflow & prompt")

    available_workflows = get_available_workflows()
    selected_workflow_path = None
    workflow_mapping = None

    if not available_workflows:
        st.warning(f"No workflows found in:\n\n{WORKFLOWS_DIR}")
    else:
        selected_workflow_path = st.selectbox(
            "ComfyUI workflow",
            options=available_workflows,
            format_func=workflow_display_name,
            key="selected_workflow",
        )

    if selected_workflow_path:
        try:
            workflow_mapping = load_workflow_mapping(selected_workflow_path)
            h3_mode = workflow_mapping.get("h3_mode")

            if not h3_mode:
                st.error(
                    "This workflow mapping does not contain an 'h3_mode'. "
                    'For example, add "h3_mode": "ref2va".'
                )
                workflow_mapping = None
            else:
                st.caption(
                    f"{selected_workflow_path.name} · "
                    f"{h3_mode.upper()} · "
                    f"{get_mapping_path(selected_workflow_path).name}"
                )

        except (FileNotFoundError, ValueError, OSError) as exc:
            workflow_mapping = None
            st.error(str(exc))

    workflow_key_prefix = (
        selected_workflow_path.stem if selected_workflow_path else "no_workflow"
    )

    field_values: dict[str, object] = {}
    image_uploads: dict[str, object] = {}

    # -----------------------------------------------------
    # Compacte hoofdinstellingen
    # -----------------------------------------------------

    compact_names = {"duration", "resolution", "aspect_ratio"}
    compact_fields: list[tuple[str, dict]] = []
    extra_fields: list[tuple[str, dict]] = []
    image_fields: list[tuple[str, dict]] = []
    model_setting_fields: list[tuple[str, dict]] = []

    if workflow_mapping:
        for field_name, rule in workflow_mapping.get("fields", {}).items():
            field_type = str(rule.get("type", "text")).lower()

            if field_type == "prompt":
                continue
            if field_type == "model_setting":
                model_setting_fields.append((field_name, rule))
            elif field_type == "image":
                image_fields.append((field_name, rule))
            elif field_name in compact_names:
                compact_fields.append((field_name, rule))
            else:
                extra_fields.append((field_name, rule))

    # Modelkeuzes komen uit de aparte Settings-pagina en verschijnen dus
    # niet opnieuw op de Create-pagina.
    missing_model_settings: list[str] = []
    for field_name, rule in model_setting_fields:
        setting_path = str(rule.get("setting", "")).strip()
        value = get_setting_value(setting_path, "")

        # Alleen overschrijven wanneer in Settings werkelijk een keuze is
        # opgeslagen. Zonder keuze blijft het model dat al in de workflow
        # staat gewoon behouden. Zo blijven bestaande workflows volledig
        # backwards-compatible.
        if value:
            field_values[field_name] = value
        else:
            missing_model_settings.append(setting_path or field_name)

    if missing_model_settings:
        st.caption(
            "For model defaults that are not configured, ComfyMax uses "
            "the model selection already stored in the workflow."
        )

    if compact_fields:
        st.markdown("##### Video settings")
        compact_columns = st.columns(len(compact_fields))

        for column, (field_name, rule) in zip(compact_columns, compact_fields):
            with column:
                field_type = str(rule.get("type", "text")).lower()
                label = rule.get("label", field_name.replace("_", " ").title())

                if field_type == "select_number":
                    options = rule.get("options", [])
                    default = rule.get("default")
                    try:
                        default_index = options.index(default)
                    except ValueError:
                        default_index = 0

                    if field_name == "duration":
                        formatter = lambda value: f"{value:g} sec"
                    elif field_name == "resolution":
                        formatter = lambda value: f"{value:g} MP"
                    else:
                        formatter = str

                    field_values[field_name] = st.selectbox(
                        label,
                        options=options,
                        index=default_index,
                        format_func=formatter,
                        key=f"{workflow_key_prefix}_{field_name}",
                    )

                elif field_type == "select":
                    options = rule.get("options", [])
                    default = rule.get("default")
                    try:
                        default_index = options.index(default)
                    except ValueError:
                        default_index = 0

                    field_values[field_name] = st.selectbox(
                        label,
                        options=options,
                        index=default_index,
                        key=f"{workflow_key_prefix}_{field_name}",
                    )

    # -----------------------------------------------------
    # Additional settings ingeklapt
    # -----------------------------------------------------

    if extra_fields:
        with st.expander("Additional settings", expanded=False):
            for field_name, rule in extra_fields:
                field_type = str(rule.get("type", "text")).lower()
                label = rule.get("label", field_name.replace("_", " ").title())

                if field_type == "select_number":
                    options = rule.get("options", [])
                    default = rule.get("default")
                    try:
                        default_index = options.index(default)
                    except ValueError:
                        default_index = 0

                    field_values[field_name] = st.selectbox(
                        label,
                        options=options,
                        index=default_index,
                        key=f"{workflow_key_prefix}_{field_name}",
                    )

                elif field_type == "select":
                    options = rule.get("options", [])
                    default = rule.get("default")
                    try:
                        default_index = options.index(default)
                    except ValueError:
                        default_index = 0

                    field_values[field_name] = st.selectbox(
                        label,
                        options=options,
                        index=default_index,
                        key=f"{workflow_key_prefix}_{field_name}",
                    )

                elif field_type == "integer":
                    minimum = max(
                        int(rule.get("min", -JS_SAFE_INTEGER)),
                        -JS_SAFE_INTEGER,
                    )
                    maximum = min(
                        int(rule.get("max", JS_SAFE_INTEGER)),
                        JS_SAFE_INTEGER,
                    )
                    default = min(
                        max(int(rule.get("default", 0)), minimum),
                        maximum,
                    )

                    field_values[field_name] = int(
                        st.number_input(
                            label,
                            min_value=minimum,
                            max_value=maximum,
                            value=default,
                            step=1,
                            key=f"{workflow_key_prefix}_{field_name}",
                        )
                    )

                elif field_type == "number":
                    field_values[field_name] = float(
                        st.number_input(
                            label,
                            min_value=float(rule.get("min", 0.0)),
                            max_value=float(rule.get("max", 1_000_000.0)),
                            value=float(rule.get("default", 0.0)),
                            key=f"{workflow_key_prefix}_{field_name}",
                        )
                    )

                else:
                    field_values[field_name] = st.text_input(
                        label,
                        value=str(rule.get("default", "")),
                        key=f"{workflow_key_prefix}_{field_name}",
                    )

    # -----------------------------------------------------
    # Reference images
    # -----------------------------------------------------

    if image_fields:
        st.markdown("##### Reference images")
        image_columns = st.columns(min(len(image_fields), 3))

        for index, (field_name, rule) in enumerate(image_fields):
            with image_columns[index % len(image_columns)]:
                label = rule.get("label", field_name.replace("_", " ").title())
                uploaded = st.file_uploader(
                    label,
                    type=["png", "jpg", "jpeg", "webp"],
                    key=f"{workflow_key_prefix}_{field_name}",
                )

                if uploaded:
                    image_uploads[field_name] = uploaded
                    field_values[field_name] = uploaded.name
                    st.image(uploaded, width=160)

    required_image_fields = [name for name, _ in image_fields]
    required_images_ready = bool(workflow_mapping) and all(
        name in image_uploads for name in required_image_fields
    )

    # -----------------------------------------------------
    # Idee + model + generatie
    # -----------------------------------------------------

    st.markdown("##### H3 Prompt")

    idea = st.text_area(
        "What would you like to create?",
        height=110,
        placeholder=(
            "Describe the scene, action, characters, camera, lighting, sound, atmosphere "
            "and any exact dialogue…"
        ),
    )

    try:
        models = lm_client.list_models()
        model = (
            st.selectbox("LM Studio model", models, key="lmstudio_model")
            if models
            else None
        )
    except LMStudioError as exc:
        model = None
        st.warning(str(exc))

    can_generate = bool(
        idea.strip()
        and model
        and workflow_mapping
        and required_images_ready
    )

    if st.button(
        "Generate H3 prompt",
        type="primary",
        disabled=not can_generate,
        use_container_width=True,
    ):
        try:
            h3_mode = workflow_mapping["h3_mode"]
            has_image = bool(image_uploads)
            target_duration = field_values.get("duration")
            system_prompt = get_h3_system_prompt(
                mode=h3_mode,
                has_image=has_image,
                duration_seconds=target_duration,
            )

            enhancer_images: list[tuple[bytes, str | None]] = []
            for field_name, rule in workflow_mapping.get("fields", {}).items():
                if str(rule.get("type", "")).lower() != "image":
                    continue
                uploaded = image_uploads.get(field_name)
                if uploaded is not None:
                    enhancer_images.append((uploaded.getvalue(), uploaded.type))

            with st.spinner(f"{model} is loading in LM Studio…"):
                instance_id = run_with_live_gpu(
                    lambda: lm_client.load_model(model),
                    interval=1.0,
                )

            st.session_state.model_instance_id = instance_id
            st.session_state.model_name = model
            st.session_state.model_unloaded = False

            with st.spinner("LM Studio is generating the MiniMax H3 prompt…"):
                generated = run_with_live_gpu(
                    lambda: lm_client.generate_prompt(
                        idea,
                        model,
                        system_prompt,
                        APP_CONFIG["temperature"],
                        images=enhancer_images or None,
                    ),
                    interval=1.0,
                )

            st.session_state.prompt = generated.text
            st.session_state.model_instance_id = generated.instance_id or instance_id
            st.session_state.model_name = generated.model
            st.session_state.prompt_approved = False

            # Kopieer de instance-id eerst uit Streamlit session_state.
            # De worker-thread mag session_state zelf niet aanspreken.
            instance_to_unload = st.session_state.get("model_instance_id")

            with st.spinner("Unloading LM Studio model…"):
                if instance_to_unload:
                    run_with_live_gpu(
                        lambda: lm_client.unload_model(instance_to_unload),
                        interval=0.5,
                    )

            st.session_state.model_unloaded = True
            st.session_state.model_instance_id = None
            st.success("Prompt ready. LM Studio model has been unloaded.")

        except (LMStudioError, ValueError) as exc:
            st.error(str(exc))

    if workflow_mapping and required_image_fields and not required_images_ready:
        st.info("Upload all required reference images first.")

    # -----------------------------------------------------
    # Promptcontrole
    # -----------------------------------------------------

    edited_prompt = st.text_area(
        "Final prompt",
        value=st.session_state.get("prompt", ""),
        height=280,
    )

    previous_prompt = st.session_state.get("prompt", "")
    if edited_prompt != previous_prompt:
        st.session_state.prompt_approved = False

    st.session_state.prompt = edited_prompt
    field_values["prompt"] = edited_prompt

    approve_col, render_col = st.columns(2)

    with approve_col:
        if st.button(
            "Approve prompt",
            disabled=not edited_prompt.strip(),
            use_container_width=True,
        ):
            st.session_state.prompt_approved = True

            # Een handmatig ingevoerde/geplakte H3-prompt heeft geen
            # LM Studio-generatie nodig. Als er geen LM Studio-instance
            # actief is, mag de prompt na goedkeuring rechtstreeks naar
            # ComfyUI.
            if not st.session_state.get("model_instance_id"):
                st.session_state.model_unloaded = True

            st.success("Prompt approved.")
            st.rerun()

    # -----------------------------------------------------
    # Workflow laden en configureren
    # -----------------------------------------------------

    workflow = None
    configured = None

    if selected_workflow_path and workflow_mapping:
        try:
            workflow_bytes = selected_workflow_path.read_bytes()
            workflow = load_api_workflow(workflow_bytes)
            configured = apply_mapping(workflow, workflow_mapping, field_values)
        except (ComfyUIError, OSError, json.JSONDecodeError) as exc:
            configured = None
            st.error(f"Workflow could not be loaded: {exc}")

    can_queue = bool(
        configured
        and workflow
        and workflow_mapping
        and edited_prompt.strip()
        and required_images_ready
        and st.session_state.get("model_unloaded")
        and st.session_state.get("prompt_approved")
    )

    with render_col:
        render_clicked = st.button(
            "Send to ComfyUI",
            type="primary",
            disabled=not can_queue,
            use_container_width=True,
        )

    if configured and edited_prompt.strip() and not st.session_state.get("prompt_approved"):
        st.caption("Review and approve the prompt before rendering.")

    # -----------------------------------------------------
    # Renderen
    # -----------------------------------------------------

    if render_clicked:
        try:
            with st.spinner("Uploading images and sending workflow to ComfyUI…"):
                final_values = dict(field_values)

                if "seed" in final_values and int(final_values["seed"]) == 0:
                    final_values["seed"] = random.randint(1, JS_SAFE_INTEGER)

                for field_name, uploaded in image_uploads.items():
                    final_values[field_name] = comfy_client.upload_image(
                        uploaded.name,
                        uploaded.getvalue(),
                        uploaded.type,
                    )

                final_workflow = apply_mapping(
                    workflow,
                    workflow_mapping,
                    final_values,
                )
                prompt_id = comfy_client.queue_prompt(final_workflow)
                refresh_gpu_monitor_now()

            st.session_state.last_prompt_id = prompt_id
            st.session_state.last_workflow = selected_workflow_path.name
            st.session_state.last_render_metadata = {
                "workflow": selected_workflow_path.name,
                "prompt_id": prompt_id,
                "values": dict(final_values),
            }

            status_box = st.empty()
            progress = st.progress(0)

            with st.spinner("ComfyUI is rendering the video…"):
                output_info = None
                checks = 0

                while output_info is None:
                    output_info = comfy_client.get_completed_output(prompt_id)

                    if output_info is None:
                        checks += 1
                        progress.progress(min(95, 5 + checks))
                        status_box.info("Rendering in ComfyUI…")
                        refresh_gpu_monitor_now()
                        time.sleep(1)

            progress.progress(100)
            status_box.success("Render complete.")
            refresh_gpu_monitor_now()

            video_bytes = comfy_client.download_output(
                output_info["filename"],
                output_info.get("subfolder", ""),
                output_info.get("type", "output"),
            )

            st.session_state.last_video_bytes = video_bytes
            st.session_state.last_video_name = output_info["filename"]

            execution_seconds = comfy_client.get_execution_seconds(prompt_id)
            st.session_state["last_render_metadata"]["execution_seconds"] = execution_seconds
            st.session_state["last_render_metadata"]["video_info"] = probe_video_bytes(
                video_bytes,
                output_info["filename"],
            )

            st.rerun()

        except ComfyUIError as exc:
            st.error(str(exc))


# =========================================================
# Rechterkolom: resultaat
# =========================================================

with right_col:
    st.subheader("Render result")

    if st.session_state.get("last_video_bytes"):
        video_bytes = st.session_state["last_video_bytes"]
        video_name = st.session_state.get("last_video_name", "ComfyUI video")
        render_metadata = st.session_state.get("last_render_metadata", {})
        values = render_metadata.get("values", {})
        video_info = render_metadata.get("video_info", {})

        st.video(video_bytes)
        st.caption(video_name)

        width = video_info.get("width")
        height = video_info.get("height")
        resolution_text = f"{width} × {height} px" if width and height else "-"

        duration = video_info.get("duration_seconds")
        duration_text = (
            f"{duration:.2f} sec"
            if duration is not None
            else (
                f"{float(values['duration']):g} sec"
                if values.get("duration") is not None
                else "-"
            )
        )

        format_text = video_info.get("format", "-")
        file_size_text = human_file_size(video_info.get("file_size_bytes"))

        meta1, meta2 = st.columns(2)
        with meta1:
            st.markdown(f"**Video:** {resolution_text}")
            st.markdown(f"**Duration:** {duration_text}")
            st.markdown(f"**Seed:** {values.get('seed', '-')}")
        with meta2:
            st.markdown(f"**Aspect ratio:** {values.get('aspect_ratio', '-')}")
            st.markdown(f"**Format:** {format_text}")
            st.markdown(f"**File:** {file_size_text}")

        execution_seconds = render_metadata.get("execution_seconds")
        if execution_seconds is not None:
            st.caption(f"Render time: {execution_seconds:.2f} sec")

        with st.expander("Render metadata", expanded=False):
            st.write(f"**Workflow:** {render_metadata.get('workflow', '-')}")
            st.write(f"**Prompt ID:** {render_metadata.get('prompt_id', '-')}")

            for field_name, value in values.items():
                if field_name in {
                    "prompt",
                    "seed",
                    "duration",
                    "aspect_ratio",
                }:
                    continue
                pretty_name = field_name.replace("_", " ").title()
                st.write(f"**{pretty_name}:** {value}")

            if values.get("prompt"):
                st.markdown("**Final H3 prompt:**")
                st.code(values["prompt"], language="text")

    else:
        st.info(
            "The most recently rendered video will appear here. "
            "The previous result remains visible while you adjust a new prompt."
        )
