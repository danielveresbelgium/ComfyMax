from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import requests


class LMStudioError(RuntimeError):
    """Readable error raised for LM Studio communication failures."""


@dataclass(frozen=True)
class GeneratedPrompt:
    text: str
    model: str
    instance_id: str | None


class LMStudioClient:
    def __init__(self, base_url: str, timeout: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        try:
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                timeout=self.timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            detail = getattr(exc.response, "text", "") if exc.response is not None else ""
            raise LMStudioError(
                f"LM Studio is unreachable or returned an error at {path}. {detail or exc}"
            ) from exc

    def list_models(self) -> list[str]:
        data = self._request("GET", "/v1/models").json()
        return [item["id"] for item in data.get("data", []) if item.get("id")]

    def _find_instance_id(self, model: str) -> str | None:
        try:
            data = self._request("GET", "/api/v1/models").json()
        except LMStudioError:
            return None

        models = data.get(
            "models",
            data.get("data", data if isinstance(data, list) else []),
        )

        for item in models if isinstance(models, list) else []:
            if item.get("key") == model or item.get("id") == model or item.get("model") == model:
                instances = item.get("loaded_instances", item.get("instances", []))
                if instances:
                    return instances[0].get("id") or instances[0].get("instance_id")
        return None

    def load_model(self, model: str) -> str:
        data = self._request(
            "POST",
            "/api/v1/models/load",
            json={"model": model},
        ).json()

        instance_id = data.get("instance_id") or data.get("model_instance_id")
        if not instance_id:
            raise LMStudioError(
                "LM Studio loaded the model but did not return an instance_id."
            )
        return instance_id

    def generate_prompt(
        self,
        user_request: str,
        model: str,
        system_prompt: str,
        temperature: float = 0.7,
        images: list[tuple[bytes, str | None]] | None = None,
    ) -> GeneratedPrompt:
        user_content: str | list[dict[str, Any]]

        if images:
            user_content = [{"type": "text", "text": user_request}]
            for index, (image_data, image_mime_type) in enumerate(images, start=1):
                mime_type = image_mime_type or "image/png"
                encoded_image = base64.b64encode(image_data).decode("ascii")
                user_content.append({"type": "text", "text": f"<Picture {index}>"})
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{encoded_image}"},
                })
        else:
            user_content = user_request

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": temperature,
        }

        data = self._request(
            "POST",
            "/v1/chat/completions",
            json=payload,
        ).json()

        try:
            text = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LMStudioError("LM Studio did not return a usable prompt.") from exc

        return GeneratedPrompt(
            text=text,
            model=data.get("model", model),
            instance_id=self._find_instance_id(model),
        )

    def unload_model(self, instance_id: str | None) -> None:
        if not instance_id:
            raise LMStudioError(
                "No LM Studio instance_id was found. Unload the model manually "
                "or check the LM Studio REST API."
            )

        self._request(
            "POST",
            "/api/v1/models/unload",
            json={"instance_id": instance_id},
        )
