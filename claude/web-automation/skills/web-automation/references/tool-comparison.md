# Tool Comparison

## Contents

- [Quick Decision Tree](#quick-decision-tree)
- [Feature Matrix](#feature-matrix)
- [Detailed Comparison](#detailed-comparison)
  - [Playwright (Recommended for Most Cases)](#playwright-recommended-for-most-cases)
  - [Selenium (Mature and Stable)](#selenium-mature-and-stable)
  - [Puppeteer (Fastest for Chrome)](#puppeteer-fastest-for-chrome)
  - [MCP browser-controller (AI-Driven)](#mcp-browser-controller-ai-driven)
  - [Direct HTTP/API Approach (Fastest)](#direct-httpapi-approach-fastest)
- [Performance Comparison](#performance-comparison)
- [Language-Specific Recommendations](#language-specific-recommendations)
  - [Python Projects](#python-projects)
  - [Node.js Projects](#nodejs-projects)
  - [Java/C# Projects](#javac-projects)
  - [Any Language (via subprocess)](#any-language-via-subprocess)
- [Migration Paths](#migration-paths)
  - [From Selenium to Playwright](#from-selenium-to-playwright)
  - [From Puppeteer to Playwright](#from-puppeteer-to-playwright)
- [Summary Recommendations](#summary-recommendations)
- [Related Documentation](#related-documentation)

Comprehensive comparison of browser automation tools to help you choose the right one for your project.

## Quick Decision Tree

```
Do you need iframe support + cross-browser testing?
  |- YES -> Playwright (recommended)
  |- NO  -> Continue...

Is your project Node.js-based and Chrome-only is acceptable?
  |- YES -> Puppeteer (fastest, simplest)
  |- NO  -> Continue...

Do you need WebDriver protocol or legacy browser support?
  |- YES -> Selenium (most mature)
  |- NO  -> Continue...

Are you using Claude Code and want AI-driven automation?
  |- YES -> MCP browser-controller (easiest to start)
  |- NO  -> Continue...

Can you solve this with HTTP requests instead of browser?
  |- YES -> Direct HTTP/API (no browser needed!)
  |- NO  -> Default to Playwright
```

## Feature Matrix

| Feature                  | Playwright        | Selenium          | Puppeteer         | MCP browser-ctrl |
|:-------------------------|:------------------|:------------------|:------------------|:-----------------|
| **Language Support**     | Python, Node, etc | Python, Java, etc | Node.js only      | Any (subprocess) |
| **Browser Support**      | Chromium, FF, WK  | Chrome, FF, etc   | Chromium only     | Chrome, Safari   |
| **Cross-Browser**        | Excellent         | Excellent         | Chrome only       | Limited          |
| **iframe Support**       | Excellent         | Good              | Good              | None             |
| **Auto-Waiting**         | Built-in          | Manual needed     | Manual needed     | Built-in         |
| **Headless Mode**        | Yes               | Yes               | Yes               | Yes              |
| **Network Interception** | Built-in          | Via extensions    | Built-in          | No               |
| **Screenshots/PDFs**     | Excellent         | Basic             | Excellent         | Large files      |
| **Shadow DOM**           | Auto-handled      | Manual access     | Manual access     | Unknown          |
| **Speed**                | Fast              | Medium            | Fastest           | Fast             |
| **Setup Complexity**     | Easy              | Medium            | Very Easy         | Requires MCP     |
| **Community/Docs**       | Excellent         | Mature            | Good              | Limited          |
| **Stability**            | Very stable       | Very stable       | Stable            | Beta             |
| **Best For**             | Modern web apps   | Enterprise/legacy | Chrome automation | AI exploration   |

## Detailed Comparison

### Playwright (Recommended for Most Cases)

**Official Site:** https://playwright.dev/

**Why Choose Playwright:**

- Modern API designed from ground up
- Built-in smart waiting (no more flaky tests)
- Excellent iframe and Shadow DOM support
- Cross-browser testing out of the box
- Active development by Microsoft
- Great documentation and examples

**Installation:**

```bash
# Python
pip install playwright
playwright install chromium

# Node.js
npm install playwright

# Install all browsers
playwright install
```

**Hello World Example:**

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    # Navigate
    page.goto('https://example.com/login')

    # Fill form (auto-waits for element)
    page.fill('#username', 'test@example.com')
    page.fill('#password', 'password123')

    # Click button (auto-waits for navigation)
    page.click('button[type="submit"]')

    # Wait for success
    page.wait_for_url('**/dashboard')

    print(f"Logged in! Current URL: {page.url}")

    browser.close()
```

**Advantages:**

- Auto-waits for elements to be ready (actionable)
- Built-in retry logic for flaky operations
- Excellent iframe context switching
- Network request/response interception
- Browser context isolation (parallel testing)
- Mobile emulation support
- Trace viewer for debugging (visual timeline)

**Disadvantages:**

- Newer than Selenium (less Stack Overflow content)
- Binary size (~300MB with browsers)
- Some corporate networks block browser downloads

**When to Use:**

- Modern web applications (React, Vue, Angular)
- Projects requiring cross-browser testing
- CI/CD pipelines (excellent headless support)
- When you need reliable, non-flaky automation
- iframe-heavy applications

**When NOT to Use:**

- Legacy browsers (IE11) required
- Very simple scripts where Puppeteer's speed matters
- Extremely resource-constrained environments

### Selenium (Mature and Stable)

**Official Site:** https://www.selenium.dev/

**Why Choose Selenium:**

- Most mature automation framework (20+ years)
- Largest community and ecosystem
- WebDriver W3C standard compliance
- Works with legacy browsers
- Extensive language bindings

**Installation:**

```bash
# Python
pip install selenium

# Download browser driver (ChromeDriver, GeckoDriver, etc.)
# Or use webdriver-manager for auto-download
pip install webdriver-manager
```

**Hello World Example:**

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Initialize driver
driver = webdriver.Chrome()

try:
    # Navigate
    driver.get('https://example.com/login')

    # Wait and fill (explicit waits required)
    wait = WebDriverWait(driver, 10)

    username = wait.until(EC.presence_of_element_located((By.ID, 'username')))
    username.send_keys('test@example.com')

    password = driver.find_element(By.ID, 'password')
    password.send_keys('password123')

    # Click button
    submit = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
    submit.click()

    # Wait for success
    wait.until(EC.url_contains('/dashboard'))

    print(f"Logged in! Current URL: {driver.current_url}")

finally:
    driver.quit()
```

**Advantages:**

- Massive community (most Stack Overflow answers)
- Works with IE11 and other legacy browsers
- WebDriver standard (portable across tools)
- Enterprise support available
- Selenium Grid for distributed testing
- Mature ecosystem (tools, plugins, libraries)

**Disadvantages:**

- No auto-waiting (must write explicit waits)
- Flaky tests without proper wait strategies
- Verbose API compared to Playwright
- WebDriver setup can be complex
- Slower than Playwright/Puppeteer

**When to Use:**

- Legacy browser support required (IE11, old Edge)
- Enterprise environments with WebDriver infrastructure
- When team already knows Selenium
- Distributed testing with Selenium Grid
- Compliance with WebDriver W3C standard

**When NOT to Use:**

- New projects (Playwright is better)
- Speed is critical (Puppeteer is faster)
- Complex iframe scenarios (Playwright is easier)

### Puppeteer (Fastest for Chrome)

**Official Site:** https://pptr.dev/

**Why Choose Puppeteer:**

- Officially maintained by Chrome team
- Fastest execution (direct CDP connection)
- Smallest API surface (easy to learn)
- Best Chrome DevTools Protocol access

**Installation:**

```bash
# Node.js only
npm install puppeteer
```

**Hello World Example:**

```javascript
const puppeteer = require('puppeteer');

(async () => {
  // Launch browser
  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();

  // Navigate
  await page.goto('https://example.com/login');

  // Fill form
  await page.type('#username', 'test@example.com');
  await page.type('#password', 'password123');

  // Click button and wait for navigation
  await Promise.all([
    page.waitForNavigation(),
    page.click('button[type="submit"]')
  ]);

  console.log(`Logged in! Current URL: ${page.url()}`);

  await browser.close();
})();
```

**Advantages:**

- Fastest execution speed
- Official Chrome support (Chrome team maintains it)
- Excellent screenshot/PDF generation
- Direct Chrome DevTools Protocol access
- Simple API (easy to learn)
- Node.js ecosystem integration

**Disadvantages:**

- Chrome/Chromium only (no Firefox, Safari)
- Node.js only (no Python, Java, etc.)
- Manual wait strategies required
- Smaller community than Selenium
- No built-in cross-browser testing

**When to Use:**

- Chrome-only projects
- Node.js backend/tooling
- Speed is critical (scraping, PDF generation)
- When you need cutting-edge Chrome features
- Headless Chrome automation

**When NOT to Use:**

- Need Firefox/Safari support
- Python/Java project
- Complex cross-browser requirements
- Team unfamiliar with JavaScript/Node.js

### MCP browser-controller (AI-Driven)

**Why Choose MCP browser-controller:**

- Designed for AI agent use
- Natural language interactions possible
- Easy subprocess invocation
- Built-in retry logic
- Claude Code integration

**Advantages:**

- AI-friendly interface
- Works with any language (subprocess calls)
- Built-in screenshot capabilities
- Simple for basic automation
- Claude Code integration

**Disadvantages:**

- No iframe context switching
- Very large screenshots (~5MB)
- Limited documentation
- Beta/experimental status
- Subprocess overhead (slower)
- Less control than Playwright/Selenium

**When to Use:**

- Claude Code projects
- AI-driven automation
- Simple automation tasks
- Prototyping/exploration
- When you want AI to write automation code

**When NOT to Use:**

- iframe-heavy applications
- Production-critical automation
- Need fine-grained control
- Speed is important
- Complex scenarios

### Direct HTTP/API Approach (Fastest)

**When to Use:**
Skip browser automation entirely if you can interact with APIs directly.

**Example: Form Submission via HTTP POST**

```python
import requests

# Instead of browser automation
response = requests.post(
    'https://example.com/api/login',
    json={'username': 'test@example.com', 'password': 'password123'},
    headers={'Content-Type': 'application/json'}
)

if response.status_code == 200:
    token = response.json()['token']
    print(f"Logged in! Token: {token}")
```

**Advantages:**

- 10-100x faster than browser
- No browser overhead (memory, CPU)
- Simple to implement
- Easy to debug (HTTP logs)
- No browser driver installation

**Disadvantages:**

- Doesn't work if JavaScript is required
- Can't handle client-side rendering
- May miss CSRF tokens or cookies
- Doesn't test actual user experience

**When to Use:**

- API-first applications
- Simple form submissions
- Background jobs / cron tasks
- When testing backend logic
- Performance critical operations

**When NOT to Use:**

- JavaScript-heavy SPAs (React, Vue)
- Complex authentication flows (OAuth, 2FA)
- Need to verify visual appearance
- Client-side validation required

## Performance Comparison

**Benchmark: Simple login flow (email -> password -> 2FA -> success)**

| Tool                       | Execution Time | Memory Usage | Setup Time       |
|:---------------------------|:---------------|:-------------|:-----------------|
| **Direct HTTP**            | 0.5s           | <10MB        | Instant          |
| **Puppeteer**              | 3-5s           | ~150MB       | ~1s (launch)     |
| **Playwright**             | 3-6s           | ~200MB       | ~1.5s (launch)   |
| **Selenium**               | 5-8s           | ~250MB       | ~2s (launch)     |
| **MCP browser-controller** | 10-15s         | ~200MB       | ~2s + subprocess |

*Note: Times include browser launch. Reusing browser context significantly improves speed.*

## Language-Specific Recommendations

### Python Projects

**1st choice:** Playwright (best API design)
**2nd choice:** Selenium (mature ecosystem)

### Node.js Projects

**1st choice:** Puppeteer (fastest, official Chrome support)
**2nd choice:** Playwright (if need cross-browser)

### Java/C# Projects

**1st choice:** Selenium (best Java/.NET support)
**2nd choice:** Playwright (.NET available)

### Any Language (via subprocess)

**1st choice:** MCP browser-controller (designed for subprocess)
**2nd choice:** Selenium (WebDriver protocol)

## Migration Paths

### From Selenium to Playwright

**Selenium:**

```python
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

wait = WebDriverWait(driver, 10)
element = wait.until(EC.presence_of_element_located((By.ID, 'username')))
element.send_keys('test@example.com')
```

**Playwright (equivalent):**

```python
# Auto-waits built-in!
page.fill('#username', 'test@example.com')
```

**Key differences:**

- Playwright auto-waits (no explicit WebDriverWait needed)
- Different iframe syntax (`frame_locator` vs `switch_to.frame`)
- Different selector syntax (CSS-based by default)

### From Puppeteer to Playwright

**Puppeteer:**

```javascript
await page.type('#username', 'test@example.com');
await page.click('button[type="submit"]');
```

**Playwright (equivalent):**

```javascript
await page.fill('#username', 'test@example.com');
await page.click('button[type="submit"]');
```

**Key differences:**

- Playwright supports multiple browsers (not just Chromium)
- Slightly different API naming
- Playwright has better auto-waiting

## Summary Recommendations

| Use Case                         | Recommended Tool       | Reason                               |
|:---------------------------------|:-----------------------|:-------------------------------------|
| **Modern web apps**              | Playwright             | Best reliability, iframe support     |
| **Chrome-only Node.js**          | Puppeteer              | Fastest, official Chrome support     |
| **Legacy browsers**              | Selenium               | Only option for IE11                 |
| **Enterprise/existing Selenium** | Selenium               | Mature ecosystem, don't rewrite      |
| **AI-driven automation**         | MCP browser-controller | Designed for AI agents               |
| **API-based tasks**              | Direct HTTP            | 100x faster, no browser needed       |
| **Learning automation**          | Playwright             | Best documentation, easiest to learn |
| **CI/CD pipelines**              | Playwright             | Excellent headless, fast, reliable   |

## Related Documentation

- [Investigation Workflow](investigation-workflow.md) - How to investigate regardless of tool
- [Element Selectors](element-selectors.md) - Selector strategies (applicable to all tools)
- [Code Patterns](code-patterns.md) - Implementation examples for each tool
- [Common Pitfalls](common-pitfalls.md) - Tool-agnostic mistakes to avoid
