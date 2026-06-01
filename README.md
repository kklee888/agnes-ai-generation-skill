# Agnes AI Generation Skill

Codex skill for calling Agnes AI text, image, and video generation APIs.

Repository: `Yacey/agnes-ai-generation-skill`

## Install

Install with `npx skills add`:

```powershell
npx skills add Yacey/agnes-ai-generation-skill --skill agnes-ai-generation --agent codex --copy -g -y
```

## API Key

Set one of these environment variables before making live API calls:

```powershell
$env:AGNES_API_KEY="YOUR_API_KEY"
```

For persistent Windows user-level configuration:

```powershell
[Environment]::SetEnvironmentVariable("AGNES_API_KEY", "YOUR_API_KEY", "User")
```

The API key is not stored in this repository.

## Capabilities

- Text generation with `agnes-2.0-flash`
- Streaming text responses
- OpenAI-compatible tool-calling request shape
- Text-to-image with `agnes-image-2.1-flash`
- Image-to-image editing with `agnes-image-2.1-flash`
- High-information-density image prompts
- Text-to-video with `agnes-video-v2.0`
- Image-to-video with `agnes-video-v2.0`
- Multi-image video generation
- Keyframe animation
- Prompt-based motion and scene control
- Cinematic video output
- Asynchronous video task creation
- Polling-based video result retrieval
- Seed-based reproducibility

## Prompt Language

For image and video generation, non-English prompts are translated to English before calling Agnes image/video APIs. This is especially important for video generation, where English prompts are more stable.

The script preserves visual details, style, lighting, composition, motion, camera movement, and constraints during translation. To skip this behavior:

```powershell
python scripts/agnes_api.py image --prompt "中文提示词" --no-translate-prompt
python scripts/agnes_api.py video --prompt "中文提示词" --no-translate-prompt
```

## Usage

Text:

```powershell
python scripts/agnes_api.py text --prompt "Write a concise product tagline for an AI assistant."
```

Image:

```powershell
python scripts/agnes_api.py image --prompt "A luminous floating city above a misty canyon at sunrise, cinematic realism" --size 1024x768
```

Image-to-image:

```powershell
python scripts/agnes_api.py image --prompt "Turn the scene into a rainy cyberpunk night while preserving composition" --image https://example.com/input.png
```

Video:

```powershell
python scripts/agnes_api.py video --prompt "A cinematic shot of a cat walking on the beach at sunset" --poll
```

Retrieve a video task:

```powershell
python scripts/agnes_api.py video-get task_123456
```

Smoke test:

```powershell
python scripts/agnes_api.py smoke-test
```

Single video case test:

```powershell
python scripts/agnes_api.py smoke-test --video-case text-to-video
```

## Validation Status

Confirmed by live API:

- Basic text
- Streaming text
- Tool-calling request shape
- Text-to-image
- Image-to-image
- High-information-density text-to-image

Partially confirmed:

- Video task creation
- Video task retrieval endpoint reachability

Not fully confirmed end-to-end yet:

- Completed `video_url` retrieval for every video mode

The first live text-to-video retrieval returned a provider-side `division by zero` error, so video modes should be treated as supported by the skill but not fully passed until a task reaches `completed`.
