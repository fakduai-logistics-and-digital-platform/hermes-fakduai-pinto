#!/usr/bin/env python3
"""Patch Hermes OpenAI image provider for OpenAI-compatible image endpoints.

Hermes upstream OpenAI image provider is hard-coded for gpt-image-2 and
openai.OpenAI() default env vars. This patch adds image-only env overrides:

- OPENAI_IMAGE_API_KEY
- OPENAI_IMAGE_BASE_URL
- OPENAI_IMAGE_API_MODEL
- OPENAI_IMAGE_MODEL
"""
from __future__ import annotations

from pathlib import Path

TARGET = Path("/usr/local/lib/python3.11/site-packages/plugins/image_gen/openai/__init__.py")


def replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        if new in text:
            return text
        raise SystemExit(f"patch target not found: {old[:80]!r}")
    return text.replace(old, new, 1)


def main() -> None:
    text = TARGET.read_text()

    text = replace_once(
        text,
        '''    env_override = os.environ.get("OPENAI_IMAGE_MODEL")\n    if env_override and env_override in _MODELS:\n        return env_override, _MODELS[env_override]\n''',
        '''    api_model_override = os.environ.get("OPENAI_IMAGE_API_MODEL")\n    env_override = os.environ.get("OPENAI_IMAGE_MODEL")\n    if api_model_override:\n        return env_override or "custom", {\n            "display": api_model_override,\n            "speed": "varies",\n            "strengths": "Custom OpenAI-compatible image model",\n            "quality": "",\n        }\n    if env_override and env_override in _MODELS:\n        return env_override, _MODELS[env_override]\n''',
    )

    text = replace_once(
        text,
        '''        payload: Dict[str, Any] = {\n            "model": API_MODEL,\n            "prompt": prompt,\n            "size": size,\n            "n": 1,\n            "quality": meta["quality"],\n        }\n''',
        '''        api_model = os.environ.get("OPENAI_IMAGE_API_MODEL") or API_MODEL\n        payload: Dict[str, Any] = {\n            "model": api_model,\n            "prompt": prompt,\n            "size": size,\n            "n": 1,\n        }\n        if meta.get("quality"):\n            payload["quality"] = meta["quality"]\n''',
    )

    text = replace_once(
        text,
        '''            client = openai.OpenAI()\n            response = client.images.generate(**payload)\n''',
        '''            api_key = os.environ.get("OPENAI_IMAGE_API_KEY") or os.environ.get("OPENAI_API_KEY")\n            base_url = os.environ.get("OPENAI_IMAGE_BASE_URL") or os.environ.get("OPENAI_BASE_URL")\n            client = openai.OpenAI(api_key=api_key, base_url=base_url)\n            response = client.images.generate(**payload)\n''',
    )

    text = replace_once(
        text,
        '''        extra: Dict[str, Any] = {"size": size, "quality": meta["quality"]}\n''',
        '''        extra: Dict[str, Any] = {"size": size}\n        if meta.get("quality"):\n            extra["quality"] = meta["quality"]\n''',
    )

    TARGET.write_text(text)
    print(f"patched {TARGET}")


if __name__ == "__main__":
    main()
