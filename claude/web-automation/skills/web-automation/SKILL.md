---
name: web-automation
description: Investigate and implement web browser automation for testing, scraping, and interaction workflows. Use when automating browser interactions, discovering element selectors, choosing automation tools, debugging automation failures, or handling complex flows like 2FA and iframes.
argument-hint: "<url-or-task> [--tool playwright|selenium|puppeteer]"
allowed-tools: Bash, Read, Write, Grep, Glob, WebFetch, WebSearch
user-invocable: true
---

# Web Automation

A guide for investigating and implementing browser automation for any web scenario - form filling, clicking buttons, navigating pages, file uploads, and more.

## Arguments

Parse from `$ARGUMENTS`:

| Flag         | Default    | Purpose                                          |
|:-------------|:-----------|:-------------------------------------------------|
| (positional) | —          | URL to automate or task description              |
| `--tool`     | playwright | Automation tool: playwright, selenium, puppeteer |

## Quick Start: 5-Step Investigation Process

When approaching any web automation task, follow this systematic process:

1. **Manual Reconnaissance** (5-10 min)
   - Open target page in browser
   - Open Developer Tools (Cmd+Option+I / F12)
   - Observe: redirects, multi-step flows, iframes, dynamic content
   - Take screenshots for reference

2. **DOM Structure Analysis** (10-15 min)
   - Inspect HTML in Elements tab
   - Document input fields (ID, name, type, autocomplete attributes)
   - Document buttons (IDs, data attributes, text content)
   - Note any special patterns (React, Vue, Shadow DOM)

3. **Interaction Testing** (10-15 min)
   - Test selectors in browser console
   - Try filling fields manually
   - Observe validation behavior
   - Check for error messages or success indicators

4. **Flow Detection** (5-10 min)
   - Check for multi-step workflows (email -> password)
   - Look for iframes (especially login/payment forms)
   - Identify 2FA/MFA requirements
   - Map out the complete user journey

5. **Tool Selection & Implementation** (30-60 min)
   - Choose appropriate tool based on requirements
   - Implement with proper waits and error handling
   - Add retry logic for flaky interactions
   - Test edge cases

## Investigation Methodology

For detailed step-by-step investigation process, see **[Investigation Workflow](references/investigation-workflow.md)**.

Key phases:

- Phase 1: Manual reconnaissance
- Phase 2: Form structure analysis
- Phase 3: Interaction testing
- Phase 4: iframe detection
- Phase 5: Multi-step flow detection
- Phase 6: 2FA/MFA handling
- Phase 7: Implementation
- Phase 8: Debugging and optimization

## Element Discovery

Finding the right selectors is critical. See **[Element Selectors](references/element-selectors.md)** for comprehensive guidance.

**Selector Priority (from most to least reliable):**

1. **`id` attribute** - Best choice, unique and stable

   ```javascript
   document.getElementById('username')
   ```

2. **`name` attribute** - Good for form fields

   ```javascript
   document.querySelector('input[name="email"]')
   ```

3. **`data-*` attributes** - Framework-specific, usually stable

   ```javascript
   document.querySelector('[data-test="submit-button"]')
   ```

4. **CSS classes** - Risky, can change with styling

   ```javascript
   document.querySelector('.login-button')
   ```

5. **XPath** - Last resort, very brittle

   ```javascript
   document.evaluate('//button[text()="Submit"]', ...)
   ```

**Key principle:** Use the most specific and stable selector available.

## Tool Selection

The right tool depends on your requirements. See **[Tool Comparison](references/tool-comparison.md)** for detailed analysis.

**Quick Decision Tree:**

```
Need iframe support + cross-browser testing?
  -> Playwright (recommended)

Chrome-only + Node.js project?
  -> Puppeteer (fastest)

Legacy system or need WebDriver protocol?
  -> Selenium (most mature)

AI-driven exploration with Claude Code?
  -> MCP browser-controller (easiest)

Just need to submit form data without JavaScript?
  -> Direct HTTP requests (no browser needed)
```

**Playwright** is recommended for most modern web automation tasks due to:

- Built-in smart waiting
- Excellent iframe support
- Cross-browser testing
- Modern API design
- Active development

## Common Scenarios

### Two-Step Login Flow

```
Step 1: Enter email -> Click "Next"
Wait for password page
Step 2: Enter password -> Click "Log In"
Wait for 2FA or success page
Step 3: If 2FA, enter code -> Click "Verify"
```

### Dropdown Selection

```
1. Wait for dropdown to be visible
2. Verify dropdown is populated (has options)
3. Select option by label or value
4. Verify selection succeeded
5. Wait for dependent dropdowns to reload
```

### Modal Dialog Handling

```
1. Wait for modal to appear (visibility check)
2. Wait for modal content to load completely
3. Interact with modal elements
4. Close modal
5. VERIFY modal actually closed before continuing
```

### iframe Forms

```
1. Detect if form is inside iframe
2. Check if iframe is same-origin (accessible)
3. Switch context to iframe
4. Perform interactions
5. Switch back to main page context
```

For more scenarios, see **[Investigation Workflow](references/investigation-workflow.md)**.

## Debugging

When automation fails, systematic debugging saves time. See **[Debugging Techniques](references/debugging-techniques.md)** and **[Practical Debugging Workflow](references/practical-debugging-workflow.md)**.

**Essential debugging techniques:**

1. **Progressive Screenshots** - Capture after each action
2. **DOM State Logging** - Log element properties before interaction
3. **Selector Validation** - Test in browser console first
4. **Timing Analysis** - Measure delays between actions
5. **Network Monitoring** - Check for AJAX/API calls
6. **Headless vs Headed** - Run with visible browser to see what's happening

**Common debugging commands:**

```javascript
// Check if element exists
document.getElementById('username') !== null

// Check if element is visible
window.getComputedStyle(document.getElementById('username')).display !== 'none'

// Get all form inputs
Array.from(document.querySelectorAll('input')).map(i => ({
  id: i.id, name: i.name, type: i.type
}))

// Check for iframes
document.querySelectorAll('iframe').length
```

## Common Pitfalls

Avoid these common mistakes. See **[Common Pitfalls](references/common-pitfalls.md)** for detailed solutions.

**Top 10 pitfalls:**

1. **Not waiting for elements** - Always wait for visibility, not just existence
2. **Using wrong selector** - Multiple elements match, getting wrong one
3. **Ignoring React/Vue events** - Direct value assignment doesn't trigger onChange
4. **Cross-origin iframes** - Can't access iframe content from different domain
5. **TOTP code expiration** - 30-second window, get code right before use
6. **Modal not fully closed** - Next interaction clicks on modal backdrop
7. **Dropdown not populated** - Selecting before options loaded
8. **Button disabled by validation** - Filling fields doesn't enable submit
9. **Rate limiting / bot detection** - Too fast automation gets blocked
10. **Assuming single-step flow** - Modern sites often use multi-step forms

## Code Patterns

Reusable code templates for common operations. See **[Code Patterns](references/code-patterns.md)**.

**Retry decorator:**

```python
def retry(max_attempts=3, delay=2.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
                    else:
                        raise
        return wrapper
    return decorator
```

**Wait for element:**

```python
def wait_for_element(page, selector, timeout=10):
    """Wait for element to be visible and stable."""
    page.wait_for_selector(selector, state="visible", timeout=timeout * 1000)
    page.wait_for_selector(selector, state="stable", timeout=2000)
```

**Validated dropdown selection:**

```python
def select_dropdown_option(dropdown, label):
    """Select option and verify selection succeeded."""
    dropdown.select_option(label=label)
    selected = dropdown.input_value()
    if selected != label:
        raise RuntimeError(f"Failed to select {label}, got {selected}")
```

## Reference Documentation

- **[Practical Debugging Workflow](references/practical-debugging-workflow.md)** - START HERE - Real-world investigation feedback loop, browser-controller integration, efficient debugging
- **[Investigation Workflow](references/investigation-workflow.md)** - Detailed 8-phase process
- **[Element Selectors](references/element-selectors.md)** - Selector strategies and patterns
- **[Tool Comparison](references/tool-comparison.md)** - Playwright vs Selenium vs Puppeteer vs MCP
- **[Common Pitfalls](references/common-pitfalls.md)** - Known issues and solutions
- **[Debugging Techniques](references/debugging-techniques.md)** - Troubleshooting failed automation
- **[Code Patterns](references/code-patterns.md)** - Reusable implementation templates
