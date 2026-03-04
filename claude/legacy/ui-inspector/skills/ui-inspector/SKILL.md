---
name: ui-inspector
description: Inspect live macOS UI elements via Accessibility API (atomacos). Find buttons, text fields, and other elements in running applications. Returns element metadata (role, title, position, enabled state) and click coordinates. Use when you need to find UI elements in a running app, get click coordinates for automation, check if buttons are enabled, or inspect the accessibility tree of macOS applications. Requires Accessibility permissions.
argument-hint: "<command> --app <app> [--role <role>] [--title <title>] [--json]"
allowed-tools: Bash, Read
user-invocable: true
---

# macOS UI Inspector

Inspect live UI elements in running macOS applications using the Accessibility API. Find elements by role, title, or identifier and get their click coordinates for automation.

## Quick Start

```bash
# List all UI elements in an application
/ui-inspector list --app "Finder"

# Find buttons only
/ui-inspector list -a "Finder" --role AXButton

# Find element by title
/ui-inspector find -a "Safari" --title "Downloads"

# Get click coordinates
/ui-inspector click -a "Safari" --title "Submit"

# Press element (no mouse movement - works for native dialogs)
/ui-inspector press -a "Google Chrome" --title "Not now"

# JSON output for automation
/ui-inspector list -a "Finder" --json
```

## Commands

### List Elements (`--list`)

List all UI elements in the frontmost window of an application.

```bash
# All elements
/ui-inspector -a "Finder" -l

# Filter by role
/ui-inspector -a "Safari" -l --role AXButton
/ui-inspector -a "Safari" -l --role AXTextField
/ui-inspector -a "Safari" -l --role AXStaticText

# JSON output
/ui-inspector -a "Finder" -l --json
```

Example output:

```
Role                      Title                     Center (x,y)    Enabled
--------------------------------------------------------------------------------
AXToolbar                 (none)                    (1028,   67)    Yes
AXButton                  Close                     (  14,   47)    Yes
AXButton                  Minimize                  (  34,   47)    Yes
AXButton                  Zoom                      (  54,   47)    Yes
AXGroup                   (none)                    ( 512,   67)    Yes
```

### Find Element (`--find`)

Find a specific element by role, title, or identifier.

```bash
# By title
/ui-inspector -a "Safari" --find --title "Downloads"

# By role
/ui-inspector -a "Safari" --find --role AXButton

# By role and title
/ui-inspector -a "Safari" --find --role AXButton --title "Back"

# By identifier
/ui-inspector -a "Safari" --find --identifier "backButton"
```

Example output:

```
Role:       AXButton
Title:      Downloads
Value:      (none)
Identifier: downloadsButton
Position:   (450, 60)
Size:       80 x 24
Center:     (490, 72)
Enabled:    Yes
Focused:    No
```

### Get Click Coordinates (`--click`)

Get the center coordinates of an element for clicking.

```bash
# By title
/ui-inspector -a "Safari" --click --title "Submit"
# Output: 490,72

# By role
/ui-inspector -a "Finder" --click --role AXButton
# Output: 14,47 (first button found)

# JSON output
/ui-inspector -a "Safari" --click --title "OK" --json
# Output: {"x": 490, "y": 72}
```

## Options

| Option         | Short | Description                              |
|:---------------|:------|:-----------------------------------------|
| `--app`        | `-a`  | Application name or bundle ID (required) |
| `--list`       | `-l`  | List all UI elements                     |
| `--find`       |       | Find specific element                    |
| `--click`      |       | Get click coordinates                    |
| `--role`       |       | Filter by element role (e.g., AXButton)  |
| `--title`      |       | Filter by element title                  |
| `--identifier` |       | Filter by element identifier             |
| `--json`       |       | Output as JSON                           |

## Application Identification

You can specify applications by name or bundle ID:

```bash
# By name (localized)
/ui-inspector -a "Safari" -l
/ui-inspector -a "Finder" -l

# By bundle ID
/ui-inspector -a "com.apple.finder" -l
/ui-inspector -a "com.apple.Safari" -l
```

## Common Element Roles

| Role            | Description          |
|:----------------|:---------------------|
| `AXButton`      | Clickable button     |
| `AXTextField`   | Text input field     |
| `AXStaticText`  | Label text           |
| `AXToolbar`     | Toolbar container    |
| `AXGroup`       | Group of elements    |
| `AXSplitGroup`  | Split view container |
| `AXScrollArea`  | Scrollable area      |
| `AXCheckBox`    | Checkbox             |
| `AXRadioButton` | Radio button         |
| `AXPopUpButton` | Dropdown menu        |
| `AXMenuItem`    | Menu item            |

## JSON Output

### List Output

```json
[
  {
    "role": "AXButton",
    "title": "Close",
    "value": null,
    "identifier": null,
    "position_x": 14,
    "position_y": 47,
    "width": 14,
    "height": 16,
    "center_x": 21,
    "center_y": 55,
    "enabled": true,
    "focused": false,
    "bounds": {
      "x": 14,
      "y": 47,
      "width": 14,
      "height": 16
    }
  }
]
```

### Click Output

```json
{"x": 21, "y": 55}
```

## Use Cases

### UI Automation

```bash
# Find and click a button
coords=$(/ui-inspector -a "Safari" --click --title "Submit")
# Use coords with cliclick or similar tool
```

### Verifying UI State

```bash
# Check if a button is enabled
/ui-inspector -a "App" --find --title "Save" --json | jq '.enabled'
```

### Cross-Skill Workflow

Combine with `verified-screenshot` for comprehensive UI detection:

```bash
# UI Inspector for known elements (fast, precise)
/ui-inspector -a "Safari" --click --role AXButton --title "Download"

# Capture screenshot for visual verification
/verified-screenshot capture "Safari" --json
```

## Permissions Required

### Accessibility Permission

**Required** for all functionality.

1. Open **System Settings** → **Privacy & Security** → **Accessibility**
2. Add your terminal application (Terminal, iTerm2, VS Code, etc.)
3. Restart the terminal after granting permission

Without this permission, you'll see:

```
Error: Application not found: Finder
```

## How It Works

1. **Application Lookup**: Finds app by name (localized) or bundle ID via atomacos
2. **Window Access**: Gets the frontmost window of the application
3. **Element Enumeration**: Traverses the accessibility tree to find elements
4. **Filtering**: Applies role/title/identifier filters
5. **Coordinate Calculation**: Returns element center for click targeting

### Screen Coordinates

Coordinates are **screen-absolute**, meaning they work directly with mouse automation tools without offset calculation.

## Troubleshooting

### "Application not found"

1. Ensure the app is running
2. Check the exact app name: `ps aux | grep -i safari`
3. Try bundle ID: `/ui-inspector -a "com.apple.Safari" -l`
4. Grant Accessibility permission to your terminal

### "No windows found"

1. Ensure the app has at least one window open
2. Bring the window to front before querying
3. Check if the app has permission issues (some system apps restrict access)

### "No elements found"

1. Some apps have limited accessibility support
2. Try different roles: `--role AXButton`, `--role AXGroup`
3. Use `--list` without filters to see what's available

### Permission Denied

1. Open System Settings → Privacy & Security → Accessibility
2. Add your terminal (may need to remove and re-add)
3. **Restart your terminal** after granting permission
4. Some enterprise MDM policies may block accessibility access

## Comparison with OCR-based tools

| Feature      | ui-inspector           | OCR-based             |
|:-------------|:-----------------------|:----------------------|
| Works on     | Live apps              | Any image             |
| Permissions  | Accessibility          | None                  |
| Speed        | Instant                | ~1-5 seconds          |
| Coordinates  | Screen-absolute        | Image-relative        |
| Element type | Any UI element         | Text only             |
| Metadata     | Role, enabled, focused | Confidence, bbox      |
| Best for     | Automation, buttons    | Screenshots, graphics |

## Technical References

- [atomacos Documentation](https://github.com/daveenguyen/atomacos)
- [Apple Accessibility API](https://developer.apple.com/documentation/accessibility)
- [macOS Accessibility Programming Guide](https://developer.apple.com/library/archive/documentation/Accessibility/Conceptual/AccessibilityMacOSX/)
