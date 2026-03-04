---
name: screen-recorder
description: Record macOS screen with verification, retry logic, and format conversion. Use when capturing screen recordings of windows or regions, creating GIFs for GitHub READMEs, recording demos for Discord, or making JetBrains marketplace media. Supports platform presets and automatic verification.
argument-hint: "[record|find|full-screen|region|check-deps] [app-name] [options]"
allowed-tools: Bash, Read
user-invocable: true
---

# macOS Screen Recorder

Record macOS screen with automatic verification, retry logic, and optimized format conversion. Captures screen recordings of specific windows or regions, converts to platform-optimized formats (GIF, WebP, MP4), and verifies the recording captured what you intended.

## Artifact Output Path

> **CRITICAL**: NEVER use `--output` unless the user EXPLICITLY states the artifact MUST be at a specific location. This should be EXTREMELY rare.

Recordings are automatically saved to `claude-code/artifacts/screen-recorder/` with timestamped filenames (e.g., `251216120000-recording_GoLand.gif`). The artifact path is always returned in the JSON output — use that path for subsequent operations.

## Quick Start

```bash
# Record a window for 5 seconds
claude-code-skills screen-recorder record "GoLand" -d 5 --json

# Record optimized for Discord upload (10MB max, WebP)
claude-code-skills screen-recorder record "GoLand" -d 5 --preset discord

# Record optimized for GitHub README (GIF, ~5MB)
claude-code-skills screen-recorder record "Code" -d 10 --preset github

# Record optimized for JetBrains Marketplace (1280x800 GIF)
claude-code-skills screen-recorder record "IntelliJ" -d 8 --preset jetbrains

# Record full screen
claude-code-skills screen-recorder full-screen -d 3

# Record window on different Space (no activation, ScreenCaptureKit)
claude-code-skills screen-recorder record "Terminal" -d 5 --backend screencapturekit

# Record absolute screen region
claude-code-skills screen-recorder region 100,200,800,600 -d 5

# Record window-relative region
claude-code-skills screen-recorder record "GoLand" --window-region 0,800,1600,400 -d 5

# Preview region before recording
claude-code-skills screen-recorder record "GoLand" --window-region 0,800,1600,400 --preview-region

# Check ffmpeg availability
claude-code-skills screen-recorder check-deps
```

## Recording Pipeline

1. **Window Discovery**: Uses `CGWindowListCopyWindowInfo` to find target window by app name, title pattern, PID, executable path, or command-line arguments.
2. **Activation** (optional): Activates the target app via AppleScript, switches to window's Space. Configurable settle time.
3. **Space Detection**: Detects if target window is on a different Space, switches there, re-finds window bounds, records, then returns to original Space.
4. **Screen Recording**: Uses native macOS `screencapture -v -R x,y,w,h -V duration` or ScreenCaptureKit for capture.
5. **Format Conversion**: Converts via ffmpeg — GIF (two-pass palette optimization), WebP (lossy animated), MP4 (H.264 yuv420p).
6. **Verification**: Runs verification strategies (basic, duration, frames, motion).
7. **Retry Loop**: On failure, retries up to N times with configurable delay.

See `references/backends.md` for detailed backend comparison.

## Platform Presets

| Preset      | Format | Max Size | FPS    | Max Width | Use Case           |
|:------------|:-------|:---------|:-------|:----------|:-------------------|
| `discord`   | WebP   | 10 MB    | 10     | 720px     | Discord (no Nitro) |
| `github`    | GIF    | 5 MB     | 10     | 600px     | README files       |
| `jetbrains` | GIF    | 20 MB    | 15     | 1280x800  | Plugin marketplace |
| `raw`       | MOV    | —        | native | —         | No conversion      |

## Region Recording

**Absolute Region** (`--region`, `-R`):

- Captures a fixed screen area: `x,y,width,height`
- Example: `-R 100,200,800,600`

**Window-Relative Region** (`--window-region`):

- Captures a region relative to a window's top-left corner
- Requires `--record` to specify the target window
- Example: `--record "GoLand" --window-region 0,800,1600,400`

Use `find` to discover window bounds before recording:

```bash
claude-code-skills screen-recorder find "GoLand" --json | jq '.bounds'
```

**Iterative Coordinate Refinement** (`--preview-region`):

```bash
# Preview estimated region
claude-code-skills screen-recorder record "GoLand" --window-region 0,890,2056,400 --preview-region
# View preview, adjust coordinates, then record when satisfied
```

## Space-Aware Recording

When recording windows on different macOS Spaces, the recorder automatically detects the target Space, switches there, re-finds window bounds, records, and returns to the original Space. No special flags required.

```bash
# Record Terminal on Space 2 while on Space 1
claude-code-skills screen-recorder record "Terminal" -d 5
```

Requirements: Accessibility permissions (System Settings > Privacy & Security > Accessibility). Use `--no-activate` to skip activation and Space switching.

## Verification Strategies

| Strategy   | Purpose           | Details                        |
|:-----------|:------------------|:-------------------------------|
| `basic`    | Sanity check      | File exists, >0 bytes          |
| `duration` | Correct length    | Duration +/-0.5s of requested  |
| `frames`   | Enough content    | >=80% of expected frames       |
| `motion`   | Content changed   | First/last frame hashes differ |
| `all`      | Full verification | All above strategies           |
| `none`     | Skip verification | Record only                    |

## Command Reference

### Actions

| Flag               | Short | Description                         |
|:-------------------|:------|:------------------------------------|
| `--record`         | `-r`  | Record window of specified app      |
| `--find`           | `-f`  | Find window without recording       |
| `--full-screen`    | `-F`  | Record entire screen                |
| `--preview-region` |       | Screenshot region for coord testing |
| `--check-deps`     |       | Check ffmpeg availability           |

### Window Filters

| Flag              | Short | Description                      |
|:------------------|:------|:---------------------------------|
| `--title`         | `-t`  | Regex pattern for window title   |
| `--pid`           |       | Filter by process ID             |
| `--path-contains` |       | Executable path must contain     |
| `--path-excludes` |       | Executable path must NOT contain |
| `--args`          |       | Command line must contain        |

### Recording Options

| Flag              | Short | Description                                     |
|:------------------|:------|:------------------------------------------------|
| `--duration`      | `-d`  | Recording duration in seconds (default: 10)     |
| `--max-duration`  |       | Maximum allowed duration (default: 60)          |
| `--region`        | `-R`  | Absolute screen region: x,y,width,height        |
| `--window-region` |       | Window-relative region (--record): x,y,w,h      |
| `--no-clicks`     |       | Don't show mouse clicks                         |
| `--no-activate`   |       | Don't activate window first                     |
| `--settle-ms`     |       | Wait time after activation (default: 500)       |
| `--backend`       |       | Capture backend: auto, quartz, screencapturekit |

### Output Options

| Flag         | Short | Description                                      |
|:-------------|:------|:-------------------------------------------------|
| `--output`   | `-o`  | Output file path                                 |
| `--format`   |       | Output format: gif, webp, mp4, mov               |
| `--preset`   | `-p`  | Platform preset: discord, github, jetbrains, raw |
| `--keep-raw` |       | Keep original .mov after conversion              |
| `--json`     | `-j`  | Output result as JSON                            |

### Format Settings (Override Preset)

| Flag              | Description                       |
|:------------------|:----------------------------------|
| `--fps`           | Target frame rate                 |
| `--max-width`     | Maximum width in pixels           |
| `--max-height`    | Maximum height in pixels          |
| `--quality`, `-q` | Quality for lossy formats (0-100) |
| `--max-size`      | Target maximum file size in MB    |

### Verification Options

| Flag       | Short | Description                                            |
|:-----------|:------|:-------------------------------------------------------|
| `--verify` | `-v`  | Strategies: basic, duration, frames, motion, all, none |

### Retry Options

| Flag               | Description                                |
|:-------------------|:-------------------------------------------|
| `--retries`        | Maximum retry attempts (default: 5)        |
| `--retry-delay`    | Delay between retries in ms (default: 500) |
| `--retry-strategy` | fixed, exponential, or reactivate          |

## Troubleshooting

### "ffmpeg not found"

```bash
brew install ffmpeg
claude-code-skills screen-recorder check-deps
```

### "No window found matching filter"

- Check if the app is running: `ps aux | grep -i appname`
- Use `find` to see what windows are available
- For sandbox IDEs, use `record "Main" --args "sandbox"`

### Recording is wrong size or window

- Grant Screen Recording permission: System Settings > Privacy & Security > Screen Recording
- Window might be on another Space — use default activation
- Increase `--settle-ms` if app is slow to render
- Use `--verify motion` to detect static recordings

### File size too large for platform

- Reduce `--duration`
- Lower `--fps` (10 is usually sufficient)
- Reduce `--max-width`
- Use appropriate `--preset` for target platform

### Sandbox IDEs (JetBrains runIde)

```bash
claude-code-skills screen-recorder --record "Main" --args "idea.plugin.in.sandbox.mode" --no-activate -d 10
```

With `--no-activate`, manually switch to the sandbox window's Space before recording.

### Permission errors

Grant in System Settings > Privacy & Security:

- **Screen Recording**: Required for screencapture
- **Accessibility**: Required for AppleScript window activation

## Dependencies

Required Python packages:

- `pyobjc-framework-Quartz>=10.0` — macOS Quartz framework bindings
- `pyobjc-framework-ScreenCaptureKit>=10.0` — ScreenCaptureKit bindings (macOS 12.3+)
- `pyobjc-framework-AVFoundation>=10.0` — AVFoundation for SCK video recording
- `psutil>=5.9` — Process information
- `pillow>=10.0` — Image processing
- `imagehash>=4.3` — Perceptual hashing (motion detection)

External tools:

- `screencapture` — Built into macOS
- `ffmpeg` / `ffprobe` — Video conversion (`brew install ffmpeg`)

See `references/python-api.md` for programmatic usage and `references/technical-refs.md` for protocol documentation.
