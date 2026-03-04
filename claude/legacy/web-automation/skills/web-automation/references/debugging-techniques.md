# Debugging Techniques

## Contents

- [Progressive Screenshot Capture](#progressive-screenshot-capture)
- [DOM State Logging](#dom-state-logging)
- [Network Request Monitoring](#network-request-monitoring)
- [Selector Validation in Console](#selector-validation-in-console)
- [Timing Analysis](#timing-analysis)
- [Headless vs Headed Debugging](#headless-vs-headed-debugging)
- [Error Context Capture](#error-context-capture)
- [Browser Console Access](#browser-console-access)
- [Trace Viewer (Playwright)](#trace-viewer-playwright)
- [Debugging Checklist](#debugging-checklist)
- [Quick Debug Commands](#quick-debug-commands)
- [Related Documentation](#related-documentation)

Systematic approaches to troubleshooting web automation failures.

## Progressive Screenshot Capture

**Technique:** Capture visual state after each significant action.

```python
def debug_login(page):
    """Login with screenshot debugging."""
    # 1. Initial state
    page.screenshot(path='debug/01-initial.png')

    # 2. After username
    page.fill('#username', 'test@example.com')
    page.screenshot(path='debug/02-username-filled.png')

    # 3. After clicking Next
    page.click('button:has-text("Next")')
    page.screenshot(path='debug/03-after-next.png')

    # 4. Password page
    page.wait_for_selector('#password')
    page.screenshot(path='debug/04-password-page.png')

    # 5. After password
    page.fill('#password', 'password123')
    page.screenshot(path='debug/05-password-filled.png')

    # 6. After submit
    page.click('button[type="submit"]')
    page.screenshot(path='debug/06-after-submit.png')

    # 7. Final state
    page.wait_for_url('**/dashboard')
    page.screenshot(path='debug/07-success.png')
```

**Why useful:** See exactly what page looked like when automation failed.

## DOM State Logging

**Technique:** Log element properties before interaction.

```python
def log_element_state(page, selector, label=''):
    """Log detailed element state."""
    print(f"\n{'='*60}")
    print(f"Element State: {label or selector}")
    print('='*60)

    try:
        locator = page.locator(selector)

        print(f"Exists: {locator.count() > 0}")

        if locator.count() > 0:
            print(f"Count: {locator.count()}")
            print(f"Visible: {locator.first.is_visible()}")
            print(f"Enabled: {locator.first.is_enabled()}")

            # Get attributes
            attrs = page.evaluate(f'''() => {{
                const el = document.querySelector("{selector}");
                if (!el) return null;
                return {{
                    id: el.id,
                    name: el.name,
                    type: el.type,
                    className: el.className,
                    value: el.value,
                    disabled: el.disabled,
                    placeholder: el.placeholder
                }};
            }}''')

            if attrs:
                for key, value in attrs.items():
                    print(f"{key}: {value}")

    except Exception as e:
        print(f"Error logging state: {e}")

# Usage
log_element_state(page, '#username', 'Username Input')
log_element_state(page, 'button[type="submit"]', 'Submit Button')
```

## Network Request Monitoring

**Technique:** Log all network activity to understand AJAX calls.

```python
def monitor_network(page):
    """Monitor network requests."""
    def log_request(request):
        print(f"-> {request.method} {request.url}")

    def log_response(response):
        status = 'OK' if response.ok else 'FAIL'
        print(f"<- {status} {response.status} {response.url}")

    page.on('request', log_request)
    page.on('response', log_response)
```

**Use case:** Understand when form submission happens (AJAX vs page reload).

## Selector Validation in Console

**Technique:** Test selectors in browser console before implementing.

```javascript
// Test selector uniqueness
const selector = 'input[name="email"]';
const elements = document.querySelectorAll(selector);
console.log(`Matches: ${elements.length}`);  // Should be 1

// Test visibility
function isVisible(el) {
  const style = window.getComputedStyle(el);
  return style.display !== 'none'
    && style.visibility !== 'hidden'
    && el.offsetParent !== null;
}

const el = document.querySelector(selector);
console.log(`Visible: ${isVisible(el)}`);

// Test value assignment
el.value = 'test@example.com';
console.log(`Value set: ${el.value}`);
```

## Timing Analysis

**Technique:** Measure delays to optimize waits.

```python
import time

def timed_action(description, action_fn):
    """Execute and time an action."""
    print(f"\n{description}...")
    start = time.time()

    try:
        result = action_fn()
        elapsed = time.time() - start
        print(f"OK {description} ({elapsed:.2f}s)")
        return result
    except Exception as e:
        elapsed = time.time() - start
        print(f"FAIL {description} failed after {elapsed:.2f}s: {e}")
        raise

# Usage
timed_action("Navigate to login", lambda: page.goto('https://example.com/login'))
timed_action("Fill username", lambda: page.fill('#username', 'test'))
timed_action("Click submit", lambda: page.click('button[type="submit"]'))
```

## Headless vs Headed Debugging

**Problem:** Automation works headed but fails headless (or vice versa).

```python
# Debug with visible browser
browser = p.chromium.launch(
    headless=False,  # Show browser
    slow_mo=500,     # Slow down by 500ms per action
    devtools=True    # Open DevTools
)
```

**Common differences:**

- Font rendering (affects element positions)
- Viewport size
- Timezone/locale
- Available fonts

**Solution:** Match headless environment to headed.

```python
browser = p.chromium.launch(
    headless=True,
    args=['--window-size=1920,1080']  # Match headed size
)
```

## Error Context Capture

**Technique:** Capture comprehensive context when errors occur.

```python
def capture_error_context(page):
    """Capture debugging information."""
    context = {
        'url': page.url,
        'title': page.title(),
        'visible_text': page.locator('body').inner_text()[:500],
        'screenshot': f'/tmp/error-{int(time.time())}.png'
    }

    # Save screenshot
    page.screenshot(path=context['screenshot'])

    return context

# Usage in error handler
try:
    page.fill('#username', username)
except Exception as e:
    context = capture_error_context(page)
    print(f"Error: {e}")
    print(f"Context: {context}")
    raise
```

## Browser Console Access

**Technique:** Execute JavaScript to inspect runtime state.

```python
# Check what inputs exist
inputs_info = page.evaluate('''() => {
  return Array.from(document.querySelectorAll('input')).map(i => ({
    id: i.id,
    name: i.name,
    type: i.type,
    visible: i.offsetParent !== null,
    value: i.value
  }));
}''')

print("Inputs on page:", inputs_info)

# Check for iframes
iframe_count = page.evaluate('document.querySelectorAll("iframe").length')
print(f"iframes: {iframe_count}")

# Get all button text
buttons = page.evaluate('''() => {
  return Array.from(document.querySelectorAll('button')).map(b => b.innerText);
}''')

print("Buttons:", buttons)
```

## Trace Viewer (Playwright)

**Technique:** Record complete execution trace for post-mortem analysis.

```python
# Start tracing
context = browser.new_context()
context.tracing.start(screenshots=True, snapshots=True)

page = context.new_page()

try:
    # Your automation here
    page.goto('https://example.com/login')
    page.fill('#username', 'test')
    # ...
except Exception:
    pass
finally:
    # Stop and save trace
    context.tracing.stop(path='trace.zip')

# View trace:
# playwright show-trace trace.zip
```

**Features:**

- Visual timeline of all actions
- Screenshots at each step
- Network activity
- Console logs
- DOM snapshots

## Debugging Checklist

When automation fails:

1. **Take screenshot** - See visual state
2. **Log element state** - Check existence, visibility, enabled
3. **Check selector uniqueness** - `querySelectorAll().length`
4. **Test in console** - Manually verify selector works
5. **Check for iframes** - Element might be in iframe
6. **Verify timing** - Element might load late
7. **Check events** - React/Vue might need event triggers
8. **Monitor network** - See if AJAX calls complete
9. **Compare headed/headless** - Environment differences
10. **Review trace** - Use Playwright trace viewer

## Quick Debug Commands

```python
# Stop and inspect (add to code)
import pdb; pdb.set_trace()

# Or use Playwright's pause
page.pause()  # Opens Playwright Inspector

# Print all locators matching selector
print(f"Count: {page.locator('button').count()}")
for i in range(page.locator('button').count()):
    print(f"Button {i}: {page.locator('button').nth(i).inner_text()}")

# Check if URL changed
print(f"Current URL: {page.url}")

# See page HTML
print(page.content()[:1000])  # First 1000 chars
```

## Related Documentation

- [Common Pitfalls](common-pitfalls.md) - Known issues to avoid
- [Element Selectors](element-selectors.md) - Selector troubleshooting
- [Investigation Workflow](investigation-workflow.md) - Systematic investigation
- [Code Patterns](code-patterns.md) - Working implementation examples
