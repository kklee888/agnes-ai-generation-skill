#!/usr/bin/env python3
"""Small CLI for Agnes AI text, image, and video generation APIs."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any


BASE_URL = "https://apihub.agnes-ai.com"
TEXT_MODEL = "agnes-2.0-flash"
IMAGE_MODEL = "agnes-image-2.1-flash"
VIDEO_MODEL = "agnes-video-v2.0"


def get_api_key() -> str:
    for name in ("AGNES_API_KEY", "AGNES_API_TOKEN", "APIHUB_AGNES_API_KEY"):
        value = os.environ.get(name)
        if value:
            return value
    raise SystemExit(
        "Missing API key. Set AGNES_API_KEY, AGNES_API_TOKEN, or APIHUB_AGNES_API_KEY."
    )


def request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {get_api_key()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            text = resp.read().decode("utf-8")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {path}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Request failed for {path}: {exc}") from exc


def request_text(method: str, path: str, payload: dict[str, Any] | None = None) -> str:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {get_api_key()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {path}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Request failed for {path}: {exc}") from exc


def stream_summary(payload: dict[str, Any]) -> dict[str, Any]:
    raw = request_text("POST", "/v1/chat/completions", payload)
    event_count = 0
    done = False
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if data == "[DONE]":
            done = True
        elif data:
            event_count += 1
    return {"events": event_count, "done": done, "raw_prefix": raw[:200]}


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def needs_english_translation(prompt: str) -> bool:
    return any(ord(ch) > 127 for ch in prompt)


def translate_prompt_to_english(prompt: str) -> str:
    payload = {
        "model": TEXT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Translate the user's image/video generation prompt into fluent English. "
                    "Preserve all concrete visual details, style words, camera motion, lighting, "
                    "composition constraints, and negative instructions. Return only the English prompt."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 800,
    }
    data = request_json("POST", "/v1/chat/completions", payload)
    try:
        translated = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise SystemExit(f"Prompt translation failed: {json.dumps(data, ensure_ascii=False)}") from exc
    if not translated:
        raise SystemExit("Prompt translation failed: empty translated prompt")
    return translated


def prepare_generation_prompt(prompt: str, translate: bool = True) -> str:
    if translate and needs_english_translation(prompt):
        return translate_prompt_to_english(prompt)
    return prompt


def cmd_text(args: argparse.Namespace) -> None:
    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": args.prompt})
    payload: dict[str, Any] = {
        "model": TEXT_MODEL,
        "messages": messages,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }
    if args.top_p is not None:
        payload["top_p"] = args.top_p
    if args.stream:
        payload["stream"] = True
    if args.tools_json:
        payload["tools"] = json.loads(args.tools_json)
    if args.tool_choice_json:
        payload["tool_choice"] = json.loads(args.tool_choice_json)
    if args.stream:
        print_json(stream_summary(payload))
    else:
        print_json(request_json("POST", "/v1/chat/completions", payload))


def cmd_image(args: argparse.Namespace) -> None:
    prompt = prepare_generation_prompt(args.prompt, not args.no_translate_prompt)
    payload: dict[str, Any] = {
        "model": IMAGE_MODEL,
        "prompt": prompt,
    }
    if args.size:
        payload["size"] = args.size
    extra: dict[str, Any] = {"response_format": "url"}
    if args.image:
        extra["image"] = args.image
    if extra:
        payload["extra_body"] = extra
    print_json(request_json("POST", "/v1/images/generations", payload))


def video_payload(args: argparse.Namespace) -> dict[str, Any]:
    prompt = prepare_generation_prompt(args.prompt, not args.no_translate_prompt)
    payload: dict[str, Any] = {
        "model": VIDEO_MODEL,
        "prompt": prompt,
    }
    for name in (
        "height",
        "width",
        "num_frames",
        "frame_rate",
        "num_inference_steps",
        "seed",
        "negative_prompt",
    ):
        value = getattr(args, name)
        if value is not None:
            payload[name] = value
    if args.mode:
        payload["mode"] = args.mode
    if args.image:
        if len(args.image) == 1 and args.mode != "keyframes":
            payload["image"] = args.image[0]
        else:
            payload["extra_body"] = {"image": args.image}
            if args.mode:
                payload["extra_body"]["mode"] = args.mode
    return payload


def poll_video(task_id: str, timeout: int, interval: int) -> dict[str, Any]:
    deadline = time.time() + timeout
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = request_json("GET", f"/v1/videos/{task_id}")
        if "error" in last:
            raise SystemExit(f"Video task {task_id} returned error: {json.dumps(last, ensure_ascii=False)}")
        status = str(last.get("status", "")).lower()
        if status in {"completed", "failed"}:
            return last
        time.sleep(interval)
    raise SystemExit(f"Timed out waiting for video task {task_id}. Last response: {json.dumps(last)}")


def cmd_video(args: argparse.Namespace) -> None:
    created = request_json("POST", "/v1/videos", video_payload(args))
    if not args.poll:
        print_json(created)
        return
    task_id = created.get("id")
    if not task_id:
        raise SystemExit(f"Video create response did not include id: {json.dumps(created)}")
    print_json(poll_video(str(task_id), args.timeout, args.interval))


def cmd_video_get(args: argparse.Namespace) -> None:
    print_json(request_json("GET", f"/v1/videos/{args.task_id}"))


def require_ok(name: str, data: dict[str, Any], keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if key not in data]
    if missing:
        raise SystemExit(f"{name} response missing {missing}: {json.dumps(data)}")
    print(f"{name}: ok")


def require_video_ok(name: str, data: dict[str, Any], completed: bool = False) -> None:
    require_ok(name, data, ("id", "status"))
    status = str(data.get("status", "")).lower()
    if status == "failed":
        raise SystemExit(f"{name} failed: {json.dumps(data, ensure_ascii=False)}")
    if completed and status != "completed":
        raise SystemExit(f"{name} did not complete: {json.dumps(data, ensure_ascii=False)}")


def extract_image_url(data: dict[str, Any]) -> str:
    candidates = []
    if isinstance(data.get("url"), str):
        candidates.append(data["url"])
    if isinstance(data.get("image_url"), str):
        candidates.append(data["image_url"])
    if isinstance(data.get("data"), list):
        for item in data["data"]:
            if isinstance(item, dict):
                for key in ("url", "image_url"):
                    if isinstance(item.get(key), str):
                        candidates.append(item[key])
    if not candidates:
        raise SystemExit(f"Could not find image URL in response: {json.dumps(data, ensure_ascii=False)}")
    return candidates[0]


def create_video_case(name: str, payload: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    created = request_json("POST", "/v1/videos", payload)
    require_video_ok(f"{name}-create", created)
    task_id = str(created["id"])
    retrieved = (
        poll_video(task_id, args.video_timeout, args.video_interval)
        if args.poll_video
        else request_json("GET", f"/v1/videos/{task_id}")
    )
    require_video_ok(f"{name}-get", retrieved, completed=args.poll_video)
    return {"create": created, "get": retrieved}


VIDEO_CASES = ("text-to-video", "image-to-video", "multi-image", "keyframes")


def cmd_smoke_test(args: argparse.Namespace) -> None:
    text = request_json(
        "POST",
        "/v1/chat/completions",
        {
            "model": TEXT_MODEL,
            "messages": [{"role": "user", "content": "Reply with exactly: Agnes text ok"}],
            "max_tokens": 20,
            "temperature": 0,
        },
    )
    require_ok("text", text, ("choices",))

    text_stream = stream_summary(
        {
            "model": TEXT_MODEL,
            "messages": [{"role": "user", "content": "Reply with exactly: Agnes stream ok"}],
            "max_tokens": 20,
            "temperature": 0,
            "stream": True,
        }
    )
    if text_stream["events"] < 1 and not text_stream["done"]:
        raise SystemExit(f"text-stream response did not look like SSE: {json.dumps(text_stream)}")
    print("text-stream: ok")

    text_tools = request_json(
        "POST",
        "/v1/chat/completions",
        {
            "model": TEXT_MODEL,
            "messages": [{"role": "user", "content": "Use the get_test_value tool."}],
            "max_tokens": 128,
            "temperature": 0,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_test_value",
                        "description": "Return a deterministic smoke test value.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string", "description": "test label"}
                            },
                            "required": ["label"],
                        },
                    },
                }
            ],
            "tool_choice": {"type": "function", "function": {"name": "get_test_value"}},
        },
    )
    require_ok("text-tools", text_tools, ("choices",))

    image_text = request_json(
        "POST",
        "/v1/images/generations",
        {
            "model": IMAGE_MODEL,
            "prompt": "A simple red square icon centered on a white background",
            "size": args.image_size,
            "extra_body": {"response_format": "url"},
        },
    )
    require_ok("image-text-to-image", image_text, ("data",))
    generated_image_url = extract_image_url(image_text)

    image_edit = request_json(
        "POST",
        "/v1/images/generations",
        {
            "model": IMAGE_MODEL,
            "prompt": "Turn this into a clean blue square icon while preserving the centered composition",
            "size": args.image_size,
            "extra_body": {"image": [generated_image_url], "response_format": "url"},
        },
    )
    require_ok("image-to-image", image_edit, ("data",))
    edited_image_url = extract_image_url(image_edit)

    video_common = {
        "model": VIDEO_MODEL,
    }
    for key, value in (
        ("height", args.video_height),
        ("width", args.video_width),
        ("num_frames", args.video_num_frames),
        ("frame_rate", args.video_frame_rate),
    ):
        if value is not None:
            video_common[key] = value
    selected_cases = set(args.video_case or VIDEO_CASES)
    video_results = {}
    if "text-to-video" in selected_cases:
        video_results["text_to_video"] = create_video_case(
            "video-text-to-video",
            {
                **video_common,
                "prompt": "A simple cinematic shot of a red square gently moving on a white background",
            },
            args,
        )
    if "image-to-video" in selected_cases:
        video_results["image_to_video"] = create_video_case(
            "video-image-to-video",
            {
                **video_common,
                "prompt": "Animate the icon with subtle floating motion, stable centered composition",
                "image": generated_image_url,
            },
            args,
        )
    if "multi-image" in selected_cases:
        video_results["multi_image"] = create_video_case(
            "video-multi-image",
            {
                **video_common,
                "prompt": "Create a smooth transformation from the first icon to the second icon, stable centered composition",
                "extra_body": {"image": [generated_image_url, edited_image_url]},
            },
            args,
        )
    if "keyframes" in selected_cases:
        video_results["keyframes"] = create_video_case(
            "video-keyframes",
            {
                **video_common,
                "prompt": "Create a smooth keyframe transition between the two icons, stable centered composition",
                "extra_body": {"image": [generated_image_url, edited_image_url], "mode": "keyframes"},
            },
            args,
        )
    print_json(
        {
            "text": text,
            "text_stream": text_stream,
            "text_tools": text_tools,
            "image_text_to_image": image_text,
            "image_to_image": image_edit,
            "video": video_results,
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Call Agnes AI generation APIs.")
    sub = parser.add_subparsers(dest="command", required=True)

    text = sub.add_parser("text", help="Create a chat completion.")
    text.add_argument("--prompt", required=True)
    text.add_argument("--system")
    text.add_argument("--temperature", type=float, default=0.7)
    text.add_argument("--top-p", type=float)
    text.add_argument("--max-tokens", type=int, default=1024)
    text.add_argument("--stream", action="store_true")
    text.add_argument("--tools-json", help="JSON array for OpenAI-compatible tool definitions.")
    text.add_argument("--tool-choice-json", help="JSON object/string for OpenAI-compatible tool_choice.")
    text.set_defaults(func=cmd_text)

    image = sub.add_parser("image", help="Generate or edit an image.")
    image.add_argument("--prompt", required=True)
    image.add_argument("--size", default="1024x768")
    image.add_argument("--image", action="append", help="Input image URL. Repeat for multiple images.")
    image.add_argument(
        "--no-translate-prompt",
        action="store_true",
        help="Do not translate non-English prompts before sending to the image API.",
    )
    image.set_defaults(func=cmd_image)

    video = sub.add_parser("video", help="Create a video task.")
    video.add_argument("--prompt", required=True)
    video.add_argument("--image", action="append", help="Input image URL. Repeat for multi-image or keyframes.")
    video.add_argument("--mode", choices=("ti2vid", "keyframes"))
    video.add_argument("--height", type=int)
    video.add_argument("--width", type=int)
    video.add_argument("--num-frames", type=int)
    video.add_argument("--frame-rate", type=float)
    video.add_argument("--num-inference-steps", type=int)
    video.add_argument("--seed", type=int)
    video.add_argument("--negative-prompt")
    video.add_argument(
        "--no-translate-prompt",
        action="store_true",
        help="Do not translate non-English prompts before sending to the video API.",
    )
    video.add_argument("--poll", action="store_true")
    video.add_argument("--timeout", type=int, default=900)
    video.add_argument("--interval", type=int, default=10)
    video.set_defaults(func=cmd_video)

    video_get = sub.add_parser("video-get", help="Retrieve a video task.")
    video_get.add_argument("task_id")
    video_get.set_defaults(func=cmd_video_get)

    smoke = sub.add_parser("smoke-test", help="Run live text, image, and video API tests.")
    smoke.add_argument("--image-size", default="1024x768")
    smoke.add_argument("--video-height", type=int)
    smoke.add_argument("--video-width", type=int)
    smoke.add_argument("--video-num-frames", type=int)
    smoke.add_argument("--video-frame-rate", type=float)
    smoke.add_argument("--poll-video", action="store_true")
    smoke.add_argument("--video-timeout", type=int, default=900)
    smoke.add_argument("--video-interval", type=int, default=10)
    smoke.add_argument(
        "--video-case",
        action="append",
        choices=VIDEO_CASES,
        help="Video case to test. Repeat to test multiple cases.",
    )
    smoke.set_defaults(func=cmd_smoke_test)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
