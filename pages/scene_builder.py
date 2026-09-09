from __future__ import annotations

import json
from pathlib import Path

import streamlit as st


# ============================================================
# Paths
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
QUESTIONS_FILE = CONFIG_DIR / "scene_questions.json"


# ============================================================
# Page
# ============================================================

st.set_page_config(
    page_title="ComfyMax Scene Builder",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 Scene Builder")

st.caption(
    "Build a scene step by step, then copy the result to the main "
    "ComfyMax prompt generator."
)


# ============================================================
# Load question configuration
# ============================================================

def load_questions() -> dict:
    if not QUESTIONS_FILE.exists():
        st.error(
            "Scene Builder configuration was not found:\n\n"
            f"`{QUESTIONS_FILE}`"
        )
        st.stop()

    try:
        data = json.loads(
            QUESTIONS_FILE.read_text(
                encoding="utf-8"
            )
        )

    except (OSError, json.JSONDecodeError) as exc:
        st.error(
            "Could not read scene_questions.json:\n\n"
            f"{exc}"
        )
        st.stop()

    if not isinstance(data, dict):
        st.error(
            "scene_questions.json does not contain a valid configuration."
        )
        st.stop()

    return data


QUESTIONS = load_questions()


# ============================================================
# Session state
# ============================================================

_SESSION_DEFAULTS = {
    "sb_dialogue_turns": [
        {
            "character": 1,
            "dialogue": "",
            "action": "",
        }
    ],
    "sb_final_prompt": "",
}

for key, default in _SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ============================================================
# Helpers
# ============================================================

def question_text(name: str) -> str:
    return QUESTIONS[name]["question"]


def get_choice(
    name: str,
    *,
    key: str,
    horizontal: bool = False,
) -> str:
    config = QUESTIONS[name]

    options = list(
        config.get(
            "options",
            []
        )
    )

    allow_custom = bool(
        config.get(
            "allow_custom",
            False
        )
    )

    visible_options = list(options)

    if allow_custom:
        visible_options.append(
            "Write my own"
        )

    if horizontal:
        selected = st.radio(
            config["question"],
            visible_options,
            horizontal=True,
            key=key,
        )
    else:
        selected = st.selectbox(
            config["question"],
            visible_options,
            key=key,
        )

    if (
        allow_custom
        and selected == "Write my own"
    ):
        custom = st.text_input(
            "Custom answer",
            key=f"{key}_custom",
        )

        return custom.strip()

    return str(selected).strip()


def character_label(
    character_number: int
) -> str:
    return f"Character {character_number}"


def reset_scene_builder() -> None:
    keys_to_remove = [
        key
        for key in st.session_state.keys()
        if key.startswith("sb_")
    ]

    for key in keys_to_remove:
        del st.session_state[key]

    st.session_state[
        "sb_dialogue_turns"
    ] = [
        {
            "character": 1,
            "dialogue": "",
            "action": "",
        }
    ]

    st.session_state[
        "sb_final_prompt"
    ] = ""


def create_scene_prompt(
    *,
    scene_type: str,
    location: str,
    time_of_day: str,
    character_descriptions: list[str],
    main_action: str,
    dialogue_enabled: bool,
    dialogue_turns: list[dict],
    camera: str,
    lighting: str,
    ending: str,
) -> str:

    lines: list[str] = []

    lines.append(
        f"Scene type: {scene_type}"
    )

    lines.append(
        f"Location: {location}"
    )

    lines.append(
        f"Time of day: {time_of_day}"
    )

    lines.append("")

    lines.append("Characters:")

    for index, description in enumerate(
        character_descriptions,
        start=1,
    ):
        lines.append(
            f"Character {index}: {description}"
        )

    lines.append("")

    lines.append(
        f"Main action: {main_action}"
    )

    lines.append("")

    if dialogue_enabled:
        lines.append(
            "Dialogue sequence:"
        )

        valid_turns = [
            turn
            for turn in dialogue_turns
            if str(
                turn.get(
                    "dialogue",
                    ""
                )
            ).strip()
        ]

        if valid_turns:
            for index, turn in enumerate(
                valid_turns,
                start=1,
            ):
                character = turn.get(
                    "character",
                    1
                )

                dialogue = str(
                    turn.get(
                        "dialogue",
                        ""
                    )
                ).strip()

                action = str(
                    turn.get(
                        "action",
                        ""
                    )
                ).strip()

                lines.append(
                    f"{index}. Character {character} says exactly: "
                    f'"{dialogue}"'
                )

                if action:
                    lines.append(
                        f"   While speaking, Character {character}: "
                        f"{action}"
                    )

        else:
            lines.append(
                "No dialogue has been entered."
            )

    else:
        lines.append(
            "Dialogue: No dialogue."
        )

    lines.append("")

    lines.append(
        f"Camera: {camera}"
    )

    lines.append(
        f"Lighting and atmosphere: {lighting}"
    )

    lines.append(
        f"Ending: {ending}"
    )

    lines.append("")

    lines.append(
        "Important instructions:"
    )

    lines.append(
        "- Preserve the characters exactly as described."
    )

    lines.append(
        "- Preserve all dialogue exactly as written."
    )

    lines.append(
        "- Preserve the dialogue order."
    )

    lines.append(
        "- Clearly associate every action and line of dialogue "
        "with the correct character."
    )

    lines.append(
        "- Do not invent additional characters."
    )

    lines.append(
        "- Keep the requested camera, lighting and ending."
    )

    return "\n".join(lines).strip()


# ============================================================
# Controls
# ============================================================

top_left, top_right = st.columns(
    [4, 1]
)

with top_right:
    if st.button(
        "Start new scene",
        use_container_width=True,
    ):
        reset_scene_builder()
        st.rerun()


# ============================================================
# 1. Scene type
# ============================================================

st.subheader(
    "1. Scene type"
)

scene_type = get_choice(
    "scene_types",
    key="sb_scene_type",
)


# ============================================================
# 2. Location
# ============================================================

st.subheader(
    "2. Location"
)

location = get_choice(
    "location",
    key="sb_location",
)


# ============================================================
# 3. Time
# ============================================================

st.subheader(
    "3. Time of day"
)

time_of_day = get_choice(
    "time_of_day",
    key="sb_time_of_day",
)


# ============================================================
# 4. Characters
# ============================================================

st.subheader(
    "4. Characters"
)

character_count_value = get_choice(
    "character_count",
    key="sb_character_count",
    horizontal=True,
)

try:
    character_count = int(
        character_count_value
    )

except ValueError:
    character_count = 1


character_descriptions: list[str] = []

character_columns = st.columns(
    character_count
)

for index in range(
    character_count
):
    character_number = index + 1

    with character_columns[index]:
        description = st.text_area(
            f"Describe Character {character_number}",
            height=130,
            key=(
                f"sb_character_"
                f"{character_number}_description"
            ),
            placeholder=(
                "Appearance, age, clothing, role, "
                "important visual details..."
            ),
        )

        character_descriptions.append(
            description.strip()
        )


# ============================================================
# 5. Main action
# ============================================================

st.subheader(
    "5. Main action"
)

main_action = st.text_area(
    question_text(
        "main_action"
    ),
    height=120,
    key="sb_main_action",
    placeholder=(
        "Describe what is happening in the scene..."
    ),
)


# ============================================================
# 6. Dialogue
# ============================================================

st.subheader(
    "6. Dialogue"
)

dialogue_choice = get_choice(
    "dialogue",
    key="sb_dialogue_enabled",
    horizontal=True,
)

dialogue_enabled = (
    dialogue_choice.lower()
    == "yes"
)


if dialogue_enabled:

    st.caption(
        "Add as many dialogue turns as necessary. "
        "The exact order will be preserved."
    )

    turns = st.session_state[
        "sb_dialogue_turns"
    ]

    # Make sure characters that no longer exist
    # are reset to Character 1.
    for turn in turns:
        if int(
            turn.get(
                "character",
                1
            )
        ) > character_count:
            turn[
                "character"
            ] = 1

    updated_turns: list[dict] = []

    for index, turn in enumerate(
        turns
    ):
        turn_number = index + 1

        with st.container(
            border=True
        ):
            st.markdown(
                f"#### Dialogue turn {turn_number}"
            )

            available_characters = list(
                range(
                    1,
                    character_count + 1
                )
            )

            stored_character = int(
                turn.get(
                    "character",
                    1
                )
            )

            if (
                stored_character
                not in available_characters
            ):
                stored_character = 1

            selected_character = st.selectbox(
                "Who speaks?",
                options=available_characters,
                index=available_characters.index(
                    stored_character
                ),
                format_func=character_label,
                key=(
                    f"sb_turn_"
                    f"{turn_number}_character"
                ),
            )

            dialogue = st.text_area(
                (
                    f"What does Character "
                    f"{selected_character} say?"
                ),
                value=str(
                    turn.get(
                        "dialogue",
                        ""
                    )
                ),
                height=90,
                key=(
                    f"sb_turn_"
                    f"{turn_number}_dialogue"
                ),
                placeholder=(
                    "Enter the exact dialogue..."
                ),
            )

            action = st.text_area(
                (
                    f"What is Character "
                    f"{selected_character} "
                    f"doing while speaking?"
                ),
                value=str(
                    turn.get(
                        "action",
                        ""
                    )
                ),
                height=90,
                key=(
                    f"sb_turn_"
                    f"{turn_number}_action"
                ),
                placeholder=(
                    "Describe gestures, movement "
                    "or physical action..."
                ),
            )

            updated_turns.append(
                {
                    "character": selected_character,
                    "dialogue": dialogue,
                    "action": action,
                }
            )

    st.session_state[
        "sb_dialogue_turns"
    ] = updated_turns

    button_col1, button_col2 = st.columns(
        2
    )

    with button_col1:
        if st.button(
            "➕ Add dialogue turn",
            use_container_width=True,
        ):
            st.session_state[
                "sb_dialogue_turns"
            ].append(
                {
                    "character": 1,
                    "dialogue": "",
                    "action": "",
                }
            )

            st.rerun()

    with button_col2:
        if st.button(
            "➖ Remove last dialogue turn",
            disabled=(
                len(
                    st.session_state[
                        "sb_dialogue_turns"
                    ]
                )
                <= 1
            ),
            use_container_width=True,
        ):
            st.session_state[
                "sb_dialogue_turns"
            ].pop()

            st.rerun()


# ============================================================
# 7. Ending
# ============================================================

st.subheader(
    "7. How does the scene end?"
)

ending = st.text_area(
    question_text(
        "ending"
    ),
    height=110,
    key="sb_ending",
    placeholder=(
        "Describe the final action or image "
        "of the shot..."
    ),
)


# ============================================================
# 8. Camera
# ============================================================

st.subheader(
    "8. Camera"
)

camera = get_choice(
    "camera",
    key="sb_camera",
)


# ============================================================
# 9. Lighting
# ============================================================

st.subheader(
    "9. Lighting & atmosphere"
)

lighting = get_choice(
    "lighting",
    key="sb_lighting",
)


# ============================================================
# Generate structured prompt
# ============================================================

st.divider()

required_ready = bool(
    scene_type.strip()
    and location.strip()
    and time_of_day.strip()
    and main_action.strip()
    and camera.strip()
    and lighting.strip()
    and ending.strip()
    and all(
        description.strip()
        for description
        in character_descriptions
    )
)


if not required_ready:
    st.info(
        "Complete the scene information above "
        "to create the Scene Builder prompt."
    )


if st.button(
    "Create Scene Builder prompt",
    type="primary",
    use_container_width=True,
    disabled=not required_ready,
):

    dialogue_turns = (
        st.session_state[
            "sb_dialogue_turns"
        ]
        if dialogue_enabled
        else []
    )

    final_prompt = create_scene_prompt(
        scene_type=scene_type,
        location=location,
        time_of_day=time_of_day,
        character_descriptions=(
            character_descriptions
        ),
        main_action=main_action.strip(),
        dialogue_enabled=dialogue_enabled,
        dialogue_turns=dialogue_turns,
        camera=camera,
        lighting=lighting,
        ending=ending.strip(),
    )

    st.session_state[
        "sb_final_prompt"
    ] = final_prompt


# ============================================================
# Result
# ============================================================

final_prompt = st.session_state.get(
    "sb_final_prompt",
    "",
)


if final_prompt:

    st.divider()

    st.subheader(
        "Scene Builder prompt"
    )

    st.success(
        "Scene ready. Copy this prompt and paste it into "
        "the main ComfyMax prompt generator."
    )

    edited_prompt = st.text_area(
        "Review or edit before copying",
        value=final_prompt,
        height=420,
        key="sb_final_prompt_editor",
    )

    st.session_state[
        "sb_final_prompt"
    ] = edited_prompt

    st.markdown(
        "#### Copy prompt"
    )

    st.caption(
        "Use the copy icon in the top-right corner "
        "of the box below."
    )

    # Streamlit's code block has a built-in clipboard button.
    st.code(
        edited_prompt,
        language=None,
    )

    st.info(
        "Next: open the main ComfyMax page, paste this into "
        "'What do you want to make?', choose the LM Studio model, "
        "and generate the H3 prompt normally."
    )