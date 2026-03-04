# Investigation Workflow

## Contents

- [Overview](#overview)
- [Phase 1: Manual Reconnaissance (5-10 minutes)](#phase-1-manual-reconnaissance-5-10-minutes)
  - [Objective](#objective)
  - [Steps](#steps)
  - [Example: JetBrains Marketplace](#example-jetbrains-marketplace)
- [Phase 2: Form Structure Analysis (10-15 minutes)](#phase-2-form-structure-analysis-10-15-minutes)
  - [Objective](#objective-1)
  - [Steps](#steps-1)
  - [Example: JetBrains Two-Step Login](#example-jetbrains-two-step-login)
- [Phase 3: Interaction Testing (10-15 minutes)](#phase-3-interaction-testing-10-15-minutes)
  - [Objective](#objective-2)
  - [Steps](#steps-2)
  - [Common Issues to Test For](#common-issues-to-test-for)
- [Phase 4: iframe Detection and Handling (5-10 minutes)](#phase-4-iframe-detection-and-handling-5-10-minutes)
  - [Objective](#objective-3)
  - [Steps](#steps-3)
  - [iframe Handling in Automation Tools](#iframe-handling-in-automation-tools)
- [Phase 5: Multi-Step Flow Detection (5-10 minutes)](#phase-5-multi-step-flow-detection-5-10-minutes)
  - [Objective](#objective-4)
  - [Steps](#steps-4)
  - [Example: Multi-Step Flows](#example-multi-step-flows)
- [Phase 6: 2FA/MFA Detection (5 minutes)](#phase-6-2famfa-detection-5-minutes)
  - [Objective](#objective-5)
  - [Steps](#steps-5)
  - [2FA Implementation Patterns](#2fa-implementation-patterns)
- [Phase 7: Implementation (30-60 minutes)](#phase-7-implementation-30-60-minutes)
  - [Objective](#objective-6)
  - [Steps](#steps-6)
- [Phase 8: Debugging and Optimization (15-30 minutes)](#phase-8-debugging-and-optimization-15-30-minutes)
  - [Objective](#objective-7)
  - [Debugging Techniques](#debugging-techniques)
  - [Optimization Tips](#optimization-tips)
- [Summary Checklist](#summary-checklist)
- [Time Estimates by Complexity](#time-estimates-by-complexity)
- [Next Steps](#next-steps)
- [Related Documentation](#related-documentation)

Comprehensive 8-phase process for investigating and implementing any web automation scenario.

## Overview

**Total Time:** 1.5-3 hours for typical automation
**Skill Level:** Intermediate (basic HTML/JavaScript knowledge required)
**Tools Needed:** Browser with Developer Tools, text editor, automation tool (Playwright/Selenium/Puppeteer)

## Phase 1: Manual Reconnaissance (5-10 minutes)

### Objective

Understand the login/interaction flow structure through manual observation.

### Steps

1. **Open target URL in browser**
   - Use your actual production browser (not incognito yet)
   - Observe any automatic redirects
   - Note the final URL

2. **Open Developer Tools**
   - Chrome/Edge: `Cmd+Option+I` (Mac) or `F12` (Windows/Linux)
   - Firefox: `Cmd+Option+I` (Mac) or `F12` (Windows/Linux)
   - Safari: Enable Develop menu first, then `Cmd+Option+I`

3. **Observe Page Behavior**
   - Does the page redirect to a different domain?
   - How many steps are in the flow? (single form vs multi-step)
   - Are there any iframes? (Check Elements tab for `<iframe>` tags)
   - Is there a CAPTCHA or bot detection?
   - Are there cookie consent banners or modals?

4. **Document Findings**

   ```
   Initial URL: ___________________
   Final URL: _____________________
   Redirects: Yes / No
   Number of steps: _______________
   iframes present: Yes / No
   CAPTCHA: Yes / No
   Cookie consent: Yes / No
   ```

5. **Take Screenshots**
   - Initial page state
   - Each step of the flow
   - Any modals or overlays
   - Success/error pages

### Example: JetBrains Marketplace

```
Initial URL: https://plugins.jetbrains.com/author/me/subscriptions
Redirects: Yes -> https://account.jetbrains.com/login
Flow steps: 3 (email -> password -> 2FA)
iframes: Yes (login modal contains iframe for OAuth providers)
CAPTCHA: No
Cookie consent: Yes (dismissable)
```

## Phase 2: Form Structure Analysis (10-15 minutes)

### Objective

Identify all input fields, buttons, and interaction points with their unique identifiers.

### Steps

1. **Open Elements Tab in DevTools**
   - Navigate to Elements/Inspector tab
   - Use element picker (cursor icon) to click on form elements

2. **Document Each Input Field**

   For each input field, note:

   ```html
   Field: _______________ (e.g., "Username", "Password", "Email")
   Tag: _______________ (input, select, textarea)
   Type: _______________ (text, password, email, etc.)
   ID: _______________ (id attribute - most important!)
   Name: _______________ (name attribute - second choice)
   Autocomplete: _______________ (username, current-password, etc.)
   Placeholder: _______________ (placeholder text)
   ARIA label: _______________ (aria-label attribute)
   Data attributes: _______________ (data-test, data-id, etc.)
   CSS classes: _______________ (last resort - unstable)
   ```

3. **Document Submit Buttons**

   ```html
   Button: _______________ (e.g., "Submit", "Log In", "Next")
   Tag: _______________ (button, input type="submit")
   Type: _______________ (submit, button)
   ID: _______________
   Data attributes: _______________ (data-test, data-action, etc.)
   Text content: _______________ (visible button text)
   ```

4. **Check for Form Element**
   - Look for `<form>` tag wrapping inputs
   - Note `action` attribute (submission URL)
   - Note `method` attribute (GET or POST)

5. **Identify Unique Selectors**

   **Priority order for reliability:**

   - **id** attribute (best - unique by spec)
   - **name** attribute (good - semantic meaning)
   - **data-*** attributes (good - framework-specific)
   - **aria-label** or **aria-labelledby** (good - accessibility)
   - CSS classes (risky - can change with design)
   - XPath (last resort - very brittle)

### Example: JetBrains Two-Step Login

**Step 1: Email Input**

```html
<input
  type="text"
  id="username"
  name="username"
  autocomplete="username"
  placeholder="Email or username"
  class="wt-input__input"
/>
```

**Best selector:** `#username` or `input[name="username"]`

**Step 1: Submit Button**

```html
<button
  type="submit"
  class="wt-button wt-button_mode_primary"
  data-test="submit-button"
>
  Next
</button>
```

**Best selector:** `button[data-test="submit-button"]`

**Step 2: Password Input (appears AFTER email submission)**

```html
<input
  type="password"
  id="password"
  name="password"
  autocomplete="current-password"
  class="wt-input__input"
/>
```

**Best selector:** `#password` or `input[name="password"]`

**Critical Discovery:** Same submit button, different context!

## Phase 3: Interaction Testing (10-15 minutes)

### Objective

Verify element targeting and interaction reliability in browser console.

### Steps

1. **Open Browser Console**
   - In DevTools, go to Console tab
   - This allows testing JavaScript interactively

2. **Test Element Existence**

   ```javascript
   // Test by ID
   document.getElementById('username')  // Should return element

   // Test by selector
   document.querySelector('#username')  // Should return element

   // Test by name
   document.querySelector('input[name="username"]')  // Should return element

   // Should return null if not found
   document.getElementById('nonexistent')  // null
   ```

3. **Test Element Visibility**

   ```javascript
   function isVisible(el) {
     if (!el) return false;
     const style = window.getComputedStyle(el);
     return style.display !== 'none'
       && style.visibility !== 'hidden'
       && el.offsetParent !== null;
   }

   isVisible(document.getElementById('username'))  // Should return true
   ```

4. **Test Value Assignment**

   ```javascript
   // Try setting value
   document.getElementById('username').value = 'test@example.com'

   // Verify value was set
   document.getElementById('username').value  // Should return 'test@example.com'
   ```

5. **Test Event Triggering (Critical for React/Vue)**

   ```javascript
   const input = document.getElementById('username');
   input.value = 'test@example.com';

   // Trigger events that frameworks listen to
   input.dispatchEvent(new Event('input', { bubbles: true }));
   input.dispatchEvent(new Event('change', { bubbles: true }));
   input.dispatchEvent(new Event('blur', { bubbles: true }));
   ```

6. **Test Button Click**

   ```javascript
   // Method 1: Direct click
   document.querySelector('[data-test="submit-button"]').click()

   // Method 2: With event
   const button = document.querySelector('[data-test="submit-button"]');
   button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
   ```

7. **Manually Fill and Submit**
   - Actually type in the form manually
   - Observe what happens:
     - Does button become enabled after typing?
     - Are there validation messages?
     - Does page reload or use AJAX?
     - What URL does it navigate to?

### Common Issues to Test For

**Issue: Button Disabled Until Validation**

```javascript
const button = document.querySelector('button[type="submit"]');
console.log('Button disabled:', button.disabled);
console.log('Button has disabled attr:', button.hasAttribute('disabled'));

// Check if button becomes enabled after filling
// Fill field, then recheck
```

**Issue: Multiple Elements Match**

```javascript
// Check how many elements match
document.querySelectorAll('input[type="text"]').length

// If > 1, need more specific selector
document.querySelectorAll('input[name="username"]').length  // Should be 1
```

## Phase 4: iframe Detection and Handling (5-10 minutes)

### Objective

Identify if critical elements are inside iframes and determine accessibility.

### Steps

1. **Check for iframes**

   ```javascript
   // Count iframes on page
   document.querySelectorAll('iframe').length

   // List all iframes with details
   Array.from(document.querySelectorAll('iframe')).map(f => ({
     src: f.src,
     id: f.id,
     name: f.name,
     title: f.title
   }))
   ```

2. **Test Cross-Origin Access**

   ```javascript
   function canAccessIframe(iframe) {
     try {
       const doc = iframe.contentDocument || iframe.contentWindow.document;
       return doc !== null;
     } catch (e) {
       console.log('Cross-origin blocked:', e.message);
       return false;
     }
   }

   const iframe = document.querySelector('iframe');
   console.log('Can access:', canAccessIframe(iframe));
   ```

3. **If Same-Origin (Accessible)**

   ```javascript
   // Access iframe content
   const iframe = document.querySelector('iframe#login-frame');
   const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

   // Query within iframe
   const input = iframeDoc.getElementById('username');
   console.log('Found input in iframe:', input);
   ```

4. **If Cross-Origin (Blocked)**
   - **Cannot access iframe content with JavaScript**
   - Options:
     - Check if site offers non-iframe alternative
     - Use Playwright/Puppeteer iframe context switching
     - Use browser automation that handles iframe contexts

### iframe Handling in Automation Tools

**Playwright (Recommended):**

```python
# Switch to iframe context
iframe = page.frame_locator('iframe#login-frame')
iframe.locator('#username').fill('test@example.com')
```

**Selenium:**

```python
# Switch to iframe
driver.switch_to.frame('login-frame')
driver.find_element(By.ID, 'username').send_keys('test@example.com')
driver.switch_to.default_content()  # Switch back
```

**MCP browser-controller:**

- **Limitation:** No iframe context switching support currently
- Must use direct-access iframes or find non-iframe alternative

## Phase 5: Multi-Step Flow Detection (5-10 minutes)

### Objective

Identify if the flow has multiple steps and map the complete user journey.

### Steps

1. **Test for Two-Step Login**

   ```javascript
   // Before submitting email
   console.log('Password field exists:', document.getElementById('password') !== null);

   // Fill email and click Next (manually)

   // After transition
   console.log('Password field exists now:', document.getElementById('password') !== null);
   // Should change from false to true if two-step
   ```

2. **Document All Steps**

   ```
   Step 1: ___________________
   -> Action: ___________________
   -> Wait for: ___________________

   Step 2: ___________________
   -> Action: ___________________
   -> Wait for: ___________________

   Step 3: ___________________
   -> Action: ___________________
   -> Success indicator: ___________________
   ```

3. **Check URL Changes**
   - Note if URL changes between steps
   - Some flows keep same URL but change content
   - Use `console.log(window.location.href)` before and after

4. **Identify Wait Points**
   - After each action, what indicates readiness for next step?
   - New element appears?
   - URL changes?
   - Loading spinner disappears?
   - Specific text becomes visible?

### Example: Multi-Step Flows

**Two-Step Login (JetBrains):**

```
Step 1: Enter email
  -> Click "Next" button
  -> Wait for password field to appear (URL stays same)

Step 2: Enter password
  -> Click "Log In" button
  -> Wait for 2FA page OR redirect to dashboard

Step 3 (Optional): Enter 2FA code
  -> Click "Verify" button
  -> Wait for redirect to dashboard
```

**OAuth Flow:**

```
Step 1: Click "Sign in with Google"
  -> Redirect to Google's domain
  -> Wait for Google login page

Step 2: Complete Google login
  -> Redirect back to original site
  -> Wait for success indicator
```

## Phase 6: 2FA/MFA Detection (5 minutes)

### Objective

Detect if two-factor authentication is required and identify the input mechanism.

### Steps

1. **Complete Login Without 2FA First**
   - Use test account without 2FA if possible
   - Observe the success flow

2. **Enable 2FA and Test Again**
   - Set up 2FA on account (TOTP/authenticator app recommended)
   - Attempt login
   - Observe what page/form appears

3. **Identify 2FA Input Field**

   Common patterns:

   ```javascript
   // Common selectors for 2FA fields
   document.querySelector('input[name="code"]')
   document.querySelector('input[name="otp"]')
   document.querySelector('input[autocomplete="one-time-code"]')
   document.querySelector('input[maxlength="6"]')  // 6-digit code
   document.querySelector('input[type="text"][placeholder*="code" i]')
   ```

4. **Check URL Patterns**

   ```javascript
   // 2FA pages often have distinctive URLs
   window.location.href.includes('2fa')
   window.location.href.includes('verify')
   window.location.href.includes('mfa')
   window.location.href.includes('otp')
   ```

5. **Check Page Content**

   ```javascript
   // Look for 2FA-related text
   const bodyText = document.body.innerText.toLowerCase();
   bodyText.includes('verification code')
   bodyText.includes('authenticator')
   bodyText.includes('two-factor')
   bodyText.includes('enter code')
   ```

### 2FA Implementation Patterns

**TOTP (Time-based One-Time Password):**

- 6-digit code
- Changes every 30 seconds
- Requires timing consideration in automation
- Can retrieve from 1Password CLI: `op item get "Account" --otp`

**SMS/Email Verification:**

- Harder to automate
- May require manual intervention
- Some services offer API access to SMS/email

**Backup Codes:**

- One-time use codes
- Not suitable for automated testing
- Keep manual fallback ready

## Phase 7: Implementation (30-60 minutes)

### Objective

Translate investigation findings into working automation code.

### Steps

1. **Choose Automation Tool**
   - See [Tool Comparison](tool-comparison.md) for detailed analysis
   - **Playwright** recommended for most cases

2. **Set Up Project**

   ```bash
   # Playwright
   pip install playwright
   playwright install chromium

   # Selenium
   pip install selenium

   # Puppeteer (Node.js)
   npm install puppeteer
   ```

3. **Implement with Proper Waits**

   **Critical: Always wait for elements to be ready!**

   ```python
   # Playwright example
   from playwright.sync_api import sync_playwright

   with sync_playwright() as p:
       browser = p.chromium.launch(headless=False)  # headless=False for debugging
       page = browser.new_page()

       # Step 1: Navigate
       page.goto('https://example.com/login')

       # Step 2: Wait for element and fill
       page.wait_for_selector('#username', state='visible')
       page.fill('#username', 'test@example.com')

       # Step 3: Click and wait for navigation
       page.click('button[data-test="submit-button"]')
       page.wait_for_selector('#password', state='visible')

       # Step 4: Fill password
       page.fill('#password', 'password123')
       page.click('button[type="submit"]')

       # Step 5: Wait for success
       page.wait_for_url('**/dashboard')  # Wait for redirect

       browser.close()
   ```

4. **Add Retry Logic**

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

   @retry(max_attempts=3)
   def click_button(page, selector):
       page.click(selector)
   ```

5. **Handle 2FA if Required**

   ```python
   # Check if 2FA page appeared
   try:
       page.wait_for_selector('input[name="code"]', timeout=5000)
       # 2FA required
       otp_code = get_otp_from_1password()  # or other source
       page.fill('input[name="code"]', otp_code)
       page.click('button:has-text("Verify")')
       page.wait_for_url('**/dashboard')
   except TimeoutError:
       # No 2FA, already logged in
       pass
   ```

6. **Add Error Handling**

   ```python
   try:
       page.fill('#username', username)
   except Exception as e:
       # Capture context for debugging
       page.screenshot(path='error.png')
       print(f"Current URL: {page.url}")
       print(f"Page title: {page.title()}")
       raise RuntimeError(f"Failed to fill username: {e}") from e
   ```

## Phase 8: Debugging and Optimization (15-30 minutes)

### Objective

Identify and fix issues, optimize timing, handle edge cases.

### Debugging Techniques

1. **Progressive Screenshot Capture**

   ```python
   page.screenshot(path='01-initial.png')
   page.fill('#username', username)
   page.screenshot(path='02-username-filled.png')
   page.click('button[type="submit"]')
   page.screenshot(path='03-after-submit.png')
   ```

2. **DOM State Logging**

   ```python
   def log_element_state(page, selector):
       element = page.locator(selector)
       print(f"Selector: {selector}")
       print(f"Visible: {element.is_visible()}")
       print(f"Enabled: {element.is_enabled()}")
       print(f"Value: {element.input_value() if element.is_visible() else 'N/A'}")

   log_element_state(page, '#username')
   ```

3. **Network Monitoring**

   ```python
   # Playwright - listen to network requests
   def log_request(request):
       print(f"Request: {request.method} {request.url}")

   page.on('request', log_request)
   ```

4. **Timing Analysis**

   ```python
   import time

   start = time.time()
   page.goto('https://example.com/login')
   print(f"Page load: {time.time() - start:.2f}s")

   start = time.time()
   page.fill('#username', username)
   print(f"Fill username: {time.time() - start:.2f}s")
   ```

### Optimization Tips

1. **Reduce Unnecessary Waits**
   - Don't use `time.sleep()` for fixed delays
   - Use smart waiting (wait for specific elements)
   - Adjust timeouts based on page load times

2. **Batch JavaScript Operations**

   ```python
   # Bad: Multiple round-trips
   page.evaluate('document.getElementById("username").value = "test"')
   page.evaluate('document.getElementById("username").dispatchEvent(...)')

   # Good: Single round-trip
   page.evaluate('''
       const input = document.getElementById("username");
       input.value = "test";
       input.dispatchEvent(new Event("input", { bubbles: true }));
   ''')
   ```

3. **Implement Session Persistence**

   ```python
   # Check if already logged in
   page.goto('https://example.com/dashboard')
   if 'login' not in page.url:
       print("Already logged in, skipping authentication")
       return

   # Proceed with login...
   ```

## Summary Checklist

Before considering investigation complete, verify:

- [ ] All input fields identified with stable selectors
- [ ] All buttons identified with stable selectors
- [ ] Multi-step flow mapped completely
- [ ] iframe handling strategy determined
- [ ] 2FA detection and handling implemented
- [ ] Wait conditions defined for each step
- [ ] Retry logic added for flaky operations
- [ ] Error handling captures context
- [ ] Screenshots available for debugging
- [ ] End-to-end test passes reliably

## Time Estimates by Complexity

**Simple (single-step form, no 2FA):** 30-60 minutes
**Medium (two-step flow, optional 2FA):** 1-2 hours
**Complex (iframes, required 2FA, dynamic content):** 2-4 hours

## Next Steps

After completing investigation:

- Implement production-ready error handling
- Add comprehensive logging
- Consider rate limiting / bot detection mitigation
- Add monitoring for UI changes (selector breakage)
- Document assumptions and limitations
- Create runbook for maintenance

## Related Documentation

- [Element Selectors](element-selectors.md) - Selector strategy deep dive
- [Tool Comparison](tool-comparison.md) - Choose the right automation tool
- [Common Pitfalls](common-pitfalls.md) - Avoid known mistakes
- [Debugging Techniques](debugging-techniques.md) - Systematic troubleshooting
- [Code Patterns](code-patterns.md) - Reusable implementation templates
