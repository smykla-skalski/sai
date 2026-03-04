---
name: verified-screenshot
description: Capture macOS window screenshots with automatic verification and retry logic. Use when you need to capture a verified screenshot of a macOS window, document UI state, verify window content matches expectations, or capture screenshots across Spaces with retry logic for automation workflows. Integrates with window-controller for window discovery.
argument-hint: "<command> <app> [--verify <strategy>] [--retries N] [--json]"
allowed-tools: Bash, Read
user-invocable: true
---

# macOS Verified Screenshot

Capture macOS window screenshots with automatic verification and retry logic. This skill ensures you actually captured what you intended by verifying the screenshot content, dimensions, and optionally text via OCR.

## Artifact Output Path

> **CRITICAL**: NEVER use `--output` unless the user EXPLICITLY states the artifact MUST be at a specific location. This should be EXTREMELY rare. Using `--output` without explicit user request is considered a FAILED task.

Screenshots are automatically saved to `claude-code/artifacts/verified-screenshot/` with timestamped filenames (e.g., `251216120000-screenshot_GoLand.png`). The artifact path is always returned in the JSON output - use that path for subsequent operations.

## Quick Start

```bash
# Capture screenshot - path is returned in output
/verified-screenshot capture "GoLand" --json
# Returns: {"path": "/path/to/artifacts/.../251216120000-screenshot_GoLand.png", ...}

# Capture with full verification
/verified-screenshot capture "GoLand" --verify all

# Capture sandbox IDE (JetBrains via Gradle runIde)
# Note: Sandbox IDEs appear as "Main", use --no-activate since AppleScript can't activate them
/verified-screenshot capture "Main" --args "idea.plugin.in.sandbox.mode" --no-activate

# Capture specific window by title
/verified-screenshot capture "Chrome" --title "GitHub"

# Capture with 3 retries
/verified-screenshot capture "Code" -r 3

# Capture without Space switching (uses ScreenCaptureKit on macOS 12.3+)
/verified-screenshot capture "GoLand" --backend screencapturekit

# Find window info without capturing
/verified-screenshot find "GoLand" --json
```

## How It Works

### Capture Pipeline

1. **Window Discovery**: Uses `CGWindowListCopyWindowInfo` to enumerate all windows and filter by app name, title pattern, PID, executable path, or command-line arguments.

2. **Activation** (optional): Activates the target app via AppleScript, which also switches to the window's Space. Configurable settle time allows the window to render.

3. **Screenshot Capture**: Uses `CGWindowListCreateImage` to capture the specific window by ID. Optionally excludes window shadow.

4. **Verification**: Runs configured verification strategies against the captured image:
   - **basic**: File exists, size > 0, valid PNG format
   - **dimensions**: Image dimensions match window bounds (within 10% tolerance)
   - **content**: Image is not blank, differs from previous capture (perceptual hash)
   - **text**: Expected text appears in image (OCR via pytesseract)

5. **Retry Loop**: If verification fails, retries up to N times with configurable delay strategy:
   - **fixed**: Constant delay between retries
   - **exponential**: Doubling delay (500ms, 1s, 2s, ...)
   - **reactivate**: Re-activate window before each retry

### Verification Strategies

| Strategy     | Purpose           | Details                                     |
|:-------------|:------------------|:--------------------------------------------|
| `basic`      | Sanity check      | File exists, >0 bytes, valid image          |
| `dimensions` | Correct window    | Width/height match window bounds ±10%       |
| `content`    | Not blank/stale   | Perceptual hash differs from blank/previous |
| `text`       | Correct content   | OCR finds expected text                     |
| `all`        | Full verification | All above strategies combined               |
| `none`       | Skip verification | Capture only, no verification               |

### Capture Backends

Two capture backends are available:

| Backend            | Availability | Cross-Space | Activation Required |
|:-------------------|:-------------|:------------|:--------------------|
| `quartz`           | All macOS    | No          | Yes                 |
| `screencapturekit` | macOS 12.3+  | Yes         | No                  |
| `auto` (default)   | -            | -           | Auto-selects best   |

**ScreenCaptureKit (macOS 12.3+):**

- Captures windows on ANY Space without switching
- Works with occluded (covered) windows
- No window activation required
- Cannot capture minimized windows
- Requires Screen Recording permission

**Quartz (legacy):**

- Uses `CGWindowListCreateImage` (deprecated in macOS 15)
- Requires window activation to capture other Spaces
- Works on all macOS versions

When using `--backend auto` (default), ScreenCaptureKit is used when available. Use `--backend quartz` to force the legacy backend.

### Perceptual Hashing

Uses [imagehash](https://github.com/JohannesBuchner/imagehash) for content verification:

- Computes `phash` (perceptual hash) of the image
- Compares via Hamming distance (number of differing bits)
- Default threshold: 5 (images with distance < 5 considered "same")
- Detects blank images and unchanged screenshots

## Command Reference

### Actions

| Flag        | Short | Description                   |
|:------------|:------|:------------------------------|
| `--capture` | `-c`  | Capture screenshot of window  |
| `--find`    | `-f`  | Find window without capturing |

### Window Filters

| Flag              | Short | Description                      |
|:------------------|:------|:---------------------------------|
| `--title`         | `-t`  | Regex pattern for window title   |
| `--pid`           |       | Filter by process ID             |
| `--path-contains` |       | Executable path must contain     |
| `--path-excludes` |       | Executable path must NOT contain |
| `--args`          |       | Command line must contain        |

### Output Options

| Flag       | Short | Description                |
|:-----------|:------|:---------------------------|
| `--output` | `-o`  | Output path for screenshot |
| `--json`   | `-j`  | Output as JSON             |

### Capture Options

| Flag            | Short | Description                                     |
|:----------------|:------|:------------------------------------------------|
| `--no-activate` |       | Don't activate window first                     |
| `--settle-ms`   |       | Wait time after activation (default: 1000)      |
| `--shadow`      |       | Include window shadow                           |
| `--backend`     | `-b`  | Capture backend: auto, quartz, screencapturekit |

### Verification Options

| Flag               | Description                                                           |
|:-------------------|:----------------------------------------------------------------------|
| `--verify`         | Verification strategies (basic, dimensions, content, text, all, none) |
| `--expected-text`  | Text to verify via OCR                                                |
| `--hash-threshold` | Hamming distance threshold (default: 5)                               |

### Retry Options

| Flag               | Short | Description                                |
|:-------------------|:------|:-------------------------------------------|
| `--retries`        | `-r`  | Maximum retry attempts (default: 5)        |
| `--retry-delay`    |       | Delay between retries in ms (default: 500) |
| `--retry-strategy` |       | fixed, exponential, or reactivate          |

## JSON Output

```bash
/verified-screenshot capture "GoLand" --verify all --json
```

```json
{
  "path": "screenshots/goland_20241214_153045.png",
  "attempt": 1,
  "window_id": 190027,
  "app_name": "GoLand",
  "window_title": "research – models.py",
  "expected_dimensions": {"width": 2056.0, "height": 1290.0},
  "actual_dimensions": {"width": 2056, "height": 1290},
  "verified": true,
  "image_hash": "a1b2c3d4e5f6",
  "verifications": [
    {"strategy": "basic", "passed": true, "message": "Valid image file", "details": {}},
    {"strategy": "dimensions", "passed": true, "message": "Dimensions match", "details": {}},
    {"strategy": "content", "passed": true, "message": "Image has meaningful content", "details": {}}
  ]
}
```

## Troubleshooting

### "No window found matching filter"

1. Check if the app is running: `ps aux | grep -i appname`
2. Use `--find` to see what windows are available
3. For sandbox IDEs, use `--capture "Main" --args "sandbox"`
4. Try without filters first to verify connectivity

### "Verification failed after N attempts"

1. Increase `--retries` and/or `--settle-ms`
2. Use `--retry-strategy reactivate` to re-focus window
3. Check verification details in JSON output
4. Try `--verify basic` to isolate the failing check

### Screenshot is blank or wrong window

1. Grant Screen Recording permission: System Settings > Privacy & Security > Screen Recording
2. The window might be minimized or on another Space
3. Use `--verify dimensions` to detect wrong-sized captures
4. Increase `--settle-ms` if app is slow to render

### Avoiding Space switching

**Option 1: Use ScreenCaptureKit (recommended for macOS 12.3+)**

```bash
/verified-screenshot capture "App" --backend screencapturekit
```

Captures windows on ANY Space without switching. Works with covered windows too.

**Option 2: Disable activation**

```bash
/verified-screenshot capture "App" --no-activate
```

**Tradeoff**: Uses Quartz backend which cannot capture windows on other Spaces (produces transparent/stale image). Only use if window is on current Space.

### Sandbox IDEs (JetBrains runIde)

JetBrains sandbox IDEs appear as "Main" (Java process name), and AppleScript cannot activate them:

```bash
# Must use --no-activate for sandbox IDEs
/verified-screenshot capture "Main" --args "idea.plugin.in.sandbox.mode" --no-activate
```

If the sandbox window needs to be active, manually switch to its Space before capturing.

### OCR text verification fails

1. Install Tesseract: `brew install tesseract`
2. Install pytesseract: `uv add pytesseract`
3. Ensure expected text is actually visible (not scrolled off)
4. Text must be readable (not too small, good contrast)

### Permission errors

Grant these permissions in System Settings > Privacy & Security:

- **Screen Recording**: Required for window names and screenshots
- **Accessibility**: Required for AppleScript window activation

## Dependencies

Required:

- `pyobjc-framework-Quartz>=10.0` - macOS Quartz framework bindings
- `pyobjc-framework-ScreenCaptureKit>=10.0` - ScreenCaptureKit bindings (macOS 12.3+)
- `psutil>=5.9` - Process information
- `pillow>=10.0` - Image processing
- `imagehash>=4.3` - Perceptual hashing

Optional:

- `pytesseract>=0.3` - OCR text verification (requires Tesseract)

## Technical References

- [ScreenCaptureKit](https://developer.apple.com/documentation/screencapturekit) - Apple's modern capture API (macOS 12.3+)
- [CGWindowListCreateImage](https://developer.apple.com/documentation/coregraphics/1454852-cgwindowlistcreateimage) - Legacy CoreGraphics API (deprecated macOS 15)
- [imagehash](https://github.com/JohannesBuchner/imagehash) - Perceptual hashing library
- [pytesseract](https://github.com/madmaze/pytesseract) - Python Tesseract wrapper
- [PyObjC](https://pyobjc.readthedocs.io/) - Python Objective-C bridge
