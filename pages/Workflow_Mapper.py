from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from pathlib import Path

import streamlit as st


# ============================================================
# ComfyMax Workflow Mapper - Integrated ComfyMax page
# ============================================================
#
# Doel:
# - ComfyUI API workflow (.json) uploaden
# - Nodes en inputs analyseren
# - Waarschijnlijke ComfyMax-besturing automatisch voorstellen
# - Gebruiker laat elke mapping controleren/corrigeren
# - Een ComfyMax-compatible mapping JSON genereren
#
# Dit script wijzigt NIETS aan ComfyMax.
# Het is een aparte testtool.
#
# Start:
#   streamlit run workflow_mapper_test.py
#
# Belangrijk:
# Gebruik een ComfyUI workflow in API-formaat:
#   Save (API Format)
# ============================================================


JS_SAFE_INTEGER = (1 << 53) - 1


# ============================================================
# Bekende ComfyMax velden
# ============================================================

FIELD_DEFINITIONS: dict[str, dict[str, Any]] = {
    "prompt": {
        "label": "Prompt",
        "type": "prompt",
        "preferred_inputs": ["text", "prompt", "positive", "value", "caption"],
        "preferred_classes": [
            "PrimitiveStringMultiline",
            "PrimitiveString",
            "CLIPTextEncode",
            "Text Multiline",
        ],
    },
    "duration": {
        "label": "Duration",
        "type": "select_number",
        "preferred_inputs": ["duration", "seconds", "length", "value"],
        "preferred_classes": [
            "PrimitiveFloat",
            "Float",
            "FloatConstant",
        ],
        "default": 5.0,
        "options": [5.0, 10.0, 15.0, 20.0],
    },
    "resolution": {
        "label": "Resolution",
        "type": "select_number",
        "preferred_inputs": [
            "megapixels",
            "megapixel",
            "mp",
            "resolution",
            "value",
        ],
        "preferred_classes": [
            "PrimitiveFloat",
            "Float",
            "FloatConstant",
        ],
        "default": 0.4,
        "options": [0.4, 0.5, 0.7, 1.0],
    },
    "aspect_ratio": {
        "label": "Aspect ratio",
        "type": "select",
        "preferred_inputs": ["aspect_ratio", "ratio"],
        "preferred_classes": [
            "ResolutionSelector",
            "AspectRatio",
            "AspectRatioSelector",
        ],
        "default": "1:1 (Square)",
        "options": [
            "1:1 (Square)",
            "2:3 (Portrait Photo)",
            "3:2 (Photo)",
            "3:4 (Portrait Standard)",
            "4:3 (Standard)",
            "9:16 (Portrait Widescreen)",
            "16:9 (Widescreen)",
            "21:9 (Ultrawide)",
        ],
    },
    "steps": {
        "label": "Steps",
        "type": "integer",
        "preferred_inputs": ["steps", "value"],
        "preferred_classes": [
            "PrimitiveInt",
            "Int",
            "Integer",
            "KSampler",
            "KSamplerAdvanced",
        ],
        "default": 4,
        "min": 0,
        "max": 30,
    },
    "seed": {
        "label": "Seed",
        "type": "integer",
        "preferred_inputs": ["noise_seed", "seed", "value"],
        "preferred_classes": [
            "RandomNoise",
            "KSampler",
            "KSamplerAdvanced",
            "PrimitiveInt",
            "Int",
        ],
        "default": 0,
        "min": 0,
        "max": JS_SAFE_INTEGER,
    },
}


MODEL_FIELDS: dict[str, dict[str, Any]] = {
    "unet_model": {
        "label": "MiniMax H3 video model",
        "type": "model_setting",
        "setting": "minimax_h3.unet",
        "preferred_inputs": ["unet_name"],
        "preferred_classes": [
            "UNETLoader",
            "UnetLoaderGGUF",
            "UnetLoader",
            "Load Diffusion Model",
        ],
    },
    "video_vae": {
        "label": "Video VAE",
        "type": "model_setting",
        "setting": "minimax_h3.video_vae",
        "preferred_inputs": ["vae_name"],
        "preferred_classes": [
            "VAELoader",
        ],
    },
    "audio_vae": {
        "label": "Audio VAE",
        "type": "model_setting",
        "setting": "minimax_h3.audio_vae",
        "preferred_inputs": ["vae_name"],
        "preferred_classes": [
            "VAELoader",
        ],
    },
    "text_encoder": {
        "label": "Text encoder / CLIP",
        "type": "model_setting",
        "setting": "minimax_h3.clip",
        "preferred_inputs": ["clip_name"],
        "preferred_classes": [
            "CLIPLoader",
            "DualCLIPLoader",
            "TripleCLIPLoader",
        ],
    },
}


IMAGE_INPUT_NAMES = [
    "image",
    "reference_image",
    "ref_image",
    "start_image",
    "subject_image",
    "picture",
]

IMAGE_CLASS_HINTS = [
    "loadimage",
    "image loader",
    "imageinput",
    "image input",
]


# ============================================================
# Datatypes
# ============================================================

@dataclass
class Candidate:
    node_id: str
    class_type: str
    input_name: str
    value: Any
    score: int
    reason: str


# ============================================================
# Workflow laden en controleren
# ============================================================

def load_api_workflow(raw: bytes) -> dict[str, Any]:
    try:
        workflow = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("The selected file is not valid JSON.") from exc

    if not isinstance(workflow, dict) or not workflow:
        raise ValueError("The workflow must be a non-empty JSON object.")

    if "nodes" in workflow:
        raise ValueError(
            "This appears to be a normal ComfyUI editor workflow. "
            "Export it using 'Save (API Format)'."
        )

    invalid_nodes = []
    for node_id, node in workflow.items():
        if not isinstance(node, dict) or "class_type" not in node:
            invalid_nodes.append(str(node_id))

    if invalid_nodes:
        shown = ", ".join(invalid_nodes[:8])
        raise ValueError(
            f"This does not look like a valid API workflow. "
            f"'class_type' is missing for node(s): {shown}"
        )

    return workflow


# ============================================================
# Node helpers
# ============================================================

def get_node_title(node: dict[str, Any]) -> str:
    meta = node.get("_meta", {})
    if isinstance(meta, dict):
        return str(meta.get("title", "") or "")
    return ""


def stringify_value(value: Any, max_len: int = 80) -> str:
    if isinstance(value, list):
        text = json.dumps(value, ensure_ascii=False)
    elif isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)

    text = text.replace("\n", " ")
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return text


def is_connection(value: Any) -> bool:
    """
    ComfyUI API connections are commonly stored as:
        ["node_id", output_index]
    Such values are outputs from another node and are normally not
    directly editable controls.
    """
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[1], int)
        and isinstance(value[0], (str, int))
    )


def node_rows(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for node_id, node in workflow.items():
        class_type = str(node.get("class_type", ""))
        title = get_node_title(node)
        inputs = node.get("inputs", {})

        if not isinstance(inputs, dict):
            inputs = {}

        editable_inputs = [
            name
            for name, value in inputs.items()
            if not is_connection(value)
        ]

        rows.append(
            {
                "Node ID": str(node_id),
                "Class type": class_type,
                "Title": title,
                "Editable inputs": ", ".join(editable_inputs),
                "All inputs": ", ".join(inputs.keys()),
            }
        )

    return rows


def all_editable_candidates(workflow: dict[str, Any]) -> list[Candidate]:
    candidates: list[Candidate] = []

    for node_id, node in workflow.items():
        class_type = str(node.get("class_type", ""))
        inputs = node.get("inputs", {})

        if not isinstance(inputs, dict):
            continue

        for input_name, value in inputs.items():
            if is_connection(value):
                continue

            candidates.append(
                Candidate(
                    node_id=str(node_id),
                    class_type=class_type,
                    input_name=str(input_name),
                    value=value,
                    score=0,
                    reason="Editable workflow input",
                )
            )

    return candidates


# ============================================================
# Detectie / scoring
# ============================================================

def score_candidate(
    candidate: Candidate,
    definition: dict[str, Any],
    field_name: str,
) -> Candidate:
    score = 0
    reasons: list[str] = []

    input_lower = candidate.input_name.lower()
    class_lower = candidate.class_type.lower()

    preferred_inputs = [
        str(x).lower()
        for x in definition.get("preferred_inputs", [])
    ]

    preferred_classes = [
        str(x).lower()
        for x in definition.get("preferred_classes", [])
    ]

    # Inputnaam is de sterkste aanwijzing.
    if input_lower in preferred_inputs:
        position = preferred_inputs.index(input_lower)
        input_score = max(55 - (position * 6), 25)
        score += input_score
        reasons.append(f"input '{candidate.input_name}' matches")

    # Gedeeltelijke input match.
    for preferred in preferred_inputs:
        if preferred and preferred in input_lower and input_lower != preferred:
            score += 12
            reasons.append(f"input contains '{preferred}'")
            break

    # Class type hint.
    for preferred in preferred_classes:
        if preferred and preferred in class_lower:
            score += 25
            reasons.append(f"class matches '{preferred}'")
            break

    # Waardetype als extra hint.
    value = candidate.value

    if field_name in {"duration", "resolution"}:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            score += 8
            reasons.append("numeric value")

    elif field_name in {"steps", "seed"}:
        if isinstance(value, int) and not isinstance(value, bool):
            score += 8
            reasons.append("integer value")

    elif field_name == "aspect_ratio":
        if isinstance(value, str) and ":" in value:
            score += 15
            reasons.append("value looks like aspect ratio")

    elif field_name == "prompt":
        if isinstance(value, str):
            score += 5
            reasons.append("text value")

        # Lange tekstvelden zijn waarschijnlijker prompts.
        if isinstance(value, str) and len(value) > 30:
            score += 8
            reasons.append("long text value")

    return Candidate(
        node_id=candidate.node_id,
        class_type=candidate.class_type,
        input_name=candidate.input_name,
        value=candidate.value,
        score=score,
        reason=", ".join(reasons) if reasons else "No strong match",
    )


def find_candidates(
    workflow: dict[str, Any],
    field_name: str,
    definition: dict[str, Any],
) -> list[Candidate]:
    result = [
        score_candidate(candidate, definition, field_name)
        for candidate in all_editable_candidates(workflow)
    ]

    result.sort(
        key=lambda item: (
            item.score,
            item.node_id,
            item.input_name,
        ),
        reverse=True,
    )

    return result


def image_candidates(workflow: dict[str, Any]) -> list[Candidate]:
    found: list[Candidate] = []

    for candidate in all_editable_candidates(workflow):
        input_lower = candidate.input_name.lower()
        class_lower = candidate.class_type.lower()

        score = 0
        reasons: list[str] = []

        if input_lower in IMAGE_INPUT_NAMES:
            score += 60
            reasons.append(f"input '{candidate.input_name}' looks like an image")

        for hint in IMAGE_CLASS_HINTS:
            if hint in class_lower:
                score += 30
                reasons.append(f"class looks like image loader ({hint})")
                break

        # Een LoadImage node heeft doorgaans een string filename.
        if isinstance(candidate.value, str):
            lower_value = candidate.value.lower()
            if lower_value.endswith(
                (".png", ".jpg", ".jpeg", ".webp", ".bmp")
            ):
                score += 25
                reasons.append("value looks like image filename")

        if score > 0:
            found.append(
                Candidate(
                    node_id=candidate.node_id,
                    class_type=candidate.class_type,
                    input_name=candidate.input_name,
                    value=candidate.value,
                    score=score,
                    reason=", ".join(reasons),
                )
            )

    found.sort(
        key=lambda item: (
            item.score,
            numeric_sort_key(item.node_id),
            item.input_name,
        ),
        reverse=True,
    )

    return found


def numeric_sort_key(value: str) -> tuple[int, str]:
    """
    Sorteert normale node IDs numeriek waar mogelijk.
    IDs zoals '914:127' blijven bruikbaar.
    """
    try:
        return int(value), value
    except ValueError:
        try:
            return int(value.split(":")[0]), value
        except ValueError:
            return -1, value


# ============================================================
# UI helpers
# ============================================================

def candidate_label(candidate: Candidate) -> str:
    return (
        f"Node {candidate.node_id} | "
        f"{candidate.class_type} | "
        f"{candidate.input_name} = "
        f"{stringify_value(candidate.value)}"
    )


def none_candidate() -> Candidate:
    return Candidate(
        node_id="",
        class_type="",
        input_name="",
        value=None,
        score=-1,
        reason="Not mapped",
    )


def default_candidate_index(candidates: list[Candidate]) -> int:
    if not candidates:
        return 0

    # index 0 is "Not mapped"
    # Alleen automatisch selecteren als de detectie redelijk sterk is.
    best = candidates[0]
    if best.score >= 50:
        return 1

    return 0


def select_candidate(
    field_name: str,
    label: str,
    candidates: list[Candidate],
    help_text: str | None = None,
) -> Candidate | None:
    options = [none_candidate()] + candidates

    selected = st.selectbox(
        label,
        options=options,
        index=default_candidate_index(candidates),
        format_func=lambda c: "— Not mapped —"
        if not c.node_id
        else candidate_label(c),
        key=f"map_{field_name}",
        help=help_text,
    )

    if not selected.node_id:
        return None

    st.caption(
        f"Suggestion score: {selected.score} · {selected.reason}"
    )

    return selected


def make_basic_rule(
    candidate: Candidate,
    field_name: str,
    definition: dict[str, Any],
) -> dict[str, Any]:
    rule: dict[str, Any] = {
        "node_id": candidate.node_id,
        "input": candidate.input_name,
        "type": definition["type"],
        "label": definition["label"],
    }

    for key in (
        "default",
        "options",
        "min",
        "max",
        "setting",
    ):
        if key in definition:
            rule[key] = definition[key]

    # Voor defaults gebruiken we indien mogelijk de actuele waarde
    # uit de workflow, zolang die past bij het type.
    value = candidate.value

    if field_name == "duration":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            numeric = float(value)
            rule["default"] = numeric

            options = list(rule.get("options", []))
            if numeric not in options:
                options.append(numeric)
                options = sorted(set(options))
            rule["options"] = options

    elif field_name == "resolution":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            numeric = float(value)
            rule["default"] = numeric

            options = list(rule.get("options", []))
            if numeric not in options:
                options.append(numeric)
                options = sorted(set(options))
            rule["options"] = options

    elif field_name in {"steps", "seed"}:
        if isinstance(value, int) and not isinstance(value, bool):
            rule["default"] = int(value)

    elif field_name == "aspect_ratio":
        if isinstance(value, str) and value:
            rule["default"] = value

            options = list(rule.get("options", []))
            if value not in options:
                options.insert(0, value)
            rule["options"] = options

    return rule


def make_image_rule(
    candidate: Candidate,
    index: int,
) -> dict[str, Any]:
    return {
        "node_id": candidate.node_id,
        "input": candidate.input_name,
        "type": "image",
        "label": f"Reference image {index}",
    }


def make_model_rule(
    candidate: Candidate,
    definition: dict[str, Any],
) -> dict[str, Any]:
    return {
        "node_id": candidate.node_id,
        "input": candidate.input_name,
        "type": "model_setting",
        "setting": definition["setting"],
        "label": definition["label"],
    }


# ============================================================
# Mapping controle
# ============================================================

def validate_mapping(
    workflow: dict[str, Any],
    mapping: dict[str, Any],
) -> list[str]:
    problems: list[str] = []

    fields = mapping.get("fields", {})
    if not fields:
        problems.append("The mapping has no fields.")
        return problems

    if "prompt" not in fields:
        problems.append("Prompt is not mapped.")

    for field_name, rule in fields.items():
        node_id = str(rule.get("node_id", ""))
        input_name = str(rule.get("input", ""))

        if node_id not in workflow:
            problems.append(
                f"{field_name}: node {node_id} does not exist."
            )
            continue

        inputs = workflow[node_id].get("inputs", {})
        if not isinstance(inputs, dict):
            problems.append(
                f"{field_name}: node {node_id} has no valid inputs object."
            )
            continue

        if input_name not in inputs:
            problems.append(
                f"{field_name}: input '{input_name}' does not exist "
                f"on node {node_id}."
            )

    return problems


# ============================================================
# v0.2 compatibility analysis
# ============================================================

def confidence_label(score: int) -> str:
    if score >= 80:
        return "High"
    if score >= 55:
        return "Good"
    if score >= 35:
        return "Possible"
    return "Low"


def compatibility_report(
    workflow: dict[str, Any],
    mapping: dict[str, Any],
    selected_fields: dict[str, tuple[Candidate, dict[str, Any]]],
    selected_images: list[Candidate],
    selected_models: dict[str, tuple[Candidate, dict[str, Any]]],
) -> dict[str, Any]:
    problems = validate_mapping(workflow, mapping)
    fields = mapping.get("fields", {})

    report: dict[str, Any] = {
        "status": "Compatible" if not problems else "Needs attention",
        "problems": problems,
        "mapped_fields": len(fields),
        "workflow_nodes": len(workflow),
        "prompt": "prompt" in fields,
        "reference_images": len(
            [
                rule
                for rule in fields.values()
                if rule.get("type") == "image"
            ]
        ),
        "model_settings": len(
            [
                rule
                for rule in fields.values()
                if rule.get("type") == "model_setting"
            ]
        ),
        "details": [],
    }

    for field_name, (candidate, definition) in selected_fields.items():
        report["details"].append(
            {
                "Field": definition["label"],
                "Mapped": True,
                "Node": candidate.node_id,
                "Input": candidate.input_name,
                "Class": candidate.class_type,
                "Confidence": confidence_label(candidate.score),
                "Score": candidate.score,
            }
        )

    for index, candidate in enumerate(selected_images, start=1):
        report["details"].append(
            {
                "Field": f"Reference image {index}",
                "Mapped": True,
                "Node": candidate.node_id,
                "Input": candidate.input_name,
                "Class": candidate.class_type,
                "Confidence": confidence_label(candidate.score),
                "Score": candidate.score,
            }
        )

    for field_name, (candidate, definition) in selected_models.items():
        report["details"].append(
            {
                "Field": definition["label"],
                "Mapped": True,
                "Node": candidate.node_id,
                "Input": candidate.input_name,
                "Class": candidate.class_type,
                "Confidence": confidence_label(candidate.score),
                "Score": candidate.score,
            }
        )

    return report


def duplicate_mapping_problems(mapping: dict[str, Any]) -> list[str]:
    """
    Detecteert wanneer meerdere ComfyMax-velden exact dezelfde node/input
    gebruiken. Soms is dat legitiem, maar meestal verdient het controle.
    """
    seen: dict[tuple[str, str], str] = {}
    problems: list[str] = []

    for field_name, rule in mapping.get("fields", {}).items():
        key = (
            str(rule.get("node_id", "")),
            str(rule.get("input", "")),
        )

        if not all(key):
            continue

        previous = seen.get(key)
        if previous is not None:
            problems.append(
                f"{field_name} and {previous} both map to "
                f"node {key[0]} / input '{key[1]}'."
            )
        else:
            seen[key] = field_name

    return problems


# ============================================================
# Streamlit pagina
# ============================================================

st.set_page_config(
    page_title="ComfyMax Workflow Mapper",
    page_icon="🧩",
    layout="wide",
)

st.title("🧩 Workflow Mapper")
st.caption(
    "Analyze a ComfyUI API workflow, create its mapping, validate it, "
    "and add it directly to ComfyMax."
)

st.info(
    "Upload a ComfyUI workflow exported with Save (API Format). "
    "Review the suggested controls before adding the workflow to ComfyMax."
)

uploaded = st.file_uploader(
    "Upload ComfyUI API workflow",
    type=["json"],
    help=(
        "In ComfyUI use the API-format export. "
        "A normal editor workflow is not accepted."
    ),
)

if uploaded is None:
    st.stop()

try:
    workflow = load_api_workflow(uploaded.getvalue())
except ValueError as exc:
    st.error(str(exc))
    st.stop()

st.success(
    f"Workflow loaded successfully: {uploaded.name} · "
    f"{len(workflow)} nodes"
)


# ============================================================
# Workflow overzicht
# ============================================================

with st.expander("1. Workflow node overview", expanded=False):
    rows = node_rows(workflow)
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# Basisinformatie mapping
# ============================================================

st.subheader("2. Mapping information")

left, middle, right = st.columns(3)

with left:
    mapping_name = st.text_input(
        "Mapping name",
        value=uploaded.name.rsplit(".", 1)[0],
    )

with middle:
    h3_mode = st.selectbox(
        "H3 mode",
        options=[
            "ref2va",
            "fl2v",
            "i2v",
            "t2v",
        ],
        index=0,
        help=(
            "For current reference-image H3 workflows, "
            "REF2VA is normally the correct mode."
        ),
    )

with right:
    description = st.text_input(
        "Description",
        value="ComfyMax custom workflow mapping.",
    )


# ============================================================
# Hoofdvelden
# ============================================================

st.subheader("3. Main controls")

auto_preview_rows: list[dict[str, Any]] = []

for preview_field in (
    "prompt",
    "duration",
    "resolution",
    "aspect_ratio",
    "steps",
    "seed",
):
    preview_definition = FIELD_DEFINITIONS[preview_field]
    preview_candidates = find_candidates(
        workflow,
        preview_field,
        preview_definition,
    )

    if preview_candidates:
        best = preview_candidates[0]
        auto_preview_rows.append(
            {
                "Control": preview_definition["label"],
                "Suggested node": best.node_id,
                "Input": best.input_name,
                "Class": best.class_type,
                "Confidence": confidence_label(best.score),
                "Score": best.score,
            }
        )
    else:
        auto_preview_rows.append(
            {
                "Control": preview_definition["label"],
                "Suggested node": "",
                "Input": "",
                "Class": "",
                "Confidence": "None",
                "Score": 0,
            }
        )

with st.expander(
    "Automatic mapping suggestions",
    expanded=True,
):
    st.dataframe(
        auto_preview_rows,
        use_container_width=True,
        hide_index=True,
    )


st.caption(
    "The assistant suggests likely nodes. Review every selection. "
    "Choose 'Not mapped' for controls you do not want ComfyMax to change."
)

selected_fields: dict[str, tuple[Candidate, dict[str, Any]]] = {}

for field_name in (
    "prompt",
    "duration",
    "resolution",
    "aspect_ratio",
    "steps",
    "seed",
):
    definition = FIELD_DEFINITIONS[field_name]
    candidates = find_candidates(
        workflow,
        field_name,
        definition,
    )

    # Houd de interface bruikbaar.
    # Voor prompt tonen we wat meer opties omdat custom text nodes sterk variëren.
    max_items = 30 if field_name == "prompt" else 20
    candidates = candidates[:max_items]

    selected = select_candidate(
        field_name,
        definition["label"],
        candidates,
    )

    if selected is not None:
        selected_fields[field_name] = (
            selected,
            definition,
        )


# ============================================================
# Reference images
# ============================================================

st.subheader("4. Reference images")

detected_images = image_candidates(workflow)

if detected_images:
    st.caption(
        f"{len(detected_images)} possible editable image input(s) detected."
    )
else:
    st.warning(
        "No obvious editable reference-image inputs were detected. "
        "You can still select them manually below."
    )

all_editable = all_editable_candidates(workflow)

# Voeg ook alle overige inputs toe als fallback zodat exotische custom nodes
# toch handmatig gekozen kunnen worden.
image_option_map: dict[tuple[str, str], Candidate] = {}

for candidate in detected_images + all_editable:
    key = (candidate.node_id, candidate.input_name)
    if key not in image_option_map:
        image_option_map[key] = candidate

image_options = list(image_option_map.values())

image_options.sort(
    key=lambda c: (
        c.score,
        numeric_sort_key(c.node_id),
        c.input_name,
    ),
    reverse=True,
)

suggested_image_count = len(
    [c for c in detected_images if c.score >= 50]
)

default_image_count = min(
    max(suggested_image_count, 1 if detected_images else 0),
    9,
)

reference_count = st.number_input(
    "How many reference images should ComfyMax control?",
    min_value=0,
    max_value=20,
    value=int(default_image_count),
    step=1,
)

selected_images: list[Candidate] = []

used_image_keys: set[tuple[str, str]] = set()

for index in range(1, int(reference_count) + 1):
    options = [none_candidate()] + image_options

    default_index = 0

    # Probeer voor iedere afbeelding een andere goede kandidaat te kiezen.
    for option_index, candidate in enumerate(
        image_options,
        start=1,
    ):
        key = (candidate.node_id, candidate.input_name)
        if candidate.score >= 50 and key not in used_image_keys:
            default_index = option_index
            break

    selected = st.selectbox(
        f"Reference image {index}",
        options=options,
        index=default_index,
        format_func=lambda c: "— Not mapped —"
        if not c.node_id
        else candidate_label(c),
        key=f"reference_image_{index}",
    )

    if selected.node_id:
        selected_images.append(selected)
        used_image_keys.add(
            (selected.node_id, selected.input_name)
        )

        if selected.score > 0:
            st.caption(
                f"Suggestion score: {selected.score} · "
                f"{selected.reason}"
            )


# ============================================================
# Model settings
# ============================================================

st.subheader("5. Optional model mappings")

st.caption(
    "These mappings let ComfyMax use the model choices stored in Settings. "
    "Leave them unmapped when your workflow should keep its own model values."
)

selected_models: dict[str, tuple[Candidate, dict[str, Any]]] = {}

for field_name, definition in MODEL_FIELDS.items():
    candidates = find_candidates(
        workflow,
        field_name,
        definition,
    )

    # Alleen kandidaten met minimaal enige aanwijzing eerst tonen.
    strong = [c for c in candidates if c.score > 0]
    weak = [c for c in candidates if c.score <= 0]
    candidates = (strong + weak)[:20]

    selected = select_candidate(
        field_name,
        definition["label"],
        candidates,
    )

    if selected is not None:
        selected_models[field_name] = (
            selected,
            definition,
        )


# ============================================================
# Mapping bouwen
# ============================================================

mapping: dict[str, Any] = {
    "name": mapping_name.strip()
    or uploaded.name.rsplit(".", 1)[0],
    "description": description.strip()
    or "ComfyMax custom workflow mapping.",
    "h3_mode": h3_mode,
    "fields": {},
}

# Hoofdvelden
for field_name, (
    candidate,
    definition,
) in selected_fields.items():
    mapping["fields"][field_name] = make_basic_rule(
        candidate,
        field_name,
        definition,
    )

# Reference images
for image_index, candidate in enumerate(
    selected_images,
    start=1,
):
    mapping["fields"][f"picture_{image_index}"] = (
        make_image_rule(
            candidate,
            image_index,
        )
    )

# Model settings
for field_name, (
    candidate,
    definition,
) in selected_models.items():
    mapping["fields"][field_name] = make_model_rule(
        candidate,
        definition,
    )


# ============================================================
# Test / validatie
# ============================================================

st.subheader("6. Compatibility report")

problems = validate_mapping(
    workflow,
    mapping,
)

duplicate_problems = duplicate_mapping_problems(
    mapping,
)

all_problems = problems + duplicate_problems

report = compatibility_report(
    workflow,
    mapping,
    selected_fields,
    selected_images,
    selected_models,
)

summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

with summary_col1:
    st.metric(
        "Workflow nodes",
        report["workflow_nodes"],
    )

with summary_col2:
    st.metric(
        "Mapped fields",
        report["mapped_fields"],
    )

with summary_col3:
    st.metric(
        "Reference images",
        report["reference_images"],
    )

with summary_col4:
    st.metric(
        "Model settings",
        report["model_settings"],
    )

if problems:
    st.error(
        "Compatibility status: Mapping contains validation issues."
    )

    for problem in problems:
        st.write(f"❌ {problem}")

if duplicate_problems:
    st.warning(
        "The mapping contains one or more duplicate node/input selections. "
        "This may be intentional, but should be reviewed before using it in ComfyMax."
    )

    for warning in duplicate_problems:
        st.write(f"⚠️ {warning}")

if not problems and not duplicate_problems:
    st.success(
        "Compatibility status: Compatible"
    )
    st.write(
        "✅ All mapped node IDs and inputs exist in the uploaded workflow."
    )
    st.write(
        f"✅ Prompt: "
        f"{'mapped' if report['prompt'] else 'not mapped'}"
    )
    st.write(
        f"✅ Reference images: {report['reference_images']}"
    )
    st.write(
        f"✅ Model settings: {report['model_settings']}"
    )
    st.write(
        f"✅ H3 mode: {h3_mode}"
    )

if report["details"]:
    st.markdown("#### Mapping confidence")

    st.dataframe(
        report["details"],
        use_container_width=True,
        hide_index=True,
    )

    low_confidence = [
        row
        for row in report["details"]
        if row["Score"] < 35
    ]

    if low_confidence:
        st.info(
            "Some selected mappings have low confidence. "
            "They are valid node/input pairs, but should be reviewed manually."
        )


# ============================================================
# JSON resultaat
# ============================================================

st.subheader("7. Generated ComfyMax mapping")

mapping_json = json.dumps(
    mapping,
    indent=2,
    ensure_ascii=False,
)

st.code(
    mapping_json,
    language="json",
)

output_name = uploaded.name

download_label = (
    "⬇️ Download mapping JSON"
    if not all_problems
    else "⬇️ Download mapping JSON anyway"
)

st.download_button(
    download_label,
    data=mapping_json.encode("utf-8"),
    file_name=output_name,
    mime="application/json",
    type="primary",
)

if all_problems:
    st.caption(
        "The mapping can still be downloaded for testing. "
        "Review the warnings above before adding it to ComfyMax."
    )

st.caption(
    "For ComfyMax, the mapping filename must match the workflow filename. "
    "Example: workflows/my_workflow.json → "
    "config/workflow_mappings/my_workflow.json"
)


# ============================================================
# Add workflow directly to ComfyMax
# ============================================================

st.divider()
st.subheader("8. Add workflow to ComfyMax")

st.caption(
    "This installs both files required by ComfyMax: the original API workflow "
    "and the generated mapping JSON. Both files use the same filename."
)

# This file lives in ComfyMax/pages, so the application root is one level up.
COMFYMAX_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = COMFYMAX_ROOT / "workflows"
MAPPINGS_DIR = COMFYMAX_ROOT / "config" / "workflow_mappings"

root_checks = {
    "App.py": (COMFYMAX_ROOT / "App.py").exists(),
    "workflows": WORKFLOWS_DIR.exists(),
    "config/workflow_mappings": MAPPINGS_DIR.exists(),
}

check_cols = st.columns(3)

for col, (label, ok) in zip(check_cols, root_checks.items()):
    with col:
        st.write(f"{'✅' if ok else '❌'} {label}")

root_valid = all(root_checks.values())

if not root_valid:
    st.error(
        "The ComfyMax folder structure is incomplete. "
        "The Workflow Mapper expects App.py, workflows, and "
        "config/workflow_mappings in the ComfyMax installation."
    )

safe_filename = Path(uploaded.name).name
if not safe_filename.lower().endswith(".json"):
    safe_filename += ".json"

workflow_target = WORKFLOWS_DIR / safe_filename
mapping_target = MAPPINGS_DIR / safe_filename

workflow_exists = workflow_target.exists()
mapping_exists = mapping_target.exists()

st.write(f"Workflow: `workflows/{safe_filename}`")
st.write(f"Mapping: `config/workflow_mappings/{safe_filename}`")

if workflow_exists or mapping_exists:
    existing = []
    if workflow_exists:
        existing.append("workflow")
    if mapping_exists:
        existing.append("mapping")

    st.warning(
        "Existing file(s) detected: "
        + ", ".join(existing)
        + ". Nothing will be overwritten unless you explicitly allow it."
    )

overwrite_allowed = False

if workflow_exists or mapping_exists:
    overwrite_allowed = st.checkbox(
        "Allow replacing the existing workflow/mapping files",
        value=False,
        help=(
            "Enable this only when you intentionally want to replace "
            "the existing ComfyMax files."
        ),
    )

install_blockers: list[str] = []

if not root_valid:
    install_blockers.append("The ComfyMax folder structure is incomplete.")

if problems:
    install_blockers.extend(problems)

if (workflow_exists or mapping_exists) and not overwrite_allowed:
    install_blockers.append(
        "Existing files require overwrite confirmation."
    )

if duplicate_problems:
    st.info(
        "Duplicate mapping warnings do not block installation, "
        "but review them before continuing."
    )

if install_blockers:
    with st.expander("Why installation is currently blocked"):
        for blocker in install_blockers:
            st.write(f"• {blocker}")

install_clicked = st.button(
    "➕ Add workflow to ComfyMax",
    type="primary",
    disabled=bool(install_blockers),
    use_container_width=True,
)

if install_clicked:
    workflow_backup: bytes | None = None
    mapping_backup: bytes | None = None

    try:
        WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
        MAPPINGS_DIR.mkdir(parents=True, exist_ok=True)

        if workflow_target.exists():
            workflow_backup = workflow_target.read_bytes()

        if mapping_target.exists():
            mapping_backup = mapping_target.read_bytes()

        # Keep the uploaded API workflow exactly as supplied.
        workflow_target.write_bytes(uploaded.getvalue())

        # Write the mapping generated by the assistant.
        mapping_target.write_text(
            mapping_json,
            encoding="utf-8",
        )

        # Read both files back and validate the installed pair.
        installed_workflow = load_api_workflow(
            workflow_target.read_bytes()
        )
        installed_mapping = json.loads(
            mapping_target.read_text(encoding="utf-8")
        )

        installed_problems = validate_mapping(
            installed_workflow,
            installed_mapping,
        )

        if installed_problems:
            raise ValueError(
                "Installed mapping failed validation: "
                + "; ".join(installed_problems)
            )

        if workflow_target.name != mapping_target.name:
            raise ValueError(
                "Workflow and mapping filenames do not match."
            )

        st.success(
            f"Workflow added successfully: {safe_filename}"
        )

        st.write("✅ API workflow installed")
        st.write("✅ Mapping installed")
        st.write("✅ Matching filenames confirmed")
        st.write("✅ Installed mapping validated against the installed workflow")

        st.info(
            "The workflow is ready. Return to the main ComfyMax page. "
            "If it was already open in another browser tab, refresh that page "
            "so the workflow list is rebuilt."
        )

    except Exception as exc:
        # Roll back a partial installation where possible.
        try:
            if workflow_backup is not None:
                workflow_target.write_bytes(workflow_backup)
            elif workflow_target.exists():
                workflow_target.unlink()

            if mapping_backup is not None:
                mapping_target.write_bytes(mapping_backup)
            elif mapping_target.exists():
                mapping_target.unlink()
        except OSError:
            pass

        st.error(
            f"Could not install the workflow: {exc}"
        )
