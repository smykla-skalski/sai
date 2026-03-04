# Practical Debugging Workflow: From Failure to Fix

## Contents

- [The Investigation Feedback Loop](#the-investigation-feedback-loop)
  - [Traditional (Slow) Approach](#traditional-slow-approach)
  - [Optimized (Fast) Approach](#optimized-fast-approach)
- [Critical Success Factors](#critical-success-factors)
  - [1. Preserve Browser State (Highest Priority!)](#1-preserve-browser-state-highest-priority)
  - [2. Investigation Handover System](#2-investigation-handover-system)
  - [3. Use browser-controller Skill EARLY](#3-use-browser-controller-skill-early)
- [Systematic Investigation Process](#systematic-investigation-process)
  - [Phase 1: Visual Confirmation (30 seconds)](#phase-1-visual-confirmation-30-seconds)
  - [Phase 2: DOM Structure Investigation (1 minute)](#phase-2-dom-structure-investigation-1-minute)
  - [Phase 3: Interaction Testing (1 minute)](#phase-3-interaction-testing-1-minute)
  - [Phase 4: ARIA & Role Investigation (advanced)](#phase-4-aria--role-investigation-advanced)
- [Real Investigation: Case Study](#real-investigation-case-study)
  - [Problem](#problem)
  - [Investigation Timeline](#investigation-timeline)
- [Common Gotchas & Solutions](#common-gotchas--solutions)
  - [Gotcha 1: Elements Navigate When Clicked](#gotcha-1-elements-navigate-when-clicked)
  - [Gotcha 2: Custom Components Look Like Native Elements](#gotcha-2-custom-components-look-like-native-elements)
  - [Gotcha 3: Element Exists But Not Interactable](#gotcha-3-element-exists-but-not-interactable)
  - [Gotcha 4: Timing Issues](#gotcha-4-timing-issues)
- [Playwright Best Practices from Real Debugging](#playwright-best-practices-from-real-debugging)
  - [Use Modern Locators](#use-modern-locators)
  - [Test Selectors Incrementally](#test-selectors-incrementally)
- [Efficiency Tips](#efficiency-tips)
  - [1. Screenshot Sequence](#1-screenshot-sequence)
  - [2. DOM Queries Library](#2-dom-queries-library)
  - [3. Parallel Investigation](#3-parallel-investigation)
- [Integration with Script Development](#integration-with-script-development)
  - [Development Flow](#development-flow)
  - [When Browser Should Stay Open](#when-browser-should-stay-open)
- [Handover Document Template](#handover-document-template)
- [Summary: The Golden Rules](#summary-the-golden-rules)
- [Tools Comparison](#tools-comparison)
- [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
  - [Anti-Pattern 1: "Log-Only Debugging"](#anti-pattern-1-log-only-debugging)
  - [Anti-Pattern 2: "Change Everything Debugging"](#anti-pattern-2-change-everything-debugging)
  - [Anti-Pattern 3: "Browser Closes Too Soon"](#anti-pattern-3-browser-closes-too-soon)
  - [Anti-Pattern 4: "Late Skill Invocation"](#anti-pattern-4-late-skill-invocation)
- [Conclusion](#conclusion)

**Based on real investigation**: JetBrains Marketplace verification scheduling automation

This document captures proven techniques for rapidly debugging browser automation failures through efficient feedback loops.

## The Investigation Feedback Loop

### Traditional (Slow) Approach

```
1. Run script -> fails
2. Read error logs (guess problem)
3. Modify code based on guess
4. Run script again -> fails differently
5. Repeat 10+ times
Time to solution: Hours
```

### Optimized (Fast) Approach

```
1. Run script with --debug --keep-browser-open
2. Script fails -> browser STAYS OPEN
3. Use browser-controller to inspect live page
4. Understand actual problem in 2-3 minutes
5. Fix code with confidence
6. Test immediately (browser still open!)
Time to solution: Minutes
```

## Critical Success Factors

### 1. Preserve Browser State (Highest Priority!)

**ALWAYS add these flags to automation scripts:**

```python
# In argument parser
parser.add_argument('--debug', action='store_true',
                   help='Enable debug logging and keep browser open on failure')
parser.add_argument('--keep-browser-open', action='store_true',
                   help='Keep browser open after completion (for inspection)')

# In browser launch
browser = p.chromium.launch(
    headless=not args.no_headless,
    devtools=False,  # Don't auto-open DevTools (use browser-controller instead)
    args=["--remote-debugging-port=9222"] if args.debug else [],
)

# CRITICAL: Keep script alive when browser should stay open
try:
    # ... automation code ...
except Exception as e:
    if args.debug or args.keep_browser_open:
        print_investigation_handover(page, e)  # Print state + next steps
        # KEEP SCRIPT ALIVE - prevents Playwright from closing browser
        while True:
            time.sleep(1)  # Browser stays open!
    raise
finally:
    if not args.keep_browser_open:
        browser.close()
```

**Why this matters:**

- Browser state = full context (DOM, network, console logs)
- Without this: you're debugging blind
- With this: you see exactly what script sees

### 2. Investigation Handover System

**When script fails, print investigation commands:**

```python
def print_investigation_handover(page, error):
    """Print actionable investigation instructions."""
    print("\n" + "="*60)
    print("INVESTIGATION HANDOVER")
    print("="*60)
    print(f"Error: {error}")

    try:
        print(f"\nCurrent page state:")
        print(f"   URL: {page.url}")
        print(f"   Title: {page.title()}")
    except:
        print("   (Unable to retrieve page state)")

    print("\nBrowser kept open on port 9222")
    print("\nInvestigation commands:")
    print("   # Take screenshot")
    print("   claude-code-skills browser-controller screenshot")
    print()
    print("   # Check what's actually on the page")
    print('   claude-code-skills browser-controller run "document.querySelectorAll(\'select\').length"')
    print()
    print("   # Find specific elements")
    print('   claude-code-skills browser-controller run "Array.from(document.querySelectorAll(\'button\')).map(b => b.textContent)"')
    print()
    print("   # Clean up when done")
    print("   claude-code-skills browser-controller cleanup --force")
    print("="*60 + "\n")
```

**Result:** Anyone (including AI) can immediately start investigating with copy-paste commands.

### 3. Use browser-controller Skill EARLY

**Don't do this:**

```
Run script 5 times -> read logs -> guess problem -> run again -> repeat...
```

**Do this instead:**

```
Run script ONCE with --debug -> fails -> use browser-controller -> understand -> fix
```

**When to invoke browser-controller:**

- Immediately after first failure (don't wait!)
- When error message mentions "element not found"
- When timeout errors occur
- When unsure about page structure
- Before writing any selector code

## Systematic Investigation Process

### Phase 1: Visual Confirmation (30 seconds)

```bash
# ALWAYS start with a screenshot
claude-code-skills browser-controller screenshot
```

**What to check:**

- Is the expected page loaded? (check URL, title)
- Is the target element visible?
- Are there popups/modals covering the page?
- Is there an error message displayed?

**Example findings:**

- "Oh! The page shows a 404 error" -> URL is wrong
- "The button exists but is disabled" -> need to fill prerequisites first
- "There's a cookie consent modal" -> need to dismiss it first
- "The form exists but uses custom dropdowns" -> change selector strategy

### Phase 2: DOM Structure Investigation (1 minute)

**Check element existence and type:**

```bash
# How many <select> elements?
claude-code-skills browser-controller run "document.querySelectorAll('select').length"

# What buttons exist?
claude-code-skills browser-controller run "Array.from(document.querySelectorAll('button')).map(b => b.textContent.trim()).slice(0, 20)"

# Is target text on page?
claude-code-skills browser-controller run "document.body.innerText.includes('Schedule Verification')"
```

**Common revelations:**

- `select count = 0` -> "They're using custom dropdowns!"
- `button count = 50` -> "Which one is the right button?"
- `target text found = true` -> "Element exists but my selector is wrong"

### Phase 3: Interaction Testing (1 minute)

**Test your selectors before using in script:**

```bash
# Does this selector work?
claude-code-skills browser-controller run "document.querySelector('#my-button') !== null"

# Can I click it?
claude-code-skills browser-controller click "#my-button"

# What happens after click?
claude-code-skills browser-controller screenshot
```

**Catch problems early:**

- Selector matches wrong element
- Click triggers unexpected navigation
- Element exists but not clickable (covered by modal)

### Phase 4: ARIA & Role Investigation (advanced)

**For custom components (React, Vue, etc.):**

```bash
# Find elements by ARIA role
claude-code-skills browser-controller run "Array.from(document.querySelectorAll('[role]')).map(el => ({role: el.getAttribute('role'), text: el.textContent.substring(0, 50)}))"

# Check for combobox (dropdown) pattern
claude-code-skills browser-controller run "document.querySelectorAll('[role=combobox]').length"

# Find by ARIA label
claude-code-skills browser-controller run "document.querySelector('[aria-label=\"IDE\"]')"
```

## Real Investigation: Case Study

### Problem

Script failed: `Timeout waiting for select[name="ide"]`

### Investigation Timeline

**Attempt 1-3 (WRONG APPROACH): 45 minutes wasted**

```
1. Run script -> timeout error
2. Check logs -> "waiting for select..."
3. Guess: "Maybe selector is wrong?"
4. Try: select[name="ideDropdown"]
5. Run script -> still times out
6. Guess: "Maybe it's in an iframe?"
7. Add iframe handling -> still fails
8. Frustration builds...
```

**Attempt 4 (RIGHT APPROACH): 3 minutes to solution**

```
1. Run script with --debug --keep-browser-open
2. Script fails -> browser STAYS OPEN
3. Take screenshot:
   -> See form with "IntelliJ IDEA" dropdown

4. Check DOM:
   -> claude-code-skills browser-controller run "document.querySelectorAll('select').length"
   -> Returns: 0
   -> AHA! No <select> elements exist!

5. Investigate component type:
   -> Screenshot shows dropdown with arrow
   -> Run: document.querySelectorAll('[role=button]')
   -> Find custom dropdown components

6. Fix: Change from <select> selector to text-based:
   -> page.get_by_text("IntelliJ IDEA").click()

7. Test immediately (browser still open!)
   -> Success!
```

**Lesson:** 3 minutes of browser inspection > 45 minutes of blind guessing

## Common Gotchas & Solutions

### Gotcha 1: Elements Navigate When Clicked

**Problem:**

```python
# Click version in sidebar
version.click()
# Try to fill form...
# ERROR: Form not found!
```

**Investigation:**

```bash
# Before click
claude-code-skills browser-controller run "window.location.href"
# -> "https://site.com/edit/versions"

# After click
claude-code-skills browser-controller run "window.location.href"
# -> "https://site.com/edit/versions/stable/123456"
# Clicking caused navigation!
```

**Solution:** Don't click elements that navigate away from target

### Gotcha 2: Custom Components Look Like Native Elements

**Visual:** Looks like `<select>` dropdown

**Reality:** It's a `<div>` styled with CSS

**Detection:**

```bash
claude-code-skills browser-controller run "document.querySelectorAll('select').length"
# -> 0 (no native selects!)

claude-code-skills browser-controller run "document.querySelectorAll('[role=combobox]').length"
# -> 3 (custom dropdowns with ARIA)
```

**Solution:** Use `get_by_role()` or `get_by_text()` instead of element type

### Gotcha 3: Element Exists But Not Interactable

**Error:** `Element is not clickable at point (x, y)`

**Investigation:**

```bash
# Check if visible
claude-code-skills browser-controller run "document.querySelector('#button').offsetParent !== null"

# Check what's covering it
claude-code-skills browser-controller screenshot
# -> Cookie modal is on top!
```

**Solution:** Dismiss overlays first

### Gotcha 4: Timing Issues

**Problem:** Element doesn't exist yet (dynamic content)

**Investigation:**

```bash
# Check if content is loaded
claude-code-skills browser-controller run "document.querySelector('#dynamic-content')"
# -> null (not loaded yet!)

# Wait 2 seconds, check again
claude-code-skills browser-controller run "document.querySelector('#dynamic-content')"
# -> <div id="dynamic-content">...</div> (now exists!)
```

**Solution:** Add explicit waits, check `wait_for_load_state()`

## Playwright Best Practices from Real Debugging

### Use Modern Locators

**Old way (brittle):**

```python
page.locator('select[name="ide"]')  # Assumes <select> element
page.locator('#submit-button')      # Assumes ID exists
page.locator('.dropdown')           # CSS classes change often
```

**New way (resilient):**

```python
page.get_by_role('combobox', name='IDE')        # Works with ARIA
page.get_by_text('Schedule Verification')        # Works with text
page.get_by_label('Build number')                # Works with form labels
page.locator('button:has-text("Submit")')       # Flexible text matching
```

### Test Selectors Incrementally

**Don't do this:**

```python
# Write 50 lines of code
page.goto(url)
page.click('#button1')
page.fill('#input1', 'value')
page.click('#button2')
# ... 10 more interactions ...
# Run script -> fails on line 3 -> wasted time
```

**Do this instead:**

```python
# Test each selector via browser-controller FIRST
# 1. Verify button exists
claude-code-skills browser-controller run "document.querySelector('#button1') !== null"

# 2. Try clicking it
claude-code-skills browser-controller click "#button1"

# 3. Check result
claude-code-skills browser-controller screenshot

# NOW write script with confidence
page.click('#button1')  # You know this works!
```

## Efficiency Tips

### 1. Screenshot Sequence

**Take progressive screenshots:**

```bash
# Before action
claude-code-skills browser-controller screenshot
# -> Save as "before-click.png"

# Perform action
claude-code-skills browser-controller click "#button"

# After action
claude-code-skills browser-controller screenshot
# -> Save as "after-click.png"

# Compare: What changed? Did action work?
```

### 2. DOM Queries Library

**Keep a reference of useful queries:**

```bash
# All buttons
Array.from(document.querySelectorAll('button')).map(b => b.textContent)

# All inputs
Array.from(document.querySelectorAll('input')).map(i => ({type: i.type, name: i.name, value: i.value}))

# All ARIA roles
Array.from(document.querySelectorAll('[role]')).map(el => el.getAttribute('role'))

# Check visibility
window.getComputedStyle(document.querySelector('#elem')).display !== 'none'

# Find by partial text
Array.from(document.querySelectorAll('*')).find(el => el.textContent.includes('Search'))

# Get element HTML
document.querySelector('#elem').outerHTML
```

### 3. Parallel Investigation

**Don't investigate serially:**

```bash
# Slow: One query at a time
screenshot -> wait -> analyze -> next query -> wait -> analyze...
```

**Fast: Capture multiple data points:**

```bash
# Take screenshot
claude-code-skills browser-controller screenshot

# Run multiple queries in one command
claude-code-skills browser-controller run "({
  selectCount: document.querySelectorAll('select').length,
  buttonCount: document.querySelectorAll('button').length,
  hasForm: document.querySelector('form') !== null,
  title: document.title,
  url: window.location.href
})"
```

## Integration with Script Development

### Development Flow

```
1. Write initial script (basic structure)
   |
2. Run with --debug --keep-browser-open
   |
3. Script fails at step X -> browser stays open
   |
4. Investigate live page with browser-controller
   |
5. Understand actual page structure
   |
6. Update selectors in script
   |
7. Kill old script (Ctrl+C)
   |
8. Browser still open -> test new selectors immediately!
   |
9. Selectors work? -> Rerun full script
   |
10. Still fails? -> Repeat from step 4
```

### When Browser Should Stay Open

**Keep browser open when:**

- Script fails (need to investigate)
- Developing new automation (iterating on selectors)
- Debugging timing issues (need to observe state changes)
- Writing complex workflows (verify each step)

**Close browser when:**

- CI/CD pipelines (no human to investigate)
- Production runs (fully tested)
- Headless mode (can't inspect anyway)

## Handover Document Template

**When investigation spans multiple sessions, create a handover document:**

```markdown
# Investigation Handover: [Task Name]

**Date**: YYYY-MM-DD
**Status**: [In Progress / Blocked / Near Complete]
**Browser**: [Open / Closed] - Port 9222

## Problem Statement
[What's broken?]

## Root Cause Analysis
[What causes the problem?]

## Investigation Timeline
- Attempt 1: [What was tried, what failed]
- Attempt 2: [What was tried, what failed]
- Attempt 3: [What worked]

## Key Findings
1. [Finding 1 + evidence]
2. [Finding 2 + evidence]

## Solution
[How to fix + code snippets]

## Next Steps
1. [Step 1]
2. [Step 2]
```

## Summary: The Golden Rules

1. **Never run blind** - Always use `--debug --keep-browser-open`
2. **Screenshot first** - Visual confirmation beats log reading
3. **Query before coding** - Test selectors in browser before script
4. **Preserve state** - Keep browser alive, don't let it close
5. **Invoke skills early** - Use browser-controller on first failure
6. **Document handovers** - Enable continuity across sessions
7. **Test incrementally** - Verify each step before moving forward
8. **Learn from errors** - Each failure teaches page structure
9. **Use modern locators** - Text/role-based > CSS selectors
10. **Iterate fast** - Feedback loop < 2 minutes = winning

## Tools Comparison

| Task               | Tool                                  | Why                          |
|:-------------------|:--------------------------------------|:-----------------------------|
| Take screenshot    | `browser-controller screenshot`       | Visual confirmation fastest  |
| Query DOM          | `browser-controller run "js"`         | Test selectors before coding |
| Test interaction   | `browser-controller click`            | Verify clickability          |
| Navigate           | `browser-controller navigate`         | Move between pages           |
| Keep browser alive | Script with `--keep-browser-open`     | Preserve full state          |
| Find elements      | Chrome DevTools (F12)                 | Interactive exploration      |
| Test selectors     | `document.querySelector()` in console | Instant validation           |

## Anti-Patterns to Avoid

### Anti-Pattern 1: "Log-Only Debugging"

```
Read error logs -> guess problem -> modify code -> run -> repeat
```

**Why bad:** No visual confirmation, pure speculation

**Fix:** Use browser-controller to see actual page

### Anti-Pattern 2: "Change Everything Debugging"

```
Modify 10 things at once -> run -> still fails -> no idea what helped
```

**Why bad:** Can't isolate which change fixed it

**Fix:** Change one thing, test, iterate

### Anti-Pattern 3: "Browser Closes Too Soon"

```
Script fails -> browser closes -> try to debug from logs alone
```

**Why bad:** Lost all context (DOM state, console logs, network)

**Fix:** Always use `--keep-browser-open` during development

### Anti-Pattern 4: "Late Skill Invocation"

```
Try 10 approaches -> all fail -> finally use browser-controller -> find problem immediately
```

**Why bad:** Wasted time on wrong approaches

**Fix:** Use browser-controller on FIRST failure

## Conclusion

**Before this investigation methodology:**

- Debugging = frustrating guessing game
- Hours per fix
- Multiple script runs wasted
- Limited confidence in solutions

**After this investigation methodology:**

- Debugging = systematic discovery process
- Minutes per fix
- Test selectors before committing
- High confidence (visual confirmation)

**Key insight:** The browser IS your debugger. Keep it open, use it actively, iterate rapidly.

---

*This document based on real investigation of JetBrains Marketplace automation (Dec 2025), capturing techniques that reduced investigation time from 2+ hours to < 10 minutes.*
