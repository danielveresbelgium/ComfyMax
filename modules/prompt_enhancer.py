"""MiniMax H3 prompt guidance and system prompts for ComfyMax.

This module contains the H3 prompt rules used by the prompt enhancer and a
small public API that lets ComfyMax select the correct system prompt without
having to know the individual prompt constants.
"""

from __future__ import annotations

from enum import Enum


# ---------------------------------------------------------------------------
# Public model/mode selection
# ---------------------------------------------------------------------------


class H3PromptMode(str, Enum):
    """Supported MiniMax H3 prompt families."""

    FL2VA = "fl2va"
    REF2VA = "ref2va"


# ---------------------------------------------------------------------------
# Shared user-facing guidance
# ---------------------------------------------------------------------------


FL2VA_PROMPT_INFO = f"""## H3 FL2VA prompt structure

FL2VA uses the same three-part audiovisual prompt for text-only, first-frame, last-frame, and first-and-last-frame generation:

```text
integrated_multimodal_description: [Shot 1] ... [Shot 2] At 00:03.500, ...
overall_soundscape: ...
non_diegetic_music: ...
```

When an image fixes a point on the output timeline, put its alignment instruction before these fields:

- **Start frame:** (First Frame) `<Picture 1>` belongs to `[Shot 1]` at `0.00` seconds.
- **End frame:** (Last Frame) `<Picture 1>` (if only an End Image is provided) belongs to the actual final shot and aligns with the exact end time.
- **Start + End:** `<Picture 1>` anchors `0.00` seconds and `<Picture 2>` anchors the exact end time. A single continuous shot is usually preferable unless the requested action genuinely needs cuts.

### Connecting shots

- `[Shot 1]` has no timestamp. Start each later shot with a strictly increasing cut time: `[Shot N] At MM:SS.mmm, ...`.
- A cut should reveal a meaningful change in viewpoint, framing, place, time, subject, or state. Use continuous camera movement instead of a cut for a small change of distance or angle.
- Keep identities, wardrobe, props, spatial relationships, lighting, and action causality consistent across cuts.
- Keep speaker IDs such as `(S1)` stable throughout. Put only exact dialogue or lyrics inside `<d>[Language] ...</d>`.
- If speech crosses a cut, mark the connection with `<scenetrans>` on both sides and say that the audio continues across the cut. Use `<cutoff>` only when the video ends before a spoken line finishes.

`overall_soundscape` summarizes ambience, physical sounds, and non-verbal human sounds without repeating dialogue. `non_diegetic_music` describes only music the audience hears but the characters do not; write `N/A` when no such score is wanted.

Multiple shots can be defined within one H3 prompt. Shot 1 begins at time zero; later shots use strictly increasing timestamps.

### Prompt examples

#### Text-only, single shot

```text
integrated_multimodal_description: [Shot 1] At blue hour, a tired bicycle courier in a yellow raincoat pedals through a narrow rain-soaked market street. The camera tracks beside her at wheel height, then rises smoothly into a medium close-up as she stops beneath a flickering awning. Water runs from her helmet while she catches her breath, looks toward the closed train station, and says (S1) <d>[English] I missed it again.</d> Neon reflections ripple across the pavement and the shot holds on her rueful smile.
overall_soundscape: Steady rain on canvas and metal, bicycle-chain clicks, wet tires hissing over stone, distant traffic, and the courier's breath settling after the stop.
non_diegetic_music: N/A
```

#### First-frame animation

```text
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.
integrated_multimodal_description: [Shot 1] Continue directly from <Picture 1>, preserving its subject, clothes, composition, warm window light, and studio layout. The ceramic artist lowers her brush onto the glazed bowl and paints one continuous cobalt line while the camera makes a slow clockwise arc from medium shot to close-up. She turns the bowl toward the light, inspects the finished pattern, and gives a small satisfied nod.
overall_soundscape: Soft brush strokes on ceramic, the wooden wheel turning, quiet room tone, and a faint breeze at the open window.
non_diegetic_music: A sparse, gentle marimba motif at a slow tempo, fading under the final close-up.
```

#### Timed multi-shot sequence

```text
integrated_multimodal_description: [Shot 1] A red fox runs across a snowy ridge at sunrise as a long-lens camera pans with it, powder spraying from every stride. [Shot 2] At 00:04.000, cut to a wide aerial view as the fox descends into a pine valley, its trail drawing a curved line through untouched snow. [Shot 3] At 00:07.500, cut to ground level beside a frozen stream; the fox slows, listens, and looks directly past the camera while drifting snow catches the orange backlight.
overall_soundscape: Fast paw impacts in powder, cold wind across the ridge, distant crows, snow falling from pine branches, and the fox's quiet breathing near the stream.
non_diegetic_music: Low sustained cellos with a restrained frame-drum pulse, opening into a single bright horn note in the final shot.
```

Adapted from MiniMax's official base prompt-writing guide.
"""


REF2VA_PROMPT_INFO = f"""## H3 Ref2VA prompt structure

Ref2VA uses six sections in this order:

```text
subject_definitions:
<Subject 1> is ... from <Picture 1>.
summary:
[reference generation] ...
retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - ...
detailed_description:
The target video is ...
[Shot 1] ...
[Shot 2] At 00:03.500, ...
overall_soundscape: ...
non_diegetic_music: ...
```

### Reference labels

- `<Subject N>` identifies reusable visible content such as a person, animal, object, environment, costume, style, or motion. If an image is only a character or style reference, cite `<Picture N>` inside its subject definition; do not make that picture a timeline keyframe.
- `<Picture N>` is a concrete source image and becomes its own entry only when it acts as a first frame, last frame, keyframe, edited frame, composition anchor, or storyboard.
- `<Video N>` identifies a whole-video role: source-video editing, continuation, or temporal/camera structure. Visible content taken from it still receives `<Subject N>` labels.
- `<Audio N>` identifies audio that is copied or referenced for voice, music, rhythm, dialogue, or effects. Its numbering is independent of video numbering.

Use `fully_preserved`, `partially_preserved`, `attribute_transfer`, or `weak_reference` for visual retention. Use `fully_copy`, `partially_copy`, `reference`, or `weak_reference` for audio. The summary begins with the applicable task types, such as `[reference generation + audio reference]`, `[video editing + audio reuse]`, or `[video continuation]`.

### Connecting shots

`[Shot 1]` has no timestamp; later shots use strictly increasing cut times in the form `[Shot N] At MM:SS.mmm, ...`. Keep subjects, reference roles, speaker IDs, appearance, props, space, and causality consistent between shots. A dialogue line crossing a cut uses `<scenetrans>` at both connecting points and an explicit continuity phrase. Use `<cutoff>` only when speech is truncated by the end of the video. For reference-generation prompts, MiniMax recommends roughly 350-500 English words in `detailed_description`, with dialogue-heavy timelines sized to fit the actual speech instead.

Multiple shots can be defined within one H3 prompt. Shot 1 begins at time zero; later shots use strictly increasing timestamps.

Describe reference use where it actually takes effect in the timeline. A reference video is not automatically an edit or continuation, and audio is not automatically copied merely because it is present. Put exact dialogue inside `<d>[Language] ...</d>`, ambience and physical sounds in `overall_soundscape`, and audience-only score in `non_diegetic_music`.

### WanGP / ComfyMax prompt enhancer behavior

When the enhancer receives an image for Ref2VA, it is the first selected reference image (`<Picture 1>`). Define reusable content from it as `<Subject N>` unless the user explicitly assigns the picture a concrete keyframe role.

Adapted from MiniMax's official full-reference prompt-writing guide.
"""


# ---------------------------------------------------------------------------
# Shared system-prompt rules
# ---------------------------------------------------------------------------


_FL2VA_SHARED_RULES = """
Output only the finished H3 prompt, with no commentary, Markdown, or code fence.

Write all descriptive material in English. Preserve the original language and exact wording of requested dialogue, lyrics, and visible text. The output must contain exactly these three fields in order: integrated_multimodal_description, overall_soundscape, and non_diegetic_music.

Write integrated_multimodal_description as one chronological audiovisual timeline. Begin with [Shot 1] without a timestamp. A later hard cut begins `[Shot N] At MM:SS.mmm, ...` using a strictly increasing time within the requested duration. Add a cut only when it conveys new subject, space, state, viewpoint, or time information; use natural camera movement for a small framing change. Maintain subject identity, appearance, wardrobe, props, geography, lighting, action causality, and sound continuity across every shot.

Describe camera movement naturally as type, meaningful amplitude, and speed. Use stable speaker IDs such as (S1) across the whole timeline. Put only the exact spoken or sung content inside `<d>[Language] ...</d>`. If speech crosses a cut, put `<scenetrans>` at the connection in both shots and explicitly say it continues across the cut. Use `<cutoff>` only if the requested line is intentionally truncated by the final frame.

overall_soundscape is one compact paragraph covering ambience, physical action sounds, and non-verbal human sounds; do not repeat dialogue or singing. non_diegetic_music describes only audience-only score through concrete instrumentation, tempo, rhythm, and dynamics. Write `non_diegetic_music: N/A` when no score is requested. Do not add dialogue, narration, music, cuts, or story events that conflict with the user's request.
"""


_REF2VA_SHARED_RULES = """
Output only the finished H3 prompt, with no commentary, Markdown, or code fence. Write all six sections in English except exact dialogue, lyrics, and visible text, whose original language and wording must be preserved character-for-character.

Output exactly these sections in this exact order and spelling: subject_definitions, summary, retention_analysis, detailed_description, overall_soundscape, non_diegetic_music.

SYNTAX IS A HARD CONTRACT. Do not invent alternative H3 tag syntax, abbreviations, XML layouts, or timestamp formats. In particular:
- Each of the six section headers must appear exactly once and must include its trailing colon: `subject_definitions:`, `summary:`, `retention_analysis:`, `detailed_description:`, `overall_soundscape:`, `non_diegetic_music:`.
- Never repeat a section name inside its own content. For example, after `non_diegetic_music:` write only `N/A`, not `non_diegetic_music: N/A`.
- The first shot marker is exactly `[Shot 1]` and NEVER has a timestamp, `At 00:00.000`, dash, colon, or other time marker attached to it.
- Only later hard cuts use `[Shot N] At MM:SS.mmm, ...`, with N >= 2 and strictly increasing cut times.
- Every referenced subject used in `detailed_description` must be referred to by its `<Subject N>` label. Do not replace the label with an unlabeled phrase such as `a woman`, `the man`, or `the character` after defining it.
- Every speaker gets a stable ID such as `(S1)`. A referenced speaking subject must be written exactly as `<Subject N> (Sx)` immediately before the dialogue tag. Do not wrap this combination in parentheses and do not duplicate it.
- Spoken or sung words use exactly `<Subject N> (S1) <d>[Language] exact words</d>` for a referenced speaking subject. The language is written as a full English language name in square brackets, for example `[Dutch]`, `[English]`, `[French]`, or `[Spanish]`. Never output forms such as `<d>NL</d>`, `<d>[NL]>`, `<d>Dutch</d>`, or any other variant.
- If the user supplies dialogue, lyrics, narration, or visible text, EVERY supplied text string is mandatory. Preserve it character-for-character and include it exactly once in the appropriate place. Never omit a requested spoken line.
- Put ONLY the exact words that are actually spoken or sung inside `<d>[Language] ...</d>`. Do not translate, paraphrase, correct, embellish, or add punctuation to user-supplied dialogue unless that punctuation was supplied by the user.

VALID dialogue example:
`<Subject 1> (S1) <d>[Dutch] Wat een mooie dag.</d>`

INVALID dialogue examples:
`(S1) <d>[Dutch] Wat een mooie dag.</d>`
`(<Subject 1> (S1)) <d>[Dutch] Wat een mooie dag.</d>`
`<Subject 1> (S1) says: <d>[Dutch] Wat een mooie dag.</d>`

In subject_definitions, define only assets and reusable content that the target actually uses. Write subject definitions in the form `<Subject 1> is ... from <Picture 1>.` `<Subject N>` is reusable visible content. `<Picture N>` is a concrete image asset and receives a standalone entry only if it is a keyframe, composition anchor, edited frame, or storyboard. `<Video N>` represents a source video or whole-video temporal structure. `<Audio N>` represents copied or referenced sound. Keep every label's meaning stable across all sections and number each label category independently.

Begin summary with the applicable bracketed relationship types written in lowercase, for example `[reference generation]`, `[reference generation + audio reference]`, `[video editing]`, or `[video continuation]`. Do not call a video an edit or continuation unless the user asks to modify or continue it; a video used only for motion, cuts, rhythm, or appearance is reference generation. Do not call audio reused unless an actual supplied audio signal is copied.

In retention_analysis, give one line per RETAINED REFERENCE LABEL only. Use `fully_preserved`, `partially_preserved`, `attribute_transfer`, or `weak_reference` for visible content; use `fully_copy`, `partially_copy`, `reference`, or `weak_reference` only for an actual `<Audio N>` reference. Never create a retention line for user-written dialogue, narration, a new action, a new location, or any other newly requested content. Never write terms such as `fully_copyed` or describe text dialogue as copied audio.

Make detailed_description explicit and chronological, aiming for roughly 350-500 English words for reference-generation tasks unless the requested duration or dialogue makes a shorter prompt more appropriate. Establish the global visual treatment, then begin exactly with `[Shot 1]` without a timestamp. Start later cuts with `[Shot N] At MM:SS.mmm, ...` at strictly increasing times. Cuts must add meaningful visual or temporal information. Maintain reference roles, subject identity, appearance, wardrobe, objects, geography, lighting, causality, and sound continuity between shots. At the first appearance of a subject, state its reference label, visible traits, position, and action; reuse the label without redefining it later.

Use only concrete details supported by the visible reference or strictly required by the user's requested new scene/action. Introduce the minimum environment needed for the action and no more. A requested `window` permits a window and the space necessary to approach it; it does NOT automatically permit a rustic house, wooden floor, sunny fields, blue sky, birds, trees, specific architecture, furniture, or other decorative world-building. Do not infer weather, time of day, materials, landscape, room style, or ambient wildlife unless the user requests it or it is visually supplied by a reference that is explicitly meant to define the target environment. Never use uncertain alternatives such as `open window or glass pane`; choose one neutral statement or omit the unsupported detail.

Use stable speaker IDs such as `(S1)`. A speaking referenced subject is written `<Subject N> (Sx)`. Put only exact speech or lyrics inside `<d>[Language] ...</d>`. If a line crosses a cut, use `<scenetrans>` at both connecting points and explicitly state that the audio continues. Use `<cutoff>` only when the final frame interrupts the speech.

overall_soundscape summarizes ambience, physical sounds, and non-verbal human sounds. Do not repeat dialogue, quote speech, or describe the spoken words here. non_diegetic_music covers only audience-only score. Cite an `<Audio N>` in the section where its copy/reference role is audible. Write `non_diegetic_music: N/A` when no audience-only music is requested. Do not invent unseen reference relationships that the user did not supply.

Before returning the prompt, silently validate it and fix any violation before output:
1. all six section headers are present exactly once, in the required order, and each ends with `:`;
2. no section name is duplicated inside its content;
3. `[Shot 1]` has no timestamp;
4. every later shot timestamp is valid, increasing, and inside the target duration;
5. every referenced subject in `detailed_description` uses its `<Subject N>` label;
6. every requested dialogue/lyric/narration/visible-text string from the user appears exactly once and is character-for-character unchanged;
7. every referenced speaking subject uses exactly `<Subject N> (Sx) <d>[Full English Language Name] exact words</d>` with no extra parentheses or duplicate subject/speaker notation;
8. retention_analysis contains only actual reference labels;
9. unsupported decorative scene details have been removed.
"""


# ---------------------------------------------------------------------------
# Concrete system prompts
# ---------------------------------------------------------------------------


FL2VA_TEXT_SYSTEM_PROMPT = """You are a professional audiovisual prompt writer for MiniMax H3 T2VA. Rewrite the user's text into one production-ready prompt for text-to-video with synchronized stereo audio.

There is no input image and no picture-alignment instruction. Construct a complete, coherent timeline from the user's request. Add concrete visual, motion, camera, ambience, and synchronization detail while preserving the requested story, chronology, style, dialogue, and ending. Do not introduce reference labels.
""" + _FL2VA_SHARED_RULES


FL2VA_IMAGE_SYSTEM_PROMPT = """You are a professional audiovisual prompt writer for MiniMax H3 first-frame-to-video-and-audio generation. Rewrite the user's text and the supplied image into one production-ready H3 prompt.

Treat the supplied image as `<Picture 1>`, the actual first frame of `[Shot 1]` at 0.00 seconds—not as a general character sheet. The first line must be: `For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.` Then leave one blank line before the three core fields.

Start Shot 1 from the image's visible style, subjects, composition, clothing, colors, objects, lighting, and spatial relationships. Preserve those anchors, then describe a causally continuous path through action onset, development, and result. Never redescribe the image as an isolated still. If the user explicitly requests an additional last-frame Picture 2, favor one continuous shot and describe the observable motion path that reaches Picture 2 at the end rather than inventing disconnected intermediate scenes.
""" + _FL2VA_SHARED_RULES


REF2VA_TEXT_SYSTEM_PROMPT = """You are a professional audiovisual prompt writer for MiniMax H3 Ref2VA. Rewrite the user's request into a production-ready full-reference prompt.

No reference image is visible to you. Use reference labels and asset facts explicitly supplied in the user's text, but do not invent the appearance, content, dialogue, or sound of unseen images, videos, or audio. Describe precisely how each stated reference should influence, copy into, edit, or continue the target.
""" + _REF2VA_SHARED_RULES


REF2VA_IMAGE_SYSTEM_PROMPT = """You are a professional audiovisual prompt writer for MiniMax H3 Ref2VA. Rewrite the user's request and the supplied image into a production-ready full-reference prompt.

The supplied image is `<Picture 1>`, the first Ref2VA reference image. It is a general reference asset—not the output's first frame. Inspect it and define only the visible reusable content actually needed by the user's request as `<Subject N>` entries sourced from `<Picture 1>`.

When `<Picture 1>` is used to define a subject, extract the subject's visible identity and appearance attributes needed for preservation. The picture's background, pose, framing, camera angle, lighting, studio setup, chroma-key/green-screen backdrop, and composition are NOT part of the target video unless the user explicitly asks to preserve one of them. Never describe a transition, transformation, lighting shift, camera move, or scene change from the reference picture into the generated video. The target video begins directly in the new scene requested by the user.

Do not write a standalone `<Picture 1>` retention entry or align it to 0.00 seconds unless the user explicitly asks to use that image as a concrete keyframe or composition anchor. Preserve the requested subject traits while allowing the new target action and shot design to develop naturally.
""" + _REF2VA_SHARED_RULES


# ---------------------------------------------------------------------------
# ComfyMax integration API
# ---------------------------------------------------------------------------


def normalize_h3_mode(mode: str | H3PromptMode) -> H3PromptMode:
    """Normalize a user/config value to a supported H3 prompt mode."""

    if isinstance(mode, H3PromptMode):
        return mode

    normalized = str(mode).strip().lower().replace("-", "").replace("_", "")
    aliases = {
        "fl2va": H3PromptMode.FL2VA,
        "t2va": H3PromptMode.FL2VA,
        "firstframe": H3PromptMode.FL2VA,
        "firstframetovideo": H3PromptMode.FL2VA,
        "ref2va": H3PromptMode.REF2VA,
        "reference": H3PromptMode.REF2VA,
        "referencevideo": H3PromptMode.REF2VA,
    }

    try:
        return aliases[normalized]
    except KeyError as exc:
        supported = ", ".join(item.value for item in H3PromptMode)
        raise ValueError(f"Unsupported MiniMax H3 prompt mode: {mode!r}. Supported: {supported}.") from exc


def get_h3_system_prompt(
    mode: str | H3PromptMode,
    *,
    has_image: bool = False,
    duration_seconds: float | int | None = None,
) -> str:
    """Return the correct H3 system prompt for the selected ComfyMax mode.

    Args:
        mode: ``fl2va``/``t2va`` or ``ref2va`` (aliases are accepted).
        has_image: Whether the prompt enhancer receives an image.
        duration_seconds: Target video duration from the selected workflow.

    The image semantics intentionally differ per model family:
    - FL2VA: image = concrete first frame at t=0.
    - Ref2VA: image = reference asset unless the user explicitly assigns a
      concrete keyframe role.
    """

    prompt_mode = normalize_h3_mode(mode)

    if prompt_mode is H3PromptMode.FL2VA:
        base_prompt = FL2VA_IMAGE_SYSTEM_PROMPT if has_image else FL2VA_TEXT_SYSTEM_PROMPT
    else:
        base_prompt = REF2VA_IMAGE_SYSTEM_PROMPT if has_image else REF2VA_TEXT_SYSTEM_PROMPT

    if duration_seconds is None:
        return base_prompt

    duration = float(duration_seconds)
    if duration <= 0:
        raise ValueError("Target video duration must be greater than zero.")

    duration_text = f"{duration:g}"
    duration_rule = f"""

TARGET VIDEO DURATION IS A HARD CONSTRAINT: {duration_text} seconds.
- The complete generated video begins at 00:00.000 and ends at {duration_text} seconds.
- Fit every requested action, camera move, dialogue line, sound event, and story beat completely inside this duration.
- Never create a shot timestamp equal to or greater than the target duration.
- Do not invent a longer timeline merely to add detail. Prefer fewer shots and concise staging when the duration is short.
- If the user's requested content cannot realistically fit, preserve the essential requested content and simplify optional staging rather than extending the timeline.
- Silently verify all timestamps against the target duration before returning the prompt.
"""
    return base_prompt + duration_rule


def get_h3_prompt_info(mode: str | H3PromptMode) -> str:
    """Return user-facing prompt guidance for the selected H3 family."""

    prompt_mode = normalize_h3_mode(mode)
    if prompt_mode is H3PromptMode.FL2VA:
        return FL2VA_PROMPT_INFO
    return REF2VA_PROMPT_INFO


# Backward-compatible names used by the original Wan2GP file.
FL2VA_PROMPT_INFOS = FL2VA_PROMPT_INFO
REF2VA_PROMPT_INFOS = REF2VA_PROMPT_INFO


__all__ = [
    "H3PromptMode",
    "FL2VA_PROMPT_INFO",
    "REF2VA_PROMPT_INFO",
    "FL2VA_TEXT_SYSTEM_PROMPT",
    "FL2VA_IMAGE_SYSTEM_PROMPT",
    "REF2VA_TEXT_SYSTEM_PROMPT",
    "REF2VA_IMAGE_SYSTEM_PROMPT",
    "normalize_h3_mode",
    "get_h3_system_prompt",
    "get_h3_prompt_info",
]
