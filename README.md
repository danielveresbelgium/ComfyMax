# ComfyMax v0.2

ComfyMax is a lightweight Streamlit frontend for creating MiniMax H3 video prompts with LM Studio, reviewing them before rendering, sending approved prompts to ComfyUI, and managing the resulting videos.

The aim is to keep the flexibility of ComfyUI while making the normal MiniMax H3 workflow easier to use for people who do not want to work directly with a large ComfyUI graph every time.

> **Status:** v0.2 is a working local version. The core workflow has been tested with one, two and three reference images. This release adds the Scene Builder, Video Gallery and persistent ComfyUI output-folder settings.

## What's new in v0.2

### Scene Builder

A new **Scene Builder** page helps build a scene step by step before sending it to the main H3 prompt generator.

It can collect:

- scene type;
- location;
- time of day;
- one to three main characters;
- character descriptions;
- main action;
- dialogue;
- multiple dialogue turns;
- the action a character performs while speaking;
- how the scene ends;
- camera style;
- lighting and atmosphere.

Dialogue order is preserved and additional dialogue turns can be added or removed as needed.

The final structured Scene Builder prompt can be reviewed, edited and copied into the main ComfyMax prompt generator.

Scene Builder questions are stored separately in:

```text
config/scene_questions.json
```

This makes the question set easy to change without rewriting the complete Scene Builder page.

### Video Gallery

A new **Video Gallery** page scans the configured ComfyUI output folder and all of its subfolders.

The gallery can:

- play generated videos directly inside ComfyMax;
- display videos in a compact multi-column gallery;
- use 2, 3, 4 or 5 columns, with 5 columns suitable for desktop use;
- search by filename or subfolder;
- filter by Today, This week or This month;
- sort by date or filename;
- show file date and file size;
- download a video;
- show a video in Windows Explorer;
- delete a video after confirmation;
- refresh the gallery without restarting ComfyMax.

Supported video extensions include `.mp4`, `.webm`, `.mov`, `.mkv`, `.avi` and `.m4v`.

### ComfyUI output folder in Settings

The ComfyUI output folder can now be stored in **Settings**.

Example:

```text
D:\ComfyUI\ComfyUI\output
```

The **Test output folder** button checks whether the folder exists and counts the videos found in that folder and its subfolders.

The Video Gallery reads this saved path automatically, so the folder does not have to be entered again on the gallery page.

The setting is stored locally in `config/settings.json`.

## Current features

- Select prepared ComfyUI API workflows through workflow-specific mappings.
- MiniMax H3 Ref2VA support with up to 9 reference images.
- Send reference images to multimodal LM Studio models in `<Picture N>` order.
- Generate structured H3 prompts with duration awareness and H3 dialogue tags.
- Review, edit and explicitly approve a prompt before rendering.
- Paste an already finished H3 prompt and render without using LM Studio.
- Build structured scenes with the Scene Builder before prompt generation.
- Create multi-turn dialogue sequences in the Scene Builder.
- Copy a completed Scene Builder prompt to the main prompt generator.
- Control duration, resolution, aspect ratio, steps and seed from ComfyMax.
- Seed `0` generates a random render seed; the actual seed is retained in metadata.
- Settings page for ComfyUI/LM Studio connectivity and MiniMax H3 model defaults.
- Save and test the ComfyUI video output folder.
- Read available UNET, VAE and CLIP model choices directly from ComfyUI.
- Display the finished video plus resolution, duration, format, size, seed and render time.
- Browse generated videos in the Video Gallery.
- Recursively scan ComfyUI output subfolders.
- Search, filter, sort, download and delete gallery videos.
- Open generated videos in Windows Explorer.
- Live NVIDIA GPU monitor showing GPU load, VRAM, temperature and power.
- Live GPU updates during LM Studio prompt generation and ComfyUI rendering.
- Manual **Unload model from ComfyUI** button to free ComfyUI VRAM when finished.
- ComfyUI models stay loaded after a render for faster repeated prompt adjustments/renders.
- LM Studio model is unloaded after prompt generation to make VRAM available to ComfyUI.

## Requirements

ComfyMax currently targets a local Windows setup with:

- Python
- Streamlit
- ComfyUI with its API available
- LM Studio with its local API enabled
- NVIDIA GPU and drivers
- `nvidia-smi` for the GPU monitor
- FFmpeg/`ffprobe` recommended for detailed video metadata

Development defaults:

```text
LM Studio: http://127.0.0.1:1234
ComfyUI:   http://127.0.0.1:8188
```

## Important — test `workflow_example` first

**Before trying ComfyMax, first open and run the supplied workflow from `workflow_example` directly in ComfyUI.**

A successful direct ComfyUI render confirms that:

1. ComfyUI can load the supplied workflow.
2. All required standard and custom nodes are installed.
3. The required MiniMax H3 models can be selected and loaded.
4. The workflow itself renders correctly before ComfyMax is added to the chain.

**Do not troubleshoot ComfyMax until the supplied example workflow works directly inside ComfyUI.**

## Project structure

```text
ComfyMax/
├─ App.py
├─ pages/
│  ├─ Scene_Builder.py
│  ├─ Video_Gallery.py
│  └─ Settings.py
├─ modules/
│  ├─ comfyui.py
│  ├─ lmstudio.py
│  └─ prompt_enhancer.py
├─ config/
│  ├─ app.json
│  ├─ scene_questions.json
│  ├─ settings.json
│  └─ workflow_mappings/
├─ workflows/
├─ workflow_example/
├─ Start_ComfyMax.bat
├─ requirements.txt
├─ README.md
└─ .gitignore
```

## Installation

### 1. Download ComfyMax

Clone the repository:

```powershell
git clone https://github.com/danielveresbelgium/ComfyMax.git
cd ComfyMax
```

You can also download the repository as a ZIP from GitHub and extract it to a folder of your choice.

### 2. Create a Python virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

ComfyUI, LM Studio, NVIDIA drivers and FFmpeg are separate applications/tools and are not installed by this command.

### 4. Test ComfyUI independently

Start ComfyUI and load the supplied workflow from:

```text
workflow_example/
```

Resolve all missing-node and missing-model errors and make at least one successful test render.

### 5. Start LM Studio

Start the LM Studio local server and make sure the model you want to use for H3 prompt generation is available.

Default address:

```text
http://127.0.0.1:1234
```

### 6. Start ComfyMax

```powershell
.\Start_ComfyMax.bat
```

or:

```powershell
streamlit run App.py
```

### 7. Configure Settings

Open **Settings** to:

- test the ComfyUI connection;
- test the LM Studio connection;
- refresh the model lists reported by ComfyUI;
- select the default MiniMax H3 video model / UNET;
- select the Video VAE;
- select the Audio VAE;
- select the Text encoder / CLIP;
- set the ComfyUI output folder;
- test the output folder and count the videos found recursively.

Settings are stored locally in `config/settings.json`.

### 8. First functional test

1. Choose one of the supplied reference-image workflows.
2. Upload the required reference image(s).
3. Select an LM Studio model.
4. Generate the H3 prompt.
5. Review and approve the prompt.
6. Send it to ComfyUI.
7. Confirm that the rendered video and metadata appear in ComfyMax.
8. Open Video Gallery and confirm that the rendered video is detected.

## Normal workflow

```text
Choose workflow
    ↓
Upload reference image(s)
    ↓
Enter the video idea
    ↓
Choose an LM Studio model
    ↓
Generate H3 prompt
    ↓
LM Studio model is unloaded
    ↓
Review/edit final prompt
    ↓
Approve prompt
    ↓
Send to ComfyUI
    ↓
Render and inspect result
```

Prompt generation and rendering are deliberately separate. Creating an H3 prompt does not immediately start a ComfyUI render.

## Scene Builder workflow

Scene Builder is optional. It is useful when you want help defining a scene before asking LM Studio to generate the final H3 prompt.

```text
Open Scene Builder
    ↓
Choose scene type, location and time
    ↓
Describe the characters
    ↓
Describe the main action
    ↓
Add dialogue turns if required
    ↓
Describe how the scene ends
    ↓
Choose camera and lighting
    ↓
Create Scene Builder prompt
    ↓
Review or edit
    ↓
Copy prompt
    ↓
Paste into the main ComfyMax prompt generator
```

The Scene Builder does not render a video itself. It creates structured input for the main ComfyMax H3 prompt generator.

## Video Gallery workflow

Before using the gallery, save the ComfyUI output folder in Settings.

The gallery scans recursively, so videos can remain in separate ComfyUI subfolders.

Deleting a video requires confirmation.

## Using an existing H3 prompt

LM Studio is optional if you already have a finished prompt:

```text
Paste H3 prompt into Final prompt
    ↓
Approve prompt
    ↓
Send to ComfyUI
```

## Reference images

The current Ref2VA mappings have been tested with 1, 2 and 3 reference images. ComfyMax preserves their mapping order:

```text
picture_1 → <Picture 1>
picture_2 → <Picture 2>
picture_3 → <Picture 3>
```

## Prompt review and H3 dialogue

The **Final prompt** remains editable because generated prompts should always be reviewed.

Dialogue is intended to remain literal and use H3 tags such as:

```text
<Subject 1> (S1) <d>[English] What a beautiful day.</d>
```

User-supplied dialogue should not be translated, paraphrased or repeated.

## Render controls

Depending on the mapping, ComfyMax can expose:

- Duration
- Resolution / megapixels
- Aspect ratio
- Steps
- Seed

Seed `0` means random.

## Model selection

The Settings page asks ComfyUI for the models it already knows about and can populate choices for UNET, video VAE, audio VAE and CLIP/text encoder.

The ComfyUI **output folder** is stored separately in Settings for use by the Video Gallery.

## GPU monitor and VRAM management

The sidebar GPU monitor uses `nvidia-smi` and displays GPU utilization, VRAM used/total, temperature and power draw.

ComfyMax intentionally does **not** unload the ComfyUI model after each render, which makes repeated renders faster.

When finished, use **Unload model from ComfyUI**.

## Render result

The last rendered video remains visible in the right-hand panel. Available metadata includes:

- width × height
- actual duration
- video format
- file size
- seed
- render time
- workflow
- ComfyUI prompt ID
- final prompt

`ffprobe` is used when available.

## Workflow mappings

API workflow JSON files live in `workflows/`.

Matching mapping files live in `config/workflow_mappings/`.

## Access from another device

Because ComfyMax uses Streamlit, it can also be opened from another device on the same local network when Streamlit is listening on the network interface and the Windows firewall allows the connection.

This is particularly useful for reviewing generated videos from a tablet.

## Troubleshooting

### ComfyMax cannot render

First confirm that the supplied `workflow_example` works directly in ComfyUI.

### Missing nodes

Install the nodes ComfyUI reports as missing, restart ComfyUI, and test again.

### Missing model in Settings

Refresh the model lists and confirm that ComfyUI itself can see the model.

### Video Gallery says no output folder is configured

Open **Settings**, enter the ComfyUI output folder, use **Test output folder**, and save the settings.

### Video Gallery does not show a video

Check the saved path, supported extension, current filters and use **Refresh gallery**.

### Video cannot be deleted

Make sure the file is not locked by another application and that Windows permits deletion.

### High VRAM after rendering

Use **Unload model from ComfyUI** when finished.

### GPU monitor does not work

Run:

```powershell
nvidia-smi
```

### Prompt cannot be sent

Check that all required images are uploaded, the final prompt is not empty, the prompt is approved, and the selected workflow has a matching mapping.

## Current scope

ComfyMax v0.2 is focused on MiniMax H3, simple local operation, explicit prompt review, reusable ComfyUI workflows, structured scene preparation and local video management.

It is not intended to replace the complete ComfyUI interface.

## Planned improvements

Future additions may include:

- saved prompt library and prompt management;
- better mobile/tablet layout;
- QR code for direct LAN access;
- ComfyUI and LM Studio status indicators;
- richer video-gallery management;
- regenerate from saved render information;
- use an existing video as a new reference;
- favorites and tags;
- improved render metadata/history.

## Before distributing a workflow

Test the complete path:

1. Workflow directly in ComfyUI.
2. Workflow mapping in ComfyMax.
3. LM Studio prompt generation.
4. Manual prompt entry.
5. Prompt approval.
6. One complete render.
7. Repeated render with the ComfyUI model still loaded.
8. Manual ComfyUI model unload.
9. Scene Builder prompt creation and copy.
10. Video Gallery detection of the rendered video.

## License

Add the chosen project license before public distribution.

## Acknowledgements

ComfyMax builds on the local AI ecosystem around ComfyUI, LM Studio and MiniMax H3.
