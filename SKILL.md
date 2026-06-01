---
name: agnes-ai-generation
description: Call Agnes AI / Sapiens AI generation APIs for text, image, and video. Use when the user asks to use Agnes models, Agnes Image, Agnes Video, Agnes 2.0 Flash, apihub.agnes-ai.com, or to generate text, images, edit images, create videos, animate images, create keyframe videos, or test Agnes API calls.
---

# Agnes AI Generation

Use this skill to call Agnes text, image, and video generation APIs through `https://apihub.agnes-ai.com`.

## Quick Start

1. Read `references/api.md` when endpoint details, parameters, or response fields are needed.
2. Use `scripts/agnes_api.py` for real API calls instead of rewriting curl by hand.
3. Require an API key in `AGNES_API_KEY`, `AGNES_API_TOKEN`, or `APIHUB_AGNES_API_KEY`. Never print the key.
4. For live verification, run the script's `smoke-test` command. Treat the skill as fully tested only when basic text, text streaming, text tool calling, text-to-image, image-to-image, text-to-video, image-to-video, multi-image video, keyframe video, and video retrieval return successful responses.

## Commands

Text generation:

```bash
python scripts/agnes_api.py text --prompt "Write a concise product tagline for an AI assistant."
```

Streaming text:

```bash
python scripts/agnes_api.py text --prompt "Write a short product intro." --stream
```

Image generation:

```bash
python scripts/agnes_api.py image --prompt "A luminous floating city above a misty canyon at sunrise, cinematic realism" --size 1024x768
```

Image-to-image:

```bash
python scripts/agnes_api.py image --prompt "Turn the scene into a rainy cyberpunk night while preserving composition" --image https://example.com/input.png --size 1024x768
```

Text-to-video with polling:

```bash
python scripts/agnes_api.py video --prompt "A cinematic shot of a cat walking on the beach at sunset" --poll
```

Image-to-video:

```bash
python scripts/agnes_api.py video --prompt "Animate subtle camera movement and natural lighting" --image https://example.com/image.png --poll
```

Keyframe / multi-image video:

```bash
python scripts/agnes_api.py video --prompt "Create a smooth cinematic transition between the two keyframes" --image https://example.com/a.png --image https://example.com/b.png --mode keyframes --poll
```

Retrieve a video task:

```bash
python scripts/agnes_api.py video-get task_123456
```

Live smoke test:

```bash
python scripts/agnes_api.py smoke-test --poll-video
```

## Workflow

- Prefer `agnes-2.0-flash` for text chat/completions.
- Prefer `agnes-image-2.1-flash` for text-to-image, image-to-image, and high-information-density image generation. High-density generation is prompt-driven; include subject hierarchy, environment, secondary details, lighting, composition, and quality requirements.
- Prefer `agnes-video-v2.0` for text-to-video, image-to-video, multi-image video, keyframe animation, prompt-based motion and scene control, cinematic output, asynchronous task creation, polling-based result retrieval, and seed-based reproducibility.
- For image and video generation, convert any non-English user prompt to a fluent English generation prompt before calling the image/video API. English prompts are more stable for Agnes video generation. Preserve concrete visual details, style, lighting, composition, motion, camera instructions, and constraints during translation.
- For videos, remember the API is asynchronous: create a task first, then poll or retrieve by task id.
- Keep video smoke tests small but valid: `num_frames` must be `8n + 1` and `<= 441`; `81` or `121` are good short-test values.
- Warn the user before costly or long-running live video generation unless they explicitly asked to test or generate video.
- Test video capabilities one at a time with `smoke-test --video-case <case>` to avoid creating many tasks at once. Supported cases are `text-to-video`, `image-to-video`, `multi-image`, and `keyframes`.

## Current Validation Notes

- Confirmed locally: skill metadata validation and Python syntax.
- Confirmed by live API: basic text, streaming text, tool-calling request shape, text-to-image, image-to-image, and high-information-density text-to-image.
- Partially confirmed by live API: video task creation and video task retrieval endpoint reachability.
- Not yet confirmed end-to-end: completed `video_url` retrieval for text-to-video, image-to-video, multi-image video, and keyframe animation. The first live text-to-video task returned a provider-side `division by zero` error when retrieved, so do not mark all video modes as fully passed until a task reaches `completed`.

## Output Handling

- Return or save generated URLs from the JSON response.
- For image responses, expect URL-style results when `extra_body.response_format` is `url`.
- For video responses, `video_url` appears only when `status` is `completed`.
- If a request fails, report HTTP status and provider error body without exposing the API key.
