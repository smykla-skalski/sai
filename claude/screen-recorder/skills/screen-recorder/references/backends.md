# Capture Backends

The recorder supports multiple capture backends with different capabilities.

## Backend Comparison

| Feature         | Backend            | Cross-Space         | Notes                             |
|:----------------|:-------------------|:--------------------|:----------------------------------|
| Video recording | ScreenCaptureKit   | Yes                 | macOS 12.3+, no activation needed |
| Video recording | `screencapture -v` | Requires activation | Built-in macOS tool, fallback     |
| Region preview  | `screencapture`    | Requires activation | Built-in macOS tool               |

## Backend Selection (`--backend`)

- `auto` (default): Uses ScreenCaptureKit for window recording on macOS 12.3+, falls back to `screencapture` for full-screen or when unavailable
- `screencapturekit`: Force ScreenCaptureKit (requires macOS 12.3+)
- `quartz`: Force traditional `screencapture` command

## ScreenCaptureKit Video (default for window recording)

- Uses SCStream + AVAssetWriter for video recording
- Records windows across Spaces without activation or Space switching
- Works with occluded/covered windows (captures window content directly)
- Requires macOS 12.3+ and Screen Recording permission
- Note: macOS 15 may have stability issues (PyObjC #647)

## Traditional screencapture (default for full-screen)

- Uses macOS built-in `screencapture -v` command
- Requires window activation to record windows on other Spaces
- Space-aware recording automatically switches Spaces when needed
- Always used for full-screen recording (`--full-screen`)

## Region Preview (`--preview-region`)

- Uses macOS built-in `screencapture` command for screenshot preview
- Requires window activation to capture windows on other Spaces
- Space-aware preview automatically switches Spaces when needed
