from __future__ import annotations

import copy
import json
from typing import Any
from uuid import uuid4

import requests


class ComfyUIError(RuntimeError):
    """Readable error raised for workflow or ComfyUI failures."""


def load_api_workflow(raw: bytes | str) -> dict[str, Any]:
    try:
        workflow = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
        raise ComfyUIError("The selected file is not a valid JSON workflow.") from exc
    if not isinstance(workflow, dict) or not workflow:
        raise ComfyUIError("The workflow must be a non-empty JSON object.")
    if "nodes" in workflow:
        raise ComfyUIError(
            "This appears to be a ComfyUI editor workflow. Export it from ComfyUI using 'Save (API Format)'."
        )
    invalid = [node_id for node_id, node in workflow.items() if not isinstance(node, dict) or "class_type" not in node]
    if invalid:
        raise ComfyUIError(f"Invalid API format; class_type is missing for node(s): {', '.join(invalid[:5])}.")
    return workflow


def apply_mapping(
    workflow: dict[str, Any], mapping: dict[str, Any], values: dict[str, Any]
) -> dict[str, Any]:
    result = copy.deepcopy(workflow)
    for field_name, rule in mapping.get("fields", {}).items():
        if field_name not in values:
            continue
        node_id = str(rule["node_id"])
        input_name = rule["input"]
        try:
            result[node_id]["inputs"][input_name] = values[field_name]
        except KeyError as exc:
            raise ComfyUIError(
                f"Mapping '{field_name}' refers to missing node {node_id} or input '{input_name}'."
            ) from exc
    return result


class ComfyUIClient:
    def __init__(self, base_url: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client_id = str(uuid4())

    def upload_image(self, name: str, content: bytes, content_type: str | None) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/upload/image",
                files={"image": (name, content, content_type or "application/octet-stream")},
                data={"type": "input", "overwrite": "false"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            detail = getattr(exc.response, "text", "") if exc.response is not None else ""
            raise ComfyUIError(f"The image could not be uploaded to ComfyUI. {detail or exc}") from exc
        uploaded_name = data.get("name")
        if not uploaded_name:
            raise ComfyUIError("ComfyUI did not confirm the image upload.")
        subfolder = data.get("subfolder", "")
        return f"{subfolder}/{uploaded_name}" if subfolder else uploaded_name

    def queue_prompt(self, workflow: dict[str, Any]) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow, "client_id": self.client_id},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            detail = getattr(exc.response, "text", "") if exc.response is not None else ""
            raise ComfyUIError(f"ComfyUI is unreachable or rejected the workflow. {detail or exc}") from exc
        if not data.get("prompt_id"):
            raise ComfyUIError("ComfyUI did not accept the request: prompt_id is missing.")
        return data["prompt_id"]

    def get_history(self, prompt_id: str) -> dict[str, Any]:
        """Haalt de ComfyUI history voor één prompt op."""
        try:
            response = requests.get(
                f"{self.base_url}/history/{prompt_id}",
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            detail = getattr(exc.response, "text", "") if exc.response is not None else ""
            raise ComfyUIError(
                f"The ComfyUI render status could not be retrieved. {detail or exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ComfyUIError("ComfyUI returned an invalid history response.")

        return data

    def get_completed_output(self, prompt_id: str) -> dict[str, str] | None:
        """
        Geeft het eerste voltooide outputbestand terug.
        SaveVideo verschijnt in de history onder outputs -> node -> images.
        """
        history = self.get_history(prompt_id)
        entry = history.get(prompt_id)

        if not isinstance(entry, dict):
            return None

        status = entry.get("status", {})
        if not status.get("completed"):
            return None

        if status.get("status_str") != "success":
            raise ComfyUIError(
                f"ComfyUI did not complete prompt {prompt_id} successfully."
            )

        outputs = entry.get("outputs", {})
        for node_output in outputs.values():
            for item in node_output.get("images", []):
                filename = item.get("filename")
                if not filename:
                    continue

                return {
                    "filename": filename,
                    "subfolder": item.get("subfolder", ""),
                    "type": item.get("type", "output"),
                }

        raise ComfyUIError(
            "The render is complete, but ComfyUI reported no video output."
        )

    def get_used_seed(
        self,
        prompt_id: str,
        node_id: str,
        input_name: str,
    ) -> int | None:
        """
        Leest de werkelijk gebruikte seed terug uit ComfyUI history.

        Bij RandomNoise met control_after_generate='randomize' blijft
        de API-prompt de ingestelde sentinel (bijv. 0) bevatten. De
        werkelijk gekozen seed staat daarna in extra_pnginfo -> workflow
        -> nodes -> widgets_values_named.
        """
        history = self.get_history(prompt_id)
        entry = history.get(prompt_id)

        if not isinstance(entry, dict):
            return None

        prompt_data = entry.get("prompt")

        if not isinstance(prompt_data, list):
            return None

        # 1. Eerst de editor-workflow metadata controleren.
        # Dit is waar ComfyUI de na randomize werkelijk gebruikte
        # noise_seed bewaart.
        if len(prompt_data) >= 3 and isinstance(prompt_data[2], dict):

            extra_pnginfo = prompt_data[2].get(
                "extra_pnginfo",
                {},
            )

            editor_workflow = extra_pnginfo.get(
                "workflow",
                {},
            )

            nodes = editor_workflow.get(
                "nodes",
                [],
            )

            if isinstance(nodes, list):

                for node in nodes:

                    if not isinstance(node, dict):
                        continue

                    if str(node.get("id")) != str(node_id):
                        continue

                    named_values = node.get(
                        "widgets_values_named",
                        {},
                    )

                    if isinstance(named_values, dict):

                        value = named_values.get(
                            input_name
                        )

                        if (
                            not isinstance(value, bool)
                            and isinstance(value, (int, float))
                        ):
                            return int(value)

                    # Fallback voor nodes die geen
                    # widgets_values_named opslaan.
                    widget_values = node.get(
                        "widgets_values",
                        [],
                    )

                    if (
                        isinstance(widget_values, list)
                        and widget_values
                        and not isinstance(widget_values[0], bool)
                        and isinstance(widget_values[0], (int, float))
                    ):
                        return int(widget_values[0])

        # 2. Fallback naar de API-workflow.
        # Dit kan bij randomize nog 0/-1 zijn, maar is bruikbaar
        # voor een expliciet ingevulde vaste seed.
        if (
            len(prompt_data) >= 2
            and isinstance(prompt_data[1], dict)
        ):

            api_workflow = prompt_data[1]
            node = api_workflow.get(str(node_id))

            if isinstance(node, dict):

                inputs = node.get(
                    "inputs",
                    {},
                )

                value = inputs.get(
                    input_name
                )

                if (
                    not isinstance(value, bool)
                    and isinstance(value, (int, float))
                ):
                    return int(value)

        return None


    def get_execution_seconds(
        self,
        prompt_id: str,
    ) -> float | None:
        """Berekent de ComfyUI uitvoeringstijd uit execution_start/success."""
        history = self.get_history(prompt_id)
        entry = history.get(prompt_id)

        if not isinstance(entry, dict):
            return None

        status = entry.get("status", {})
        messages = status.get("messages", [])

        start_ms = None
        success_ms = None

        for message in messages:

            if (
                not isinstance(message, list)
                or len(message) < 2
                or not isinstance(message[1], dict)
            ):
                continue

            event_name = message[0]
            timestamp = message[1].get("timestamp")

            if not isinstance(timestamp, (int, float)):
                continue

            if event_name == "execution_start":
                start_ms = timestamp

            elif event_name == "execution_success":
                success_ms = timestamp

        if (
            start_ms is None
            or success_ms is None
            or success_ms < start_ms
        ):
            return None

        return round(
            (success_ms - start_ms) / 1000.0,
            2,
        )


    def download_output(
        self,
        filename: str,
        subfolder: str = "",
        output_type: str = "output",
    ) -> bytes:
        """Haalt het originele outputbestand rechtstreeks uit ComfyUI op."""
        try:
            response = requests.get(
                f"{self.base_url}/view",
                params={
                    "filename": filename,
                    "subfolder": subfolder,
                    "type": output_type,
                },
                timeout=max(self.timeout, 120),
            )
            response.raise_for_status()
            return response.content
        except requests.RequestException as exc:
            detail = getattr(exc.response, "text", "") if exc.response is not None else ""
            raise ComfyUIError(
                f"The rendered video could not be retrieved from ComfyUI. {detail or exc}"
            ) from exc

