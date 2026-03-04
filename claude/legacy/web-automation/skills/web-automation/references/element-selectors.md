# Element Selectors

## Contents

- [Selector Priority Hierarchy](#selector-priority-hierarchy)
  - [1. `id` Attribute (Best Choice)](#1-id-attribute-best-choice)
  - [2. `name` Attribute (Excellent for Forms)](#2-name-attribute-excellent-for-forms)
  - [3. `data-*` Attributes (Framework-Specific)](#3-data--attributes-framework-specific)
  - [4. `aria-label` and Accessibility Attributes (Stable)](#4-aria-label-and-accessibility-attributes-stable)
  - [5. CSS Classes (Risky)](#5-css-classes-risky)
  - [6. XPath (Very Brittle)](#6-xpath-very-brittle)
- [Advanced Selector Strategies](#advanced-selector-strategies)
  - [Combining Selectors for Specificity](#combining-selectors-for-specificity)
  - [Text-Based Selectors (Playwright)](#text-based-selectors-playwright)
  - [Handling Dynamic IDs](#handling-dynamic-ids)
  - [iframe Selectors](#iframe-selectors)
  - [Shadow DOM Selectors](#shadow-dom-selectors)
- [Selector Testing Techniques](#selector-testing-techniques)
  - [Testing in Browser Console](#testing-in-browser-console)
  - [Selector Debugging Helper](#selector-debugging-helper)
- [Element State Checks](#element-state-checks)
  - [Visibility vs Existence](#visibility-vs-existence)
  - [Element Enabled vs Disabled](#element-enabled-vs-disabled)
  - [Element in Viewport](#element-in-viewport)
- [Wait Strategies](#wait-strategies)
  - [Why Waiting Matters](#why-waiting-matters)
  - [Playwright Wait Strategies](#playwright-wait-strategies)
  - [Waiting for Element to be Stable](#waiting-for-element-to-be-stable)
- [Common Selector Patterns](#common-selector-patterns)
  - [Form Elements](#form-elements)
  - [Buttons](#buttons)
  - [Links](#links)
  - [Tables](#tables)
  - [Lists](#lists)
- [Selector Best Practices](#selector-best-practices)
- [Troubleshooting Selectors](#troubleshooting-selectors)
  - [Issue: "Element not found"](#issue-element-not-found)
  - [Issue: "Multiple elements match"](#issue-multiple-elements-match)
  - [Issue: "Element not visible"](#issue-element-not-visible)
- [Related Documentation](#related-documentation)

Comprehensive guide to finding, testing, and using element selectors for web automation.

## Selector Priority Hierarchy

Choose the most specific and stable selector available. Ordered from best to worst:

### 1. `id` Attribute (Best Choice)

**Why:** Unique by HTML spec, rarely changes, fastest lookup.

```javascript
document.getElementById('username')
```

**Playwright:**

```python
page.locator('#username')
page.fill('#username', 'test@example.com')
```

**When to use:** Always prefer `id` when available.

**Caveat:** Some frameworks generate dynamic IDs (e.g., `input-field-1234-abcd`). Check if ID is stable across page loads.

### 2. `name` Attribute (Excellent for Forms)

**Why:** Semantic meaning, used by forms for submission, usually stable.

```javascript
document.querySelector('input[name="email"]')
```

**Playwright:**

```python
page.locator('input[name="email"]')
```

**When to use:** Form inputs, especially when no `id` is available.

### 3. `data-*` Attributes (Framework-Specific)

**Why:** Explicitly set by developers for testing/automation, stable.

```javascript
document.querySelector('[data-test="submit-button"]')
document.querySelector('[data-testid="login-form"]')
document.querySelector('[data-qa="username-input"]')
```

**Playwright:**

```python
page.locator('[data-test="submit-button"]')
```

**When to use:** Modern applications that follow testing best practices.

**Common naming patterns:**

- `data-test`
- `data-testid`
- `data-qa`
- `data-cy` (Cypress)
- `data-selenium-id`

### 4. `aria-label` and Accessibility Attributes (Stable)

**Why:** Accessibility attributes rarely change, semantic meaning.

```javascript
document.querySelector('[aria-label="Email address"]')
document.querySelector('[aria-labelledby="username-label"]')
document.querySelector('[role="button"][aria-label="Submit"]')
```

**Playwright:**

```python
page.get_by_label('Email address')  # Built-in accessibility locator
page.locator('[aria-label="Email address"]')
```

**When to use:** Accessible applications, good fallback when `id`/`name` unavailable.

### 5. CSS Classes (Risky)

**Why:** Can change with design/styling, not semantically meaningful.

```javascript
document.querySelector('.login-button')
document.querySelector('.form-input.email-field')
```

**Playwright:**

```python
page.locator('.login-button')
```

**When to use:** Last resort for static elements, combine with other selectors.

**Risk:** Classes like `.btn-primary` or `.mt-3` (utility classes) change frequently.

### 6. XPath (Very Brittle)

**Why:** Breaks easily with DOM changes, hard to read/maintain.

```javascript
document.evaluate('//button[text()="Submit"]', ...)
```

**Playwright:**

```python
page.locator('xpath=//button[text()="Submit"]')
```

**When to use:** Only when no other option exists, prefer Playwright's text locators instead.

## Advanced Selector Strategies

### Combining Selectors for Specificity

**Problem:** Multiple elements match your selector.

**Solution:** Combine multiple attributes.

```javascript
// Too broad: matches all text inputs
document.querySelector('input[type="text"]')

// More specific: email input only
document.querySelector('input[type="text"][name="email"]')

// Even more specific
document.querySelector('form#login-form input[name="email"]')
```

**Playwright:**

```python
# Chaining selectors
page.locator('form#login-form').locator('input[name="email"]')

# Or combined
page.locator('form#login-form input[name="email"]')
```

### Text-Based Selectors (Playwright)

**Use when:** Element has unique visible text.

```python
# Exact text match
page.get_by_text('Sign In')

# Partial text match
page.get_by_text('Sign In', exact=False)

# Button with specific text
page.get_by_role('button', name='Submit')

# Link with specific text
page.get_by_role('link', name='Forgot password?')
```

**Advantages:**

- Resilient to DOM changes
- Matches user's mental model
- Good for end-to-end tests

**Disadvantages:**

- Breaks with internationalization (i18n)
- Sensitive to text changes

### Handling Dynamic IDs

**Problem:** IDs change on every page load.

```html
<!-- ID changes: input-field-1234, input-field-5678, etc. -->
<input id="input-field-1234" name="email" />
```

**Solution 1: Use `name` or other stable attribute**

```python
page.locator('input[name="email"]')
```

**Solution 2: Partial ID match with regex**

```python
# Matches any ID starting with "input-field-"
page.locator('input[id^="input-field-"]')
```

**Solution 3: Use parent element with stable ID**

```python
# Find by parent, then child
page.locator('#email-container input')
```

### iframe Selectors

**Problem:** Element is inside an iframe.

**Solution (Playwright):**

```python
# Switch to iframe context
iframe = page.frame_locator('iframe#login-frame')

# Query within iframe
iframe.locator('#username').fill('test@example.com')

# Or by frame name/title
iframe = page.frame_locator('[name="login"]')
iframe.locator('#username').fill('test@example.com')
```

**Solution (Selenium):**

```python
# Switch context
driver.switch_to.frame('login-frame')
driver.find_element(By.ID, 'username').send_keys('test@example.com')

# Switch back to main page
driver.switch_to.default_content()
```

**Cross-Origin Limitation:**
If iframe is from different domain (e.g., embedded Google/Facebook login), browser security blocks direct access. Browser automation tools handle this, but console scripts cannot.

### Shadow DOM Selectors

**Problem:** Element is inside Shadow DOM (Web Components).

**Detection:**

```javascript
// Check if element has shadow root
const host = document.querySelector('#custom-element');
console.log('Has shadow root:', host.shadowRoot !== null);
```

**Solution (Playwright):**

```python
# Playwright handles Shadow DOM automatically
page.locator('#custom-element').locator('#internal-button').click()
```

**Solution (Manual JavaScript):**

```javascript
// Access shadow root
const host = document.querySelector('#custom-element');
const shadowRoot = host.shadowRoot;
const button = shadowRoot.querySelector('#internal-button');
button.click();
```

## Selector Testing Techniques

### Testing in Browser Console

Always test selectors in console before implementing:

```javascript
// 1. Check if selector matches anything
const element = document.querySelector('#username');
console.log('Found:', element);  // Should not be null

// 2. Check how many elements match
const all = document.querySelectorAll('input[type="text"]');
console.log('Count:', all.length);  // Should be 1 for unique selector

// 3. Verify it's the right element
const el = document.querySelector('#username');
console.log('Attributes:', {
  id: el.id,
  name: el.name,
  type: el.type,
  placeholder: el.placeholder
});

// 4. Check visibility
const style = window.getComputedStyle(el);
console.log('Visible:', style.display !== 'none' && style.visibility !== 'hidden');
```

### Selector Debugging Helper

```javascript
function debugSelector(selector) {
  const elements = document.querySelectorAll(selector);

  console.log(`Selector: ${selector}`);
  console.log(`Matches: ${elements.length}`);

  elements.forEach((el, index) => {
    const style = window.getComputedStyle(el);
    console.log(`\nMatch ${index + 1}:`, {
      tag: el.tagName,
      id: el.id,
      name: el.name,
      classes: el.className,
      text: el.innerText?.substring(0, 50),
      visible: style.display !== 'none' && style.visibility !== 'hidden',
      offsetParent: el.offsetParent !== null
    });
  });
}

// Usage
debugSelector('input[type="text"]');
```

## Element State Checks

### Visibility vs Existence

**Element exists but not visible:**

```javascript
const element = document.getElementById('username');

// Exists?
console.log('Exists:', element !== null);

// Visible?
const style = window.getComputedStyle(element);
const visible = style.display !== 'none'
  && style.visibility !== 'hidden'
  && element.offsetParent !== null;

console.log('Visible:', visible);
```

**Playwright built-in checks:**

```python
# Wait for element to exist
page.locator('#username').wait_for(state='attached')

# Wait for element to be visible
page.locator('#username').wait_for(state='visible')

# Wait for element to be enabled
page.locator('button[type="submit"]').wait_for(state='enabled')
```

### Element Enabled vs Disabled

```javascript
const button = document.querySelector('button[type="submit"]');

// Check disabled state
console.log('Disabled:', button.disabled);
console.log('Has disabled attr:', button.hasAttribute('disabled'));

// Button may be disabled by validation
// Fill form fields, then recheck
```

**Playwright:**

```python
# Check if enabled
is_enabled = page.locator('button[type="submit"]').is_enabled()

# Wait for button to become enabled
page.locator('button[type="submit"]').wait_for(state='enabled', timeout=5000)
```

### Element in Viewport

```javascript
function isInViewport(element) {
  const rect = element.getBoundingClientRect();
  return (
    rect.top >= 0 &&
    rect.left >= 0 &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
  );
}

const element = document.getElementById('submit-button');
console.log('In viewport:', isInViewport(element));
```

## Wait Strategies

### Why Waiting Matters

**Problem:** Element doesn't exist yet when code tries to interact with it.

**Common mistakes:**

```python
# BAD: No wait, will fail if page hasn't loaded
page.click('#username')

# BAD: Fixed sleep is unreliable
time.sleep(5)
page.click('#username')

# GOOD: Wait for element to be ready
page.wait_for_selector('#username', state='visible')
page.click('#username')
```

### Playwright Wait Strategies

**1. Wait for selector (visibility)**

```python
# Wait for element to be visible (default behavior)
page.wait_for_selector('#username', state='visible', timeout=10000)
```

**2. Wait for selector (attached to DOM)**

```python
# Element exists but may not be visible
page.wait_for_selector('#username', state='attached', timeout=10000)
```

**3. Wait for selector (hidden/removed)**

```python
# Wait for element to disappear
page.wait_for_selector('.loading-spinner', state='hidden', timeout=10000)
```

**4. Wait for URL**

```python
# Wait for navigation to specific URL
page.wait_for_url('**/dashboard')

# Wait for URL pattern
page.wait_for_url(re.compile(r'.*/success.*'))
```

**5. Wait for network idle**

```python
# Wait for page load to complete
page.goto('https://example.com', wait_until='networkidle')
```

**6. Wait for JavaScript function**

```python
# Wait for custom condition
page.wait_for_function('() => document.querySelectorAll(".item").length > 10')
```

### Waiting for Element to be Stable

**Problem:** Element moves due to animations or layout shifts.

```python
# Playwright automatically waits for element to be stable before clicking
page.click('#username')  # Waits for animations to complete

# Explicit stability check
page.locator('#username').wait_for(state='stable', timeout=5000)
```

## Common Selector Patterns

### Form Elements

```python
# Text input
page.locator('input[type="text"][name="email"]')

# Password input
page.locator('input[type="password"]')

# Checkbox
page.locator('input[type="checkbox"][name="remember"]')

# Radio button
page.locator('input[type="radio"][value="option1"]')

# Select dropdown
page.locator('select[name="country"]')

# Textarea
page.locator('textarea[name="message"]')
```

### Buttons

```python
# By ID
page.locator('button#submit-btn')

# By type
page.locator('button[type="submit"]')

# By text (Playwright)
page.get_by_role('button', name='Sign In')

# By data attribute
page.locator('button[data-test="login-button"]')
```

### Links

```python
# By href
page.locator('a[href="/login"]')

# By text (Playwright)
page.get_by_role('link', name='Forgot password?')

# Contains text
page.locator('a:has-text("Sign Up")')
```

### Tables

```python
# Specific table cell
page.locator('table tr:nth-child(2) td:nth-child(3)')

# Row containing text
page.locator('table tr:has-text("John Doe")')

# First row
page.locator('table tr').first

# Last row
page.locator('table tr').last
```

### Lists

```python
# All list items
page.locator('ul li')

# Specific list item
page.locator('ul li:nth-child(2)')

# List item containing text
page.locator('ul li:has-text("Option A")')
```

## Selector Best Practices

1. **Prefer stable attributes over fragile ones**
   - Use `id`, `name`, `data-*`, `aria-label`
   - Avoid CSS classes, XPath

2. **Test selectors in console before implementing**
   - Verify uniqueness (`querySelectorAll().length === 1`)
   - Check visibility and state

3. **Make selectors specific but not overly specific**
   - Good: `form#login input[name="email"]`
   - Bad: `div > div > div > form > div > input`

4. **Use Playwright's built-in locators when possible**
   - `get_by_role()`, `get_by_label()`, `get_by_text()`
   - More resilient to DOM changes

5. **Add waits for dynamic content**
   - Always wait for elements to be visible/enabled
   - Use smart waits, not fixed `time.sleep()`

6. **Document why you chose a selector**

   ```python
   # Using data-test because ID is dynamically generated
   page.locator('[data-test="submit-button"]').click()
   ```

7. **Maintain a selector fallback strategy**

   ```python
   def find_submit_button(page):
       # Try primary selector
       try:
           return page.locator('button[data-test="submit"]')
       except:
           # Fallback to text-based
           return page.get_by_role('button', name='Submit')
   ```

## Troubleshooting Selectors

### Issue: "Element not found"

**Causes:**

- Element doesn't exist on page
- Typo in selector
- Element inside iframe
- Element not loaded yet

**Debug steps:**

```python
# 1. Check if page loaded correctly
print(f"Current URL: {page.url}")
print(f"Page title: {page.title()}")

# 2. Take screenshot
page.screenshot(path='debug.png')

# 3. Check all matching elements
count = page.locator('input[type="text"]').count()
print(f"Text inputs found: {count}")

# 4. List all inputs
all_inputs = page.evaluate('''
  Array.from(document.querySelectorAll('input')).map(i => ({
    type: i.type,
    id: i.id,
    name: i.name,
    visible: i.offsetParent !== null
  }))
''')
print(all_inputs)
```

### Issue: "Multiple elements match"

**Solution:** Make selector more specific.

```python
# Check count first
count = page.locator('button').count()
print(f"Buttons found: {count}")

# If > 1, add specificity
# Option 1: Add parent context
page.locator('form#login button[type="submit"]')

# Option 2: Use .first or .last
page.locator('button[type="submit"]').first

# Option 3: Filter by text
page.locator('button', has_text='Sign In')
```

### Issue: "Element not visible"

**Causes:**

- Element hidden by CSS (`display: none`, `visibility: hidden`)
- Element outside viewport
- Element covered by another element (modal, overlay)

**Debug:**

```javascript
const element = document.getElementById('username');
const style = window.getComputedStyle(element);

console.log({
  display: style.display,
  visibility: style.visibility,
  offsetParent: element.offsetParent,
  zIndex: style.zIndex,
  position: style.position,
  top: element.getBoundingClientRect().top,
  left: element.getBoundingClientRect().left
});
```

## Related Documentation

- [Investigation Workflow](investigation-workflow.md) - Complete investigation process
- [Debugging Techniques](debugging-techniques.md) - Troubleshooting selector issues
- [Common Pitfalls](common-pitfalls.md) - Selector-related mistakes to avoid
- [Code Patterns](code-patterns.md) - Reusable selector patterns
