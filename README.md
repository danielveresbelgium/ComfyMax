# ComfyMax v0.1

ComfyMax is a lightweight Streamlit frontend for creating MiniMax H3
video prompts with LM Studio and sending approved prompts to ComfyUI.
The aim is to keep the flexibility of ComfyUI while making the normal
MiniMax H3 workflow easier to use.

> **Status:** v0.1 is a working local version. The core workflow has
> been tested with one, two and three reference images.

## Current features

-   Select prepared ComfyUI API workflows through workflow-specific
    mappings.
-   MiniMax H3 Ref2VA support with 1, 2 or 3 reference images.
-   Send reference images to multimodal LM Studio models in
    `<Picture N>` order.
-   Generate structured H3 prompts with duration awareness and H3
    dialogue tags.
-   Review, edit and explicitly approve a prompt before rendering.
-   Paste an already finished H3 prompt and render without using LM
    Studio.
-   Control duration, resolution, aspect ratio, steps and seed from
    ComfyMax.
-   Seed `0` generates a random render seed; the actual seed is retained
    in metadata.
-   Settings page for ComfyUI/LM Studio connectivity and MiniMax H3
    model defaults.
-   Read available UNET, VAE and CLIP model choices directly from
    ComfyUI.
-   Display the finished video plus resolution, duration, format, size,
    seed and render time.
-   Live NVIDIA GPU monitor showing GPU load, VRAM, temperature and
    power.
-   Live GPU updates during LM Studio prompt generation and ComfyUI
    rendering.
-   Manual **Model in ComfyUI unload** button to free ComfyUI VRAM when
    finished.
-   ComfyUI models stay loaded after a render for faster repeated prompt
    adjustments/renders.
-   LM Studio model is unloaded after prompt generation to make VRAM
    available to ComfyUI.

## Requirements

ComfyMax currently targets a local Windows setup with:

-   Python
-   Streamlit
-   ComfyUI with its API available
-   LM Studio with its local API enabled
-   NVIDIA GPU and drivers
-   `nvidia-smi` for the GPU monitor
-   FFmpeg/`ffprobe` recommended for detailed video metadata

Development defaults:

``` text
LM Studio: http://127.0.0.1:1234
ComfyUI:   http://127.0.0.1:8188
```

## Important --- test `workflow_example` first

**Before trying ComfyMax, first open and run the supplied workflow from
`workflow_example` directly in ComfyUI.**

This is the recommended installation and compatibility test. A
successful direct ComfyUI render confirms that:

1.  ComfyUI can load the supplied workflow.
2.  All required standard and custom nodes are installed.
3.  The required MiniMax H3 models can be selected and loaded.
4.  The workflow itself renders correctly before ComfyMax is added to
    the chain.

If ComfyUI reports missing nodes, install those nodes first and restart
ComfyUI. If it reports missing models, resolve those model requirements
first.

**Do not troubleshoot ComfyMax until the supplied example workflow works
directly inside ComfyUI.**

## Project structure

``` text
ComfyMax/
├─ App.py
├─ pages/
│  └─ Settings.py
├─ modules/
│  ├─ comfyui.py
│  ├─ lmstudio.py
│  └─ prompt_enhancer.py
├─ config/
│  ├─ app.json
│  ├─ settings.json
│  └─ workflow_mappings/
├─ workflows/
├─ workflow_example/
├─ requirements.txt
├─ README.md
└─ .gitignore
```

## Installation

### 1. Download ComfyMax

Clone the repository:

``` powershell
git clone https://github.com/danielveresbelgium/ComfyMax.git
cd ComfyMax
```

You can also download the repository as a ZIP from GitHub and extract it
to a folder of your choice.

### 2. Create a Python virtual environment

A local virtual environment is recommended so ComfyMax dependencies stay
separate from other Python installations.

From the ComfyMax folder:

``` powershell
python -m venv .venv
```

Activate it:

``` powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation because of the execution policy, you can
either adjust the policy for your own environment or continue without
activating the environment and call `.venv\Scripts\python.exe`
directly.

### 3. Install Python dependencies

With the virtual environment active:

``` powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The supplied `requirements.txt` installs the Python packages required by
ComfyMax. ComfyUI, LM Studio, NVIDIA drivers and FFmpeg are separate
applications/tools and are not installed by this command.

### 4. Test ComfyUI independently

Start ComfyUI and load the supplied workflow from:

``` text
workflow_example/
```

Resolve all missing-node and missing-model errors and make at least one
successful test render.

This step is important: do not troubleshoot ComfyMax until the example
workflow renders successfully inside ComfyUI itself.

### 5. Start LM Studio

Start the LM Studio local server and make sure the model you want to use
for H3 prompt generation is available. For reference-image workflows,
use a model capable of receiving image input.

The default local LM Studio address expected by ComfyMax is:

``` text
http://127.0.0.1:1234
```

### 6. Start ComfyMax

The easiest method on Windows is:

``` powershell
.\Start_ComfyMax.bat
```

The startup script prefers the local `.venv` when it exists and otherwise
falls back to Python on `PATH`.

You can also start ComfyMax manually:

``` powershell
streamlit run App.py
```

On first launch, ComfyMax automatically creates `config/app.json` from
`config/app.example.json` if `app.json` does not yet exist.

### 7. Configure Settings

Open **Settings** to:

-   test the ComfyUI and LM Studio connections;
-   refresh the model lists reported by ComfyUI;
-   select the default MiniMax H3 video model / UNET;
-   select the Video VAE;
-   select the Audio VAE;
-   select the Text encoder / CLIP.

Settings are stored locally in `config/settings.json`. Both
`config/app.json` and `config/settings.json` are excluded from Git so
local machine settings are not committed accidentally.

When no model override is configured, the model already stored in a
workflow can remain the fallback.

### 8. First functional test

For the first ComfyMax test:

1. Choose one of the supplied reference-image workflows.
2. Upload the required reference image(s).
3. Select an LM Studio model.
4. Generate the H3 prompt.
5. Review and approve the prompt.
6. Send it to ComfyUI.
7. Confirm that the rendered video and metadata appear in ComfyMax.

If this complete cycle works, the local installation is ready for normal
use.

## Normal workflow

``` text
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

Prompt generation and rendering are deliberately separate. Creating an
H3 prompt does not immediately start a ComfyUI render.

## Using an existing H3 prompt

LM Studio is optional if you already have a finished prompt:

``` text
Paste H3 prompt into Final prompt
    ↓
Approve prompt
    ↓
Send to ComfyUI
```

## Reference images

The current Ref2VA mappings have been tested with 1, 2 and 3 reference
images. ComfyMax preserves their mapping order:

``` text
picture_1 → <Picture 1>
picture_2 → <Picture 2>
picture_3 → <Picture 3>
```

For Ref2VA, reference images are treated as reusable reference assets
rather than automatically as the first video frame.

## Prompt review and H3 dialogue

The **Final prompt** remains editable because generated prompts should
always be reviewed. Check for invented scene details, wrong subject
references, changed dialogue, unwanted camera instructions, and timing
outside the selected duration.

Dialogue is intended to remain literal and use H3 tags such as:

``` text
<Subject 1> (S1) <d>[English] What a beautiful day.</d>
```

User-supplied dialogue should not be translated, paraphrased or
repeated. Manual review is still recommended before every render.

## Render controls

Depending on the mapping, ComfyMax can expose:

-   Duration
-   Resolution / megapixels
-   Aspect ratio
-   Steps
-   Seed

Seed `0` means random. The actual generated seed is retained in the
render metadata so it can be reused manually.

## Model selection

ComfyMax does not need a fixed ComfyUI model-directory path. The
Settings page asks ComfyUI for the models it already knows about and can
populate choices for UNET, video VAE, audio VAE and CLIP/text encoder.
This also accommodates extra ComfyUI model paths as long as ComfyUI
itself sees those models.

## GPU monitor and VRAM management

The sidebar GPU monitor uses `nvidia-smi` and displays:

-   GPU utilization
-   VRAM used / total
-   temperature
-   power draw

It continues updating while LM Studio generates a prompt and while
ComfyUI renders.

ComfyMax intentionally **does not unload the ComfyUI model after each
render**. This makes repeated prompt edits and renders faster because H3
does not have to reload every time.

When finished, use **Model in ComfyUI unload** to request that ComfyUI
unload its loaded models and free its VRAM cache.

Other applications can also occupy VRAM. If memory remains high after
unloading ComfyUI, check LM Studio, Windows Task Manager or
`nvidia-smi`.

For the normal LM Studio route, ComfyMax loads the selected model,
generates the prompt and then unloads that LM Studio model so the VRAM
is available for ComfyUI.

## Render result

The last rendered video remains visible in the right-hand panel while
the left side can be edited. Available metadata includes:

-   width × height
-   actual duration
-   video format
-   file size
-   seed
-   render time
-   workflow
-   ComfyUI prompt ID
-   final prompt

`ffprobe` is used when available to inspect the actual rendered video.

## Workflow mappings

API workflow JSON files live in:

``` text
workflows/
```

Their matching mapping files use the same filename under:

``` text
config/workflow_mappings/
```

Mappings tell ComfyMax which node/input corresponds to prompt, images,
duration, resolution, steps, seed and model choices. This keeps the full
ComfyUI workflow separate from the simplified controls exposed by
ComfyMax.

## Troubleshooting

### ComfyMax cannot render

First confirm that the supplied `workflow_example` works directly in
ComfyUI.

### Missing nodes

Load `workflow_example` in ComfyUI, install the nodes ComfyUI reports as
missing, restart ComfyUI, and test again.

### Missing model in Settings

Refresh the model lists. If the model is still absent, first confirm
that ComfyUI itself can see it.

### High VRAM after rendering

This can be normal because ComfyMax deliberately keeps the ComfyUI model
loaded. Use **Model in ComfyUI unload** when finished. If VRAM remains
occupied, check LM Studio or another GPU process.

### GPU monitor does not work

Run:

``` powershell
nvidia-smi
```

If that does not work in Windows, ComfyMax cannot obtain NVIDIA GPU
statistics using this method.

### Prompt cannot be sent

Check that all required images are uploaded, the final prompt is not
empty, the prompt is approved, and the selected workflow has a matching
mapping.

## Current scope

ComfyMax v0.1 is intentionally focused on MiniMax H3, simple local
operation, explicit prompt review, reusable ComfyUI workflows and
one-to-three-reference-image Ref2VA workflows. It is not intended to
replace the complete ComfyUI interface.

## Before distributing a workflow

Test the complete path:

1.  Workflow directly in ComfyUI.
2.  Workflow mapping in ComfyMax.
3.  LM Studio prompt generation.
4.  Manual prompt entry.
5.  Prompt approval.
6.  One complete render.
7.  Repeated render with the ComfyUI model still loaded.
8.  Manual ComfyUI model unload.

## License

ComfyMax is released under the MIT License. See LICENSE for details.

## Acknowledgements

ComfyMax builds on the local AI ecosystem around ComfyUI, LM Studio and
MiniMax H3.
