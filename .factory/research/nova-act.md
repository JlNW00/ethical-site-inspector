# Nova Act SDK Research

## Overview
Amazon Nova Act is an AWS service for building AI agents that automate UI-based workflows in the browser. The Python SDK (`nova-act`) lets you combine natural language prompts with Python code to navigate websites, interact with elements, and extract data.

## Installation
```bash
pip install nova-act
# Latest: 3.1.263.0 (Feb 26, 2026)
# Requires: Python >= 3.10
# Optional: playwright install chrome (for Google Chrome, Chromium works too)
```

## Authentication
Two methods:
1. **API Key**: Get from https://nova.amazon.com/act, set `NOVA_ACT_API_KEY` env var
2. **IAM Auth** (our method): Use AWS credentials via boto3. Uses `Workflow` class with `workflow_definition_name` and `model_id`.

For IAM auth, the SDK instantiates a default boto3 session if AWS credentials are configured in environment.

## Core API

### NovaAct Constructor
```python
from nova_act import NovaAct

nova = NovaAct(
    starting_page="https://example.com",  # Required: URL to start at
    headless=True,           # Run without visible browser
    tty=False,               # Disable interactive terminal output
    timeout=300,             # Session timeout in seconds
    record_video=True,       # Record video of session
    logs_directory="./logs", # Where to save logs/videos
    nova_act_api_key="...",  # API key (or set env var)
    user_agent="...",        # Custom user agent
    proxy={...},             # Proxy config
    tools=[...],             # Custom tools
    human_input_callbacks=..., # HITL callbacks
)
```

### Context Manager Usage (preferred)
```python
with NovaAct(starting_page="https://example.com") as nova:
    nova.act("Click the login button")
    result = nova.act_get("What is the page title?")
    print(result.response)
```

### Manual Start/Stop
```python
nova = NovaAct(starting_page="https://example.com")
nova.start()
nova.act("Do something")
nova.stop()
```

### act() - Perform browser actions
```python
result = nova.act(
    "Click the 'Accept All' cookie button",
    max_steps=30,      # Max browser actuations (default 30)
    timeout=120,        # Timeout in seconds
    observation_delay_ms=500,  # Wait for animations
)
# Returns ActResult with metadata (session_id, num_steps, timing)
```

### act_get() - Extract data from page
```python
from pydantic import BaseModel

class PriceData(BaseModel):
    original_price: float
    displayed_price: float
    hidden_fees: list[str]

result = nova.act_get(
    "Extract all prices shown on this checkout page, including any hidden fees",
    schema=PriceData.model_json_schema(),
)
# Returns ActGetResult with .response (str) and .parsed_response (JSON)
price_data = PriceData.model_validate(result.parsed_response)
```

### BOOL_SCHEMA for yes/no checks
```python
from nova_act import BOOL_SCHEMA
result = nova.act_get("Is there a cookie consent banner visible?", schema=BOOL_SCHEMA)
if result.parsed_response:
    print("Cookie banner found!")
```

### Access Playwright Page directly
```python
screenshot_bytes = nova.page.screenshot()
dom_string = nova.page.content()
nova.page.keyboard.type("hello")
```

## Workflow API (IAM Auth)
```python
from nova_act import NovaAct, Workflow

with Workflow(
    workflow_definition_name="ethical-site-inspector",
    model_id="nova-act-latest"
) as workflow:
    with NovaAct(
        starting_page="https://example.com",
        workflow=workflow,
    ) as nova:
        nova.act("...")
```

## Prompting Best Practices
1. **Be direct and succinct** - not "Let's see what's here" but "Navigate to the pricing page"
2. **Provide complete instructions** - specify exact actions, values, stopping conditions
3. **Break large tasks into smaller acts** - each act should be <30 steps
4. **Add hints when needed** - tell the agent about tricky UI elements
5. **Use schemas for extraction** - always use act_get with Pydantic schemas for structured data

## Data Extraction
```python
from nova_act import NovaAct, STRING_SCHEMA
# STRING_SCHEMA is the default for act_get()
result = nova.act_get("What is the total price shown?")
print(result.response)  # String response

# For structured data, use Pydantic models
result = nova.act_get("...", schema=MyModel.model_json_schema())
data = MyModel.model_validate(result.parsed_response)
```

## Parallel Sessions
```python
from concurrent.futures import ThreadPoolExecutor

def run_audit(url, persona):
    with NovaAct(starting_page=url) as nova:
        nova.act(f"Browse as a {persona} user...")
        return nova.act_get("Extract findings...")

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(run_audit, url, "privacy_sensitive"),
        executor.submit(run_audit, url, "cost_sensitive"),
        executor.submit(run_audit, url, "exit_intent"),
    ]
```

## Recording Sessions
```python
with NovaAct(
    starting_page="https://example.com",
    record_video=True,
    logs_directory="./audit_recordings"
) as nova:
    nova.act("...")
# Video saved to logs_directory
```

## Key Limitations
- English only
- Best under 30 steps per act() call
- Single-threaded per session (but multiple sessions can run in parallel threads)
- First run may take 1-2 minutes (installs Playwright modules)
- May encounter CAPTCHAs on some sites
- Not supported with ipython
- SSL validation enforced on all page navigations

## For Dark Pattern Detection
Key capabilities for our use case:
- `act()` to navigate cookie consent flows, checkout processes, cancellation flows
- `act_get()` with schemas to extract: button text/size/color, price breakdowns, hidden fees, checkbox states
- `nova.page.screenshot()` for evidence capture at each step
- `nova.page.content()` for DOM snapshots
- Parallel sessions for testing different personas against the same site
- HITL for CAPTCHA handling if needed

## Example: Cookie Consent Audit
```python
with NovaAct(starting_page=target_url, headless=True) as nova:
    # Check for cookie banner
    has_banner = nova.act_get("Is there a cookie consent banner?", schema=BOOL_SCHEMA)
    if has_banner.parsed_response:
        # Screenshot the initial state
        evidence_before = nova.page.screenshot()
        
        # Try to reject cookies
        nova.act("Try to reject all cookies or select only necessary cookies")
        evidence_after = nova.page.screenshot()
        
        # Extract what happened
        result = nova.act_get(
            "Describe: Was rejecting cookies straightforward? "
            "How many clicks were needed compared to accepting? "
            "Were dark patterns used (hidden reject, confusing language, guilt-tripping)?",
            schema=CookieConsentAnalysis.model_json_schema()
        )
```
