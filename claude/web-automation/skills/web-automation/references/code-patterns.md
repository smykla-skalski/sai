# Code Patterns

## Contents

- [Retry Decorator](#retry-decorator)
- [Wait for Element Pattern](#wait-for-element-pattern)
- [Validated Dropdown Selection](#validated-dropdown-selection)
- [Modal Handling Pattern](#modal-handling-pattern)
- [2FA/TOTP Handling](#2fatotp-handling)
- [Credential Management (1Password CLI)](#credential-management-1password-cli)
- [Error Context Capture](#error-context-capture)
- [Session Persistence Check](#session-persistence-check)
- [Comprehensive Login Flow](#comprehensive-login-flow)
- [Two-Step Form Pattern](#two-step-form-pattern)
- [Related Documentation](#related-documentation)

Reusable implementation templates for common web automation scenarios.

## Retry Decorator

**Pattern:** Retry failed operations with exponential backoff.

```python
from functools import wraps
import time

def retry(max_attempts=3, delay=2.0, backoff=2):
    """Retry decorator with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    wait = delay * (backoff ** (attempt - 1))
                    print(f"Attempt {attempt} failed: {e}. Retrying in {wait}s...")
                    time.sleep(wait)
        return wrapper
    return decorator

# Usage
@retry(max_attempts=3, delay=2, backoff=2)
def click_flaky_button(page, selector):
    """Click button that sometimes fails."""
    page.click(selector)
```

## Wait for Element Pattern

**Pattern:** Smart waiting for element to be ready.

```python
def wait_for_element(page, selector, state='visible', timeout=10000):
    """Wait for element with multiple state options."""
    page.wait_for_selector(selector, state=state, timeout=timeout)

    # Optional: Wait for stability (animations complete)
    if state == 'visible':
        page.wait_for_selector(selector, state='stable', timeout=2000)

    return page.locator(selector)

# Usage
element = wait_for_element(page, '#submit-button')
element.click()
```

## Validated Dropdown Selection

**Pattern:** Select dropdown option and verify selection succeeded.

```python
def select_dropdown_verified(page, selector, label):
    """Select dropdown option with verification."""
    dropdown = page.locator(selector)

    # Wait for dropdown to be populated
    page.wait_for_selector(f'{selector} option', timeout=5000)

    # Check if option exists
    options = dropdown.locator('option').all_inner_texts()
    if label not in options:
        raise ValueError(f"Option '{label}' not found. Available: {options}")

    # Select option
    dropdown.select_option(label=label)

    # Verify selection
    selected = dropdown.input_value()
    if selected != label:
        raise RuntimeError(f"Failed to select '{label}', got '{selected}'")

    return selected

# Usage
select_dropdown_verified(page, '#country', 'United States')
```

## Modal Handling Pattern

**Pattern:** Interact with modal and verify closure.

```python
def handle_modal(page, modal_trigger_fn, modal_actions_fn):
    """Handle modal dialog with guaranteed closure."""
    # Trigger modal
    modal_trigger_fn()

    # Wait for modal to appear
    page.wait_for_selector('[role="dialog"], .modal', state='visible')

    # Perform actions in modal
    modal_actions_fn(page)

    # Close modal (adjust selector as needed)
    page.keyboard.press('Escape')

    # CRITICAL: Verify modal is actually gone
    page.wait_for_selector('[role="dialog"], .modal', state='hidden', timeout=5000)

# Usage
def open_modal():
    page.click('button:has-text("Edit Profile")')

def fill_modal(page):
    page.fill('#name', 'John Doe')
    page.click('button:has-text("Save")')

handle_modal(page, open_modal, fill_modal)
```

## 2FA/TOTP Handling

**Pattern:** Retrieve and submit TOTP code with timing optimization.

```python
import time
import subprocess

def get_fresh_totp(item_name, max_age_seconds=5):
    """Get TOTP ensuring it won't expire soon."""
    # Get current position in 30s cycle
    current_second = time.time() % 30

    # If less than max_age seconds remaining, wait for next code
    if current_second > (30 - max_age_seconds):
        wait_time = 30 - current_second + 1
        print(f"Waiting {wait_time:.0f}s for fresh TOTP...")
        time.sleep(wait_time)

    # Get code from 1Password CLI
    result = subprocess.run(
        ['op', 'item', 'get', item_name, '--otp'],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()

def handle_2fa_if_required(page, otp_provider):
    """Handle 2FA if page requires it."""
    # Check if 2FA page appeared
    try:
        page.wait_for_selector('input[name="code"]', timeout=3000)
    except:
        # No 2FA required
        return False

    # 2FA required - get fresh code
    otp = get_fresh_totp('JetBrains Account')

    # Fill and submit
    page.fill('input[name="code"]', otp)
    page.click('button:has-text("Verify")')

    # Wait for success
    page.wait_for_url('**/dashboard', timeout=10000)

    return True

# Usage
page.fill('#password', password)
page.click('button[type="submit"]')
handle_2fa_if_required(page, get_fresh_totp)
```

## Credential Management (1Password CLI)

**Pattern:** Securely retrieve credentials without hardcoding.

```python
import subprocess
from dataclasses import dataclass
from typing import Callable

@dataclass
class Credentials:
    """Container for credentials with optional OTP provider."""
    username: str
    password: str
    otp_provider: Callable[[], str] | None = None

def get_credentials_from_1password(item_name: str) -> Credentials:
    """Retrieve credentials from 1Password CLI."""
    def get_field(field_name):
        result = subprocess.run(
            ['op', 'item', 'get', item_name, '--fields', f'label={field_name}'],
            capture_output=True,
            text=True,
            check=True
        )
        value = result.stdout.strip()
        if not value:
            raise RuntimeError(f"{field_name} field is empty")
        return value

    def get_otp():
        result = subprocess.run(
            ['op', 'item', 'get', item_name, '--otp'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()

    username = get_field('username')
    password = get_field('password')

    # Test if OTP available
    otp_provider = None
    try:
        test_otp = get_otp()
        if test_otp:
            otp_provider = get_otp
    except:
        pass  # OTP not configured

    return Credentials(username, password, otp_provider)

# Usage
creds = get_credentials_from_1password('JetBrains Account')
page.fill('#username', creds.username)
page.fill('#password', creds.password)
if creds.otp_provider:
    otp = creds.otp_provider()
    page.fill('#otp', otp)
```

## Error Context Capture

**Pattern:** Capture rich debugging context on failure.

```python
import time
from pathlib import Path

def capture_error_context(page, error, debug_dir='debug'):
    """Capture comprehensive error context."""
    Path(debug_dir).mkdir(exist_ok=True)

    timestamp = int(time.time())
    context = {
        'error': str(error),
        'url': page.url,
        'title': page.title(),
        'screenshot': f'{debug_dir}/error-{timestamp}.png',
        'html': f'{debug_dir}/error-{timestamp}.html',
    }

    # Capture screenshot
    page.screenshot(path=context['screenshot'])

    # Capture HTML
    html = page.content()
    Path(context['html']).write_text(html)

    # Capture visible text (first 500 chars)
    try:
        context['visible_text'] = page.locator('body').inner_text()[:500]
    except:
        context['visible_text'] = 'N/A'

    return context

# Usage in try/except
try:
    page.fill('#username', username)
except Exception as e:
    context = capture_error_context(page, e)
    print(f"Error: {e}")
    print(f"Screenshot: {context['screenshot']}")
    print(f"HTML: {context['html']}")
    raise
```

## Session Persistence Check

**Pattern:** Skip login if already authenticated.

```python
def is_logged_in(page, logged_in_url_pattern):
    """Check if user is already logged in."""
    page.goto('https://example.com/dashboard')

    # Method 1: Check URL
    if logged_in_url_pattern in page.url:
        return True

    # Method 2: Check for logout button
    try:
        page.wait_for_selector('button:has-text("Logout")', timeout=2000)
        return True
    except:
        pass

    # Method 3: Check for user menu
    try:
        page.wait_for_selector('[data-test="user-menu"]', timeout=2000)
        return True
    except:
        pass

    return False

# Usage
if is_logged_in(page, '/dashboard'):
    print("Already logged in, skipping authentication")
else:
    perform_login(page, credentials)
```

## Comprehensive Login Flow

**Pattern:** Complete login with all best practices.

```python
def login_with_2fa(page, credentials, login_url):
    """
    Complete login flow with 2FA support.

    Args:
        page: Playwright page object
        credentials: Credentials object with username, password, otp_provider
        login_url: Login page URL
    """
    print("Starting login...")

    # Navigate
    page.goto(login_url, wait_until='networkidle')
    print("Navigated to login page")

    # Step 1: Email/username
    page.wait_for_selector('#username', state='visible')
    page.fill('#username', credentials.username)
    print(f"Filled username: {credentials.username[:3]}***")

    # Click Next (if two-step)
    try:
        next_button = page.locator('button:has-text("Next")')
        if next_button.is_visible(timeout=1000):
            next_button.click()
            print("Clicked Next")
            page.wait_for_selector('#password', state='visible', timeout=10000)
    except:
        pass  # Single-step login

    # Step 2: Password
    page.wait_for_selector('#password', state='visible')
    page.fill('#password', credentials.password)
    print("Filled password")

    # Submit
    page.click('button[type="submit"]')
    print("Submitted login form")

    # Step 3: Handle 2FA if required
    try:
        page.wait_for_selector('input[name="code"]', timeout=5000)
        print("2FA required")

        if not credentials.otp_provider:
            raise RuntimeError("2FA required but OTP provider not configured")

        # Get fresh TOTP
        otp = get_fresh_totp(credentials.otp_provider)
        page.fill('input[name="code"]', otp)
        print(f"Filled OTP: {otp[:3]}***")

        page.click('button:has-text("Verify")')
        print("Submitted 2FA")

    except TimeoutError:
        print("No 2FA required")

    # Wait for success
    page.wait_for_url('**/dashboard', timeout=10000)
    print(f"Login successful! URL: {page.url}")

# Usage
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    creds = get_credentials_from_1password('My Account')
    login_with_2fa(page, creds, 'https://example.com/login')

    # Now authenticated, continue automation...

    browser.close()
```

## Two-Step Form Pattern

**Pattern:** Handle multi-step forms with proper waiting.

```python
def fill_two_step_form(page, step1_data, step2_data):
    """Fill two-step form with proper waits."""
    # Step 1
    for field_id, value in step1_data.items():
        page.fill(f'#{field_id}', value)

    page.click('button:has-text("Next")')

    # Wait for step 2 to appear (check for new field)
    first_step2_field = list(step2_data.keys())[0]
    page.wait_for_selector(f'#{first_step2_field}', state='visible')

    # Step 2
    for field_id, value in step2_data.items():
        page.fill(f'#{field_id}', value)

    page.click('button[type="submit"]')

# Usage
fill_two_step_form(
    page,
    step1_data={'email': 'test@example.com'},
    step2_data={'password': 'pass123', 'confirm_password': 'pass123'}
)
```

## Related Documentation

- [Investigation Workflow](investigation-workflow.md) - When to use these patterns
- [Common Pitfalls](common-pitfalls.md) - Why these patterns prevent issues
- [Debugging Techniques](debugging-techniques.md) - How to debug when patterns fail
- [Tool Comparison](tool-comparison.md) - Tool-specific variations
