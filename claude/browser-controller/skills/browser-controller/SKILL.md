---
name: browser-controller
description: Programmatic control of Chrome and Firefox browsers via CDP and Marionette. Use when automating browser interactions, managing tabs, navigating pages, filling forms, clicking elements, executing JavaScript, or taking browser screenshots. Connects to already-running browser instances with remote debugging enabled.
argument-hint: "[command] [args]"
allowed-tools: Bash, Read
user-invocable: true
---

# Browser Controller

Control Chrome and Firefox browsers via CDP (Chrome DevTools Protocol) and Marionette. Connect to already-running browser instances with remote debugging enabled.

## Prerequisites

Start your browser with remote debugging enabled.

**CRITICAL: Chrome REQUIRES `--user-data-dir`**

```bash
open -a "Google Chrome" --args --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-debug"
```

This is **mandatory** because:

1. Chrome may fail to accept `--remote-debugging-port` without a separate profile
2. It prevents interference with your normal Chrome session
3. It ensures a clean, predictable automation environment

**IMPORTANT (macOS):** Use `open -a` instead of direct binary paths. This ensures screen recording permissions are attributed to Chrome/Firefox rather than your terminal app, avoiding the persistent "Currently Sharing" indicator.

**Firefox:**

```bash
open -a Firefox --args --marionette
```

## Basic Commands

```bash
# Check for running browsers
claude-code-skills browser-controller check

# List all open tabs
claude-code-skills browser-controller tabs

# Navigate to URL
claude-code-skills browser-controller navigate "https://example.com"

# Click an element
claude-code-skills browser-controller click "#submit-btn"

# Fill a form field
claude-code-skills browser-controller fill "#email" "test@example.com"

# Read page content
claude-code-skills browser-controller read

# Execute JavaScript
claude-code-skills browser-controller run "document.title"

# Take screenshot (saves to claude-code/artifacts/ by default)
claude-code-skills browser-controller screenshot
```

## Command Reference

### check

Check for browsers running with remote debugging:

```bash
browser-controller check
browser-controller check --json
```

### tabs

List all open tabs:

```bash
browser-controller tabs
browser-controller tabs --browser chrome
browser-controller tabs --json
```

### navigate

Navigate to a URL:

```bash
browser-controller navigate "https://example.com"
browser-controller navigate "example.com"  # https:// added automatically
browser-controller navigate "https://example.com" --tab TAB_ID
```

### click

Click an element by CSS selector:

```bash
browser-controller click "#submit-btn"
browser-controller click ".my-class button"
browser-controller click "[data-testid='login']"
```

### fill

Fill a form field:

```bash
browser-controller fill "#email" "test@example.com"
browser-controller fill "input[name='password']" "secret123"
```

### read

Read page content:

```bash
browser-controller read                  # Show URL, title, and text
browser-controller read --text-only      # Text content only
browser-controller read --json           # Full content as JSON
```

### element

Get information about an element:

```bash
browser-controller element "#submit"
browser-controller element "input[name='email']" --json
```

### run

Execute JavaScript:

```bash
browser-controller run "document.title"
browser-controller run "document.querySelectorAll('a').length"
browser-controller run "window.scrollTo(0, document.body.scrollHeight)"
```

### screenshot

> **CRITICAL**: NEVER use `--output` unless the user EXPLICITLY states the artifact MUST be at a specific location.

Take a screenshot (saves to `claude-code/artifacts/browser-controller/` by default):

```bash
browser-controller screenshot --json
browser-controller screenshot --full-page  # Chrome only, full page capture
```

### activate

Activate (bring to front) a tab:

```bash
browser-controller activate TAB_ID
```

### close

Close a tab:

```bash
browser-controller close TAB_ID
```

### start

Start Chrome with remote debugging (always uses `--user-data-dir`):

```bash
claude-code-skills browser-controller start
claude-code-skills browser-controller start --port 9223
claude-code-skills browser-controller start --dismiss-popups
```

### cleanup

Kill orphaned browser processes with remote debugging:

```bash
claude-code-skills browser-controller cleanup              # With confirmation
claude-code-skills browser-controller cleanup --dry-run    # Show without killing
claude-code-skills browser-controller cleanup --force      # No confirmation
```

## Common Options

| Option            | Description                                            |
|:------------------|:-------------------------------------------------------|
| `--browser`, `-b` | Browser type: `chrome`, `firefox`, or `auto` (default) |
| `--chrome-port`   | Chrome CDP port (default: 9222)                        |
| `--firefox-port`  | Firefox Marionette port (default: 2828)                |
| `--tab`, `-t`     | Target tab ID (uses first tab if not specified)        |
| `--json`, `-j`    | Output as JSON                                         |

## Selector Types

CSS selectors are supported by default:

```bash
browser-controller click "#id"
browser-controller click ".class"
browser-controller click "button[type='submit']"
browser-controller click "div.container > form input"
```

Shorthand prefixes:

```bash
browser-controller click "id:element-id"     # Same as #element-id
browser-controller click "class:my-class"    # Same as .my-class
browser-controller click "css:.explicit"     # Explicit CSS
```

## Resource Cleanup

**IMPORTANT:** Always clean up browser resources after use unless the user explicitly requests otherwise.

Use the `cleanup` command to find and kill orphaned browser processes. The cleanup command finds processes matching Chrome with `--remote-debugging-port`, Chrome with debug user-data-dir patterns, and Firefox with `--marionette`.

### Screen Sharing Indicator (macOS)

If you see "Currently Sharing" in the macOS menu bar after using this skill:

- **Why:** Launching Chrome/Firefox directly via binary path attributes screen recording permissions to the terminal app rather than the browser. The indicator persists after the browser quits.
- **Fix:** Always use `open -a` to launch browsers (see Prerequisites).
- **If stuck:** Restart your terminal app, or toggle Screen Recording permission off/on in System Settings, then run `cleanup --force`.

## Troubleshooting

### "No browser found"

Verify browser is running with remote debugging:

```bash
curl http://localhost:9222/json/version   # Chrome
nc -z localhost 2828                       # Firefox
```

Start browser with correct flags if not running (see Prerequisites).

### "Connection refused"

Check what's using the port:

```bash
lsof -i :9222
lsof -i :2828
```

### "Element not found"

- Verify selector in browser DevTools console: `document.querySelector("#my-element")`
- Page may not be fully loaded — wait and retry
- Element may be in an iframe (not supported)

## Limitations

- **Iframes**: Cross-origin iframes not directly accessible
- **File dialogs**: Native OS dialogs cannot be controlled
- **Browser extensions**: May interfere with automation
- **Firefox multi-tab**: Marionette operates on one window at a time
- **Authentication**: Basic auth popups not supported
