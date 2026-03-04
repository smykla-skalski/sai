# Common Pitfalls

## Contents

- [Top 10 Pitfalls (Most Common)](#top-10-pitfalls-most-common)
  - [1. Not Waiting for Elements](#1-not-waiting-for-elements)
  - [2. Using Wrong Selector (Multiple Matches)](#2-using-wrong-selector-multiple-matches)
  - [3. Ignoring React/Vue Event Triggering](#3-ignoring-reactvue-event-triggering)
  - [4. Cross-Origin iframe Blocking](#4-cross-origin-iframe-blocking)
  - [5. TOTP Code Expiration](#5-totp-code-expiration)
  - [6. Modal Not Fully Closed](#6-modal-not-fully-closed)
  - [7. Dropdown Not Populated](#7-dropdown-not-populated)
  - [8. Button Disabled by Validation](#8-button-disabled-by-validation)
  - [9. Rate Limiting / Bot Detection](#9-rate-limiting--bot-detection)
  - [10. Assuming Single-Step Flow](#10-assuming-single-step-flow)
- [Technical Deep Dives](#technical-deep-dives)
  - [React/Vue Controlled Components](#reactvue-controlled-components)
  - [TOTP Timing Algorithm](#totp-timing-algorithm)
  - [Shadow DOM Access](#shadow-dom-access)
- [Failed Approaches (What NOT to Do)](#failed-approaches-what-not-to-do)
- [Debugging Checklist](#debugging-checklist)
- [Related Documentation](#related-documentation)

Known issues and their solutions when implementing web automation. Learn from these mistakes to avoid hours of debugging.

## Top 10 Pitfalls (Most Common)

### 1. Not Waiting for Elements

**Problem:** Interacting with elements before they're ready.

```python
# WRONG: Will fail if element doesn't exist yet
page.click('#submit-button')

# CORRECT: Wait for element to be visible
page.wait_for_selector('#submit-button', state='visible')
page.click('#submit-button')

# BEST: Playwright auto-waits
page.click('#submit-button')  # Built-in smart waiting
```

**Root cause:** Network latency, JavaScript execution, DOM manipulation.

**Solution:** Always use smart waits or Playwright's auto-waiting.

### 2. Using Wrong Selector (Multiple Matches)

**Problem:** Selector matches multiple elements, getting wrong one.

```python
# WRONG: Matches all text inputs
page.fill('input[type="text"]', 'test@example.com')  # Which input?

# CORRECT: Be specific
page.fill('input[name="email"]', 'test@example.com')

# BETTER: Use unique ID
page.fill('#email-input', 'test@example.com')
```

**Debug:** Check `document.querySelectorAll('your-selector').length` - should be 1.

### 3. Ignoring React/Vue Event Triggering

**Problem:** Direct value assignment doesn't trigger onChange handlers.

```javascript
// WRONG: React doesn't see this change
document.getElementById('username').value = 'test@example.com'

// CORRECT: Trigger events
const input = document.getElementById('username');
input.value = 'test@example.com';
input.dispatchEvent(new Event('input', { bubbles: true }));
input.dispatchEvent(new Event('change', { bubbles: true }));
```

**Why:** React/Vue use controlled components that rely on events.

**Playwright solution:** `.fill()` automatically triggers events.

### 4. Cross-Origin iframe Blocking

**Problem:** Can't access iframe content from different domain.

```javascript
// FAILS: Cross-origin security blocks this
const iframe = document.querySelector('iframe');
const doc = iframe.contentDocument;  // null or SecurityError
```

**Solution:** Use browser automation tool's iframe context switching:

```python
# Playwright handles cross-origin iframes
iframe = page.frame_locator('iframe#login')
iframe.locator('#username').fill('test@example.com')
```

**Workaround:** Look for non-iframe login alternative on the site.

### 5. TOTP Code Expiration

**Problem:** 30-second TOTP window expires before code is used.

```python
# WRONG: Code retrieved too early
totp = get_totp_code()
# ... 40 seconds of other operations ...
page.fill('#otp', totp)  # Code expired!

# CORRECT: Get code right before use
page.wait_for_selector('#otp')  # Wait for input first
totp = get_totp_code()  # Get fresh code
page.fill('#otp', totp)  # Use immediately
```

**Best practice:** Check if code is expiring soon (>25s in cycle), wait for next.

### 6. Modal Not Fully Closed

**Problem:** Modal still visible or blocking after "closing."

```python
# WRONG: Assumes Escape closes modal
page.keyboard.press('Escape')
page.click('#next-button')  # Clicks modal backdrop!

# CORRECT: Verify modal is gone
page.keyboard.press('Escape')
page.wait_for_selector('.modal', state='hidden')
page.click('#next-button')  # Now safe
```

**Impact:** Clicks go to modal backdrop instead of page elements.

### 7. Dropdown Not Populated

**Problem:** Selecting option before dropdown loads data.

```python
# WRONG: Dropdown may be empty
page.select_option('#country', label='United States')

# CORRECT: Wait for options to load
page.wait_for_selector('#country option[value="US"]')
page.select_option('#country', label='United States')

# BETTER: Verify dropdown has options
options_count = page.locator('#country option').count()
if options_count < 2:  # First option is usually placeholder
    raise RuntimeError('Dropdown not populated')
page.select_option('#country', label='United States')
```

**Common with:** Dependent dropdowns (country -> state -> city).

### 8. Button Disabled by Validation

**Problem:** Form validation keeps submit button disabled.

```python
# WRONG: Button may still be disabled
page.fill('#email', 'test@example.com')
page.click('button[type="submit"]')  # Button disabled!

# CORRECT: Wait for button to be enabled
page.fill('#email', 'test@example.com')
page.wait_for_selector('button[type="submit"]:not([disabled])')
page.click('button[type="submit"]')
```

**Why:** JavaScript validation enables button only after valid input.

### 9. Rate Limiting / Bot Detection

**Problem:** Too-fast automation triggers bot detection.

**Signs:**

- CAPTCHA appears unexpectedly
- Account locked
- Request returns 429 Too Many Requests
- "Suspicious activity" message

**Solutions:**

```python
# Add human-like delays
import random
time.sleep(random.uniform(0.5, 2.0))

# Use realistic user agent
context = browser.new_context(
    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...'
)

# Don't run automation too frequently
# Use session persistence to reduce login frequency
```

### 10. Assuming Single-Step Flow

**Problem:** Modern sites often use multi-step forms.

```python
# WRONG: Assumes single-step login
page.fill('#username', 'test@example.com')
page.fill('#password', 'password123')  # Password field doesn't exist yet!
page.click('button[type="submit"]')

# CORRECT: Handle multi-step
page.fill('#username', 'test@example.com')
page.click('button[type="submit"]')
page.wait_for_selector('#password')  # Wait for next step
page.fill('#password', 'password123')
page.click('button[type="submit"]')
```

**Always:** Investigate flow manually first to map all steps.

## Technical Deep Dives

### React/Vue Controlled Components

**The Problem:**

```javascript
// React component (simplified)
function LoginForm() {
  const [username, setUsername] = useState('');

  return (
    <input
      value={username}
      onChange={(e) => setUsername(e.target.value)}
    />
  );
}
```

When you set `.value` directly, React's internal state stays empty. On next render, React resets the input.

**The Solution:**

```javascript
function setReactInputValue(element, value) {
  // Use native setter to bypass React
  const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype,
    'value'
  ).set;
  nativeInputValueSetter.call(element, value);

  // Trigger React's onChange
  element.dispatchEvent(new Event('input', { bubbles: true }));
}

// Usage
const input = document.getElementById('username');
setReactInputValue(input, 'test@example.com');
```

**Simpler (90% cases):**

```javascript
input.value = 'test@example.com';
input.dispatchEvent(new Event('input', { bubbles: true }));
input.dispatchEvent(new Event('change', { bubbles: true }));
```

### TOTP Timing Algorithm

TOTP codes refresh every 30 seconds. If your automation is slow:

```python
import time

def get_fresh_totp(otp_provider):
    """Get TOTP ensuring it won't expire soon."""
    # Get current position in 30s cycle
    current_second = time.time() % 30

    # If less than 5s remaining, wait for next code
    if current_second > 25:
        wait_time = 30 - current_second + 1
        print(f"Waiting {wait_time:.0f}s for fresh TOTP...")
        time.sleep(wait_time)

    return otp_provider()
```

### Shadow DOM Access

Web Components encapsulate their DOM in Shadow Roots:

```html
<custom-element>
  #shadow-root (closed)
    <button id="internal-btn">Click</button>
</custom-element>
```

**Playwright automatically pierces Shadow DOM:**

```python
# Just use normal selectors, Playwright handles it
page.locator('#internal-btn').click()
```

**Manual JavaScript access:**

```javascript
const host = document.querySelector('custom-element');
const shadowRoot = host.shadowRoot;
const button = shadowRoot.querySelector('#internal-btn');
button.click();
```

## Failed Approaches (What NOT to Do)

### Direct Form Submission Without Events

**Attempted:**

```javascript
document.getElementById('username').value = 'test';
document.getElementById('password').value = 'pass';
document.querySelector('form').submit();
```

**Result:** Failed silently, no navigation.

**Why:** React forms require onChange events to enable submit button.

**Lesson:** Always trigger input events after value assignment.

---

### Fixed Time Delays Instead of Smart Waits

**Attempted:**

```python
page.goto('https://example.com/login')
time.sleep(5)  # Hope page loaded
page.fill('#username', 'test')
```

**Result:** Sometimes worked, sometimes failed (flaky).

**Why:** Page load time varies with network, server load.

**Lesson:** Wait for specific elements, not arbitrary time.

---

### CSS Class-Based Selectors

**Attempted:**

```python
page.click('.btn-primary.submit-button')
```

**Result:** Broke after design update.

**Why:** CSS classes change with styling, not semantic.

**Lesson:** Use `id`, `name`, or `data-*` attributes.

---

### Caching TOTP Codes for Reuse

**Attempted:**

```python
totp = get_otp_code()
# Use for multiple operations
page.fill('#otp-1', totp)
time.sleep(40)
page.fill('#otp-2', totp)  # Expired!
```

**Result:** "Invalid code" error.

**Why:** TOTP expires after 30 seconds.

**Lesson:** Get fresh code right before use.

---

### Generic Element Waiting with Fixed Timeout

**Attempted:**

```python
page.goto('https://example.com')
time.sleep(10)  # Hope everything loaded
```

**Result:** Sometimes too short, sometimes wasteful.

**Why:** Page load time is unpredictable.

**Lesson:** Wait for specific element that indicates page is ready.

## Debugging Checklist

When automation fails, check:

- [ ] Element exists in DOM? (`document.querySelector()`)
- [ ] Element visible? (not `display: none`)
- [ ] Element enabled? (not `disabled` attribute)
- [ ] Correct element selected? (multiple matches?)
- [ ] Inside iframe? (need context switch?)
- [ ] In Shadow DOM? (need to pierce shadow)
- [ ] Waiting long enough? (element loads late?)
- [ ] Events triggered? (React/Vue onChange)
- [ ] Button enabled? (validation passed?)
- [ ] Modal closed? (not blocking clicks?)

## Related Documentation

- [Investigation Workflow](investigation-workflow.md) - Systematic investigation process
- [Element Selectors](element-selectors.md) - Choosing reliable selectors
- [Debugging Techniques](debugging-techniques.md) - Troubleshooting failed automation
- [Code Patterns](code-patterns.md) - Implementation examples that work
