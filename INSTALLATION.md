# ComfyMax Installation

This guide explains the basic installation of ComfyMax on Windows.

## Requirements

Before installing ComfyMax, make sure you already have:

* Windows 10 or Windows 11
* NVIDIA GPU
* ComfyUI installed and working
* LM Studio installed
* Git for Windows
* Python support is handled through the included ComfyMax virtual environment after installation

ComfyMax does not replace ComfyUI or LM Studio. Both services must be available locally.

## 1. Download ComfyMax

Open PowerShell and choose the folder where you want to install ComfyMax.

Clone the repository:

```powershell
git clone https://github.com/danielveresbelgium/ComfyMax.git
```

Then open the ComfyMax folder:

```powershell
cd ComfyMax
```

## 2. Install the Python environment

If your ComfyMax package includes an installation or setup script, run that first.

After installation, the ComfyMax folder should contain a virtual environment named:

```text
.venv
```

## 3. Test ComfyUI first

Before using ComfyMax, open ComfyUI and test the example workflow supplied in:

```text
workflow_example
```

This is important because it confirms that:

* the required custom nodes are installed;
* the required models are available;
* the workflow itself works correctly in ComfyUI.

If the example workflow does not work directly in ComfyUI, fix that before trying it through ComfyMax.

## 4. Start LM Studio

Start LM Studio and load or enable the local server.

The default ComfyMax configuration expects LM Studio at:

```text
http://127.0.0.1:1234/v1
```

You can change this later in ComfyMax if necessary.

## 5. Start ComfyUI

Start ComfyUI normally.

The default ComfyMax configuration expects ComfyUI at:

```text
http://127.0.0.1:8188
```

If your ComfyUI installation uses another port, change the address in ComfyMax.

## 6. Start ComfyMax

Run:

```text
Start_ComfyMax.bat
```

ComfyMax should open in your browser.

The normal local address is:

```text
http://localhost:8501
```

On first use, Streamlit may ask for an email address.

This is optional. Leave the field blank and press **Enter** to continue.

## 7. Configure models

Open the **Settings** page in ComfyMax and select the models used by your MiniMax H3 workflow.

If no model is selected in Settings, ComfyMax can continue using the model already stored inside the workflow where supported.

## 8. Add your own ComfyUI workflow

ComfyMax includes a **Workflow Mapper**.

Export your workflow from ComfyUI using:

```text
Export (API Format)
```

Then open the **Workflow Mapper** page in ComfyMax.

The Mapper can:

* analyze the workflow;
* detect important controls;
* suggest mappings;
* detect reference-image inputs;
* validate the mapping;
* install both the workflow and mapping directly into ComfyMax.

You don't need to manually create the mapping JSON for most workflows.

## Updating ComfyMax

To update an existing Git installation, run:

```text
Update_ComfyMax.bat
```

The updater:

* checks GitHub for updates;
* protects locally modified tracked files;
* leaves untracked user files alone;
* downloads the latest ComfyMax version;
* updates Python dependencies from `requirements.txt`.

If you modified an existing ComfyMax source file manually, the updater will stop instead of overwriting it.

## Important folders

```text
workflows
```

Contains ComfyUI API workflows used by ComfyMax.

```text
config/workflow_mappings
```

Contains the matching ComfyMax mapping files.

The workflow and mapping must use the same filename.

```text
workflow_example
```

Contains example workflows that should be tested directly in ComfyUI before using ComfyMax.

## Need more information?

See the main:

```text
README.md
```

for the full feature overview, configuration details, Workflow Mapper information, Scene Builder, Video Gallery, and other ComfyMax features.
