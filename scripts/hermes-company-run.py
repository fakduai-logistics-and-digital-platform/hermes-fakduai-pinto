#!/usr/bin/env python3
"""Run a local Hermes-only company workflow.

This is not OpenClaw and does not touch ~/.openclaw. It reads personas from
hermes-config/config.yaml:

  platforms.pinto.extra.pintoAgents.<persona_key>.channelPrompt

Then runs a sequential handoff chain against Hermes API Server /v1/responses.
Outputs are written under hermes-config/company-runs/ (ignored by git).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: pip install pyyaml") from exc


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "hermes-config" / "config.yaml"
ENV_PATHS = [ROOT / "hermes-config" / ".env", ROOT / ".env"]
RUNS_DIR = ROOT / "hermes-config" / "company-runs"
DEFAULT_API_BASE = "http://127.0.0.1:8642"


def load_dotenv(paths: list[Path]) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in paths:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    return values


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise SystemExit(f"config not found: {CONFIG_PATH}")
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"config must be a map: {CONFIG_PATH}")
    return data


def pinto_extra(config: dict[str, Any]) -> dict[str, Any]:
    extra = (((config.get("platforms") or {}).get("pinto") or {}).get("extra") or {})
    return extra if isinstance(extra, dict) else {}


def load_personas(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = pinto_extra(config).get("pintoAgents") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def workflow_order(config: dict[str, Any], explicit: list[str] | None) -> list[str]:
    if explicit:
        return explicit
    extra = pinto_extra(config)
    workflows = extra.get("companyWorkflows") or {}
    if isinstance(workflows, dict):
        default = workflows.get("default")
        if isinstance(default, list):
            return [str(x) for x in default]
    return list(load_personas(config).keys())


def persona_prompt(key: str, cfg: dict[str, Any]) -> str:
    prompt = cfg.get("channelPrompt") or cfg.get("prompt") or cfg.get("systemPrompt")
    role = cfg.get("role") or cfg.get("name") or key
    if prompt:
        return str(prompt).strip()
    return f"You are {role}. Stay in this role. Produce clear handoff-ready output."


def call_hermes(api_base: str, api_key: str, session_id: str, key: str, prompt: str, message: str, timeout: int) -> str:
    body = {
        "model": os.environ.get("HERMES_MODEL"),
        "instructions": prompt,
        "input": message,
        "session_id": f"company:{session_id}:{key}",
        "store": True,
    }
    body = {k: v for k, v in body.items() if v is not None}
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}/v1/responses",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"Hermes HTTP {exc.code}: {detail}") from exc

    text = data.get("output_text")
    if text:
        return str(text)
    output = data.get("output")
    if isinstance(output, list):
        chunks: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("text"):
                        chunks.append(str(part["text"]))
            elif item.get("text"):
                chunks.append(str(item["text"]))
        if chunks:
            return "\n".join(chunks).strip()
    if data.get("final_response"):
        return str(data["final_response"])
    return json.dumps(data, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Hermes-only persona handoff workflow")
    parser.add_argument("task", help="task/objective for the company workflow")
    parser.add_argument("--agents", nargs="+", help="persona keys to run in order")
    parser.add_argument("--api-base", default=os.environ.get("HERMES_API_BASE", DEFAULT_API_BASE))
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--dry-run", action="store_true", help="print planned chain without calling Hermes")
    args = parser.parse_args()

    env = load_dotenv(ENV_PATHS)
    api_key = os.environ.get("API_SERVER_KEY") or env.get("API_SERVER_KEY")
    if not api_key and not args.dry_run:
        raise SystemExit("API_SERVER_KEY not found in environment, hermes-config/.env, or .env")

    config = load_config()
    personas = load_personas(config)
    if not personas:
        raise SystemExit("No personas found at platforms.pinto.extra.pintoAgents")

    chain = workflow_order(config, args.agents)
    missing = [key for key in chain if key not in personas]
    if missing:
        raise SystemExit(f"Unknown persona key(s): {', '.join(missing)}")

    session_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print("Hermes company workflow")
    print(f"task: {args.task}")
    print("chain: " + " -> ".join(chain))

    if args.dry_run:
        return 0

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []
    handoff = args.task
    for i, key in enumerate(chain, start=1):
        cfg = personas[key]
        name = cfg.get("name") or key
        print(f"[{i}/{len(chain)}] {key} ({name}) ...", flush=True)
        user_message = (
            f"Company workflow task:\n{args.task}\n\n"
            f"Current handoff/input for persona '{key}':\n{handoff}\n\n"
            "Return concise output plus any explicit handoff notes for the next persona."
        )
        started = time.time()
        output = call_hermes(
            api_base=args.api_base,
            api_key=api_key or "",
            session_id=session_id,
            key=key,
            prompt=persona_prompt(key, cfg),
            message=user_message,
            timeout=args.timeout,
        )
        elapsed = round(time.time() - started, 3)
        steps.append({"persona": key, "name": name, "elapsed_seconds": elapsed, "output": output})
        handoff = output

    run = {
        "id": session_id,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "task": args.task,
        "chain": chain,
        "steps": steps,
        "final_output": handoff,
    }
    out = RUNS_DIR / f"{session_id}.json"
    out.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"saved: {out}")
    print("\nfinal output:\n" + handoff)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
