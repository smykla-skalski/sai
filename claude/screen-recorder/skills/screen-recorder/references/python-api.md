# Python API

For programmatic use of the screen recorder.

## Basic Usage

```python
from screen_recorder import (
    record_verified,
    record_simple,
    RecordingConfig,
    PlatformPreset,
    VerificationStrategy,
)

# Simple recording
result = record_simple(
    app_name="GoLand",
    duration=5,
    preset=PlatformPreset.GITHUB,
)
print(f"Saved: {result.final_path}")
print(f"Size: {result.video_info.file_size_mb:.2f} MB")

# Full configuration
config = RecordingConfig(
    app_name="Chrome",
    title_pattern="GitHub",
    duration_seconds=10,
    preset=PlatformPreset.DISCORD,
    output_path="demo.webp",
    max_retries=3,
    verification_strategies=(
        VerificationStrategy.BASIC,
        VerificationStrategy.DURATION,
        VerificationStrategy.MOTION,
    ),
)
result = record_verified(config)

if result.verified:
    print(f"Recording saved: {result.final_path}")
    print(f"Duration: {result.duration_actual:.1f}s")
    print(f"Size: {result.video_info.file_size_mb:.2f} MB")
else:
    print("Recording failed verification:")
    for v in result.verifications:
        print(f"  {v.strategy.value}: {v.message}")
```

## JSON Output Example

```bash
claude-code-skills screen-recorder record "GoLand" -d 5 --preset github --json
```

```json
{
  "raw_path": "recordings/goland_20241214_153045_raw.mov",
  "final_path": "recordings/goland_20241214_153045.gif",
  "attempt": 1,
  "duration_requested": 5.0,
  "duration_actual": 5.1,
  "window_id": 190027,
  "app_name": "GoLand",
  "window_title": "research – models.py",
  "bounds": {"x": 0, "y": 25, "width": 2056, "height": 1290},
  "output_format": "gif",
  "preset": "github",
  "video_info": {
    "path": "recordings/goland_20241214_153045.gif",
    "duration_seconds": 5.1,
    "frame_count": 51,
    "fps": 10.0,
    "width": 600,
    "height": 376,
    "file_size_mb": 2.34
  },
  "verifications": [
    {"strategy": "basic", "passed": true, "message": "Valid video file"},
    {"strategy": "duration", "passed": true, "message": "Duration matches"}
  ],
  "verified": true
}
```
