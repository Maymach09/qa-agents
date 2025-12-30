import json
from pathlib import Path
from typing import Dict
from playwright.async_api import async_playwright, Page
from langchain_core.tools import tool
import asyncio
from datetime import datetime
from subprocess import run, PIPE

# ---- GLOBAL BROWSER SESSION (single session, async) ----
_playwright = None
_browser = None
_context = None
_page: Page | None = None
_page_lock = asyncio.Lock()  # Lock to prevent concurrent page operations

async def _get_page() -> Page:
    global _playwright, _browser, _context, _page
    if _page is None:
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=False)
        # Use the saved Salesforce session for authentication
        try:
            _context = await _browser.new_context(storage_state="auth_state.json")
        except Exception as e:
            print(f"Warning: Could not load auth_state.json: {e}")
            print("Creating new context without saved session")
            _context = await _browser.new_context()
        _page = await _context.new_page()
    return _page



@tool
async def browser_navigate(url: str) -> str:
    """Navigate to a URL"""
    async with _page_lock:
        page = await _get_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return f"Navigated to {url}"



@tool
async def browser_wait(seconds: int = 2) -> str:
    """Wait for page to stabilize"""
    page = await _get_page()
    await page.wait_for_timeout(seconds * 5000)
    return f"Waited {seconds} seconds"



@tool
async def browser_click(selector: str) -> str:
    """Click an element using a stable selector"""
    page = await _get_page()
    await page.locator(selector).first.click()
    return f"Clicked element: {selector}"



@tool
async def browser_fill(selector: str, value: str) -> str:
    """Fill input field"""
    page = await _get_page()
    await page.locator(selector).first.fill(value)
    return f"Filled {selector} with value"



@tool
async def browser_snapshot(page_name: str) -> dict:
    """
    Capture AX tree and convert it into an action-oriented JSON
    usable for Playwright test generation.
    """
    async with _page_lock:
        page = await _get_page()

        client = await page.context.new_cdp_session(page)
        ax_tree = await client.send("Accessibility.getFullAXTree")

        INTERACTIVE_ROLES = {
            "button",
            "textbox",
            "link",
            "combobox",
            "checkbox",
            "radio",
            "menuitem"
        }

        actions = []
        ref_counter = 1

        for node in ax_tree["nodes"]:
            role = node.get("role", {}).get("value")
            name = node.get("name", {}).get("value")

            if not role or role not in INTERACTIVE_ROLES:
                continue

            if not name or not name.strip():
                continue

            ref = f"e{ref_counter}"
            ref_counter += 1

            locator = (
                f"page.getByRole('{role}', {{ name: '{name}' }})"
            )

            actions.append({
                "role": role,
                "label": name,
                "ref": ref,
                "locator": locator,
                "fallback_locators": []
            })

        # Page type inference
        lower_name = page_name.lower()
        if any(k in lower_name for k in ["new", "edit", "create", "form"]):
            page_type = "form_page"
        elif any(k in lower_name for k in ["list", "view"]):
            page_type = "list_view"
        else:
            page_type = "general_page"

        snapshot = {
            "url": page.url,
            "page_name": page_name,
            "page_type": page_type,
            "actions": actions
        }

        output_dir = Path("output/snapshots")
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_page_name = page_name.replace(" ", "_").replace("/", "_")
        file_path = output_dir / f"{safe_page_name}_{timestamp}.json"
        file_path.write_text(json.dumps(snapshot, indent=2))

        return {
            "page": page_name,
            "actions_captured": len(actions),
            "file": str(file_path)
        }



@tool
async def browser_drag(source_selector: str, target_selector: str) -> str:
    """Drag an element from source_selector to target_selector."""
    page = await _get_page()
    source = page.locator(source_selector).first
    target = page.locator(target_selector).first
    await source.drag_to(target)
    return f"Dragged from {source_selector} to {target_selector}"


@tool
async def browser_evaluate(script: str) -> str:
    """Evaluate JavaScript in the page context."""
    page = await _get_page()
    result = await page.evaluate(script)
    return f"Evaluated script. Result: {result}"


@tool
async def browser_file_upload(selector: str, file_path: str) -> str:
    """Upload a file to an input element."""
    page = await _get_page()
    await page.set_input_files(selector, file_path)
    return f"Uploaded file {file_path} to {selector}"


@tool
async def browser_handle_dialog(action: str = "accept", prompt_text: str = None) -> str:
    """Handle browser dialogs (alert, confirm, prompt)."""
    page = await _get_page()
    async def dialog_handler(dialog):
        if action == "accept":
            await dialog.accept(prompt_text) if prompt_text else await dialog.accept()
        else:
            await dialog.dismiss()
    page.once("dialog", dialog_handler)
    return f"Dialog will be handled with action: {action}"


@tool
async def browser_hover(selector: str) -> str:
    """Hover over an element."""
    page = await _get_page()
    await page.locator(selector).first.hover()
    return f"Hovered over {selector}"


@tool
async def browser_press_key(selector: str, key: str) -> str:
    """Press a key on an element."""
    page = await _get_page()
    await page.locator(selector).first.press(key)
    return f"Pressed key {key} on {selector}"


@tool
async def browser_select_option(selector: str, value: str) -> str:
    """Select an option in a dropdown."""
    page = await _get_page()
    await page.locator(selector).first.select_option(value)
    return f"Selected option {value} in {selector}"


@tool
async def browser_type(selector: str, text: str) -> str:
    """Type text into an element (character by character)."""
    page = await _get_page()
    await page.locator(selector).first.type(text)
    return f"Typed '{text}' into {selector}"


@tool
async def browser_verify_element_visible(selector: str) -> str:
    """Verify that an element is visible."""
    page = await _get_page()
    visible = await page.locator(selector).first.is_visible()
    assert visible, f"Element {selector} is not visible"
    return f"Element {selector} is visible"


@tool
async def browser_verify_list_visible(selector: str) -> str:
    """Verify that a list of elements is visible (at least one)."""
    page = await _get_page()
    count = await page.locator(selector).count()
    assert count > 0, f"No elements found for {selector}"
    for i in range(count):
        assert await page.locator(selector).nth(i).is_visible(), f"Element {selector}[{i}] is not visible"
    return f"All elements for {selector} are visible"


@tool
async def browser_verify_text_visible(selector: str, expected: str) -> str:
    """Verify that the element's text matches expected value."""
    page = await _get_page()
    text = await page.locator(selector).first.text_content()
    assert text and expected in text, f"Expected '{expected}' in '{text}'"
    return f"Text '{expected}' is visible in {selector}"


@tool
async def browser_verify_value(selector: str, expected: str) -> str:
    """Verify that the element's value matches expected value."""
    page = await _get_page()
    value = await page.locator(selector).first.input_value()
    assert value == expected, f"Expected value '{expected}', got '{value}'"
    return f"Value '{expected}' is present in {selector}"


@tool
async def browser_wait_for(selector: str, timeout: int = 5000) -> str:
    """Wait for an element to be visible within timeout (ms)."""
    page = await _get_page()
    await page.locator(selector).first.wait_for(state="visible", timeout=timeout)
    return f"Waited for {selector} to be visible"


@tool
async def browser_close() -> str:
    """Close browser session"""
    global _playwright, _browser, _context, _page
    try:
        if _browser:
            await _browser.close()
        if _playwright:
            await _playwright.stop()
    finally:
        _playwright = _browser = _context = _page = None
    return "Browser closed"


@tool
async def playwright_run_test_headed(script_name: str) -> dict:
    """
    Run a Playwright test script in headed mode and return the result, error output, and (if failed) a screenshot path.
    script_name: Name of the test script file (e.g., 'TC-001.spec.ts')
    """
    import os
    import time
    from pathlib import Path
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    script_path = Path("tests") / script_name
    if not script_path.exists():
        return {"error": f"Script {script_name} not found."}
    screenshot_dir = Path("output/headed_screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = screenshot_dir / f"{script_name}_{timestamp}.png"
    # Run Playwright test in headed mode, capture output
    cmd = [
        "npx", "playwright", "test", str(script_path),
        "--project=chromium",
        "--headed",
        f"--output={screenshot_dir}",
        "--timeout=60000"
    ]
    result = run(cmd, stdout=PIPE, stderr=PIPE, text=True)
    # Find screenshot if any
    screenshots = list(screenshot_dir.glob(f"**/{script_path.stem}*.png"))
    screenshot_file = str(screenshots[0]) if screenshots else None
    return {
        "script": script_name,
        "returncode": result.returncode,
        "stdout": result.stdout[-2000:],
        "stderr": result.stderr[-2000:],
        "screenshot": screenshot_file
    }

@tool
def playwright_run_all_tests() -> dict:
    """
    Run all Playwright tests using JSON reporter and return structured results.
    """
    cmd = [
        "npx",
        "playwright",
        "test",
        "--reporter=json"
    ]
    result = run(cmd, stdout=PIPE, stderr=PIPE, text=True)

    if result.returncode != 0 and not result.stdout:
        return {
            "error": "Playwright execution failed",
            "stderr": result.stderr[-2000:]
        }

    try:
        return json.loads(result.stdout)
    except Exception as e:
        return {
            "error": "Failed to parse Playwright JSON output",
            "exception": str(e),
            "raw": result.stdout[-2000:]
        }
    
@tool
async def playwright_analyze_failure(script_name: str, test_title: str | None = None) -> dict:
    """
    Automatically analyze a failing test by running it in headed mode,
    capturing errors, screenshots, and page state at failure point.
    Returns comprehensive diagnostic information.
    """
    from pathlib import Path
    import time
    import json
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = Path("output/failure_analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run test in headed mode with detailed output
    cmd = [
        "npx",
        "playwright",
        "test",
        f"tests/{script_name}",
        "--project=chromium",
        "--headed",
        "--reporter=json",
        "--max-failures=1",
        "--timeout=30000"
    ]
    
    if test_title:
        cmd.extend(["-g", test_title])
    
    result = run(cmd, stdout=PIPE, stderr=PIPE, text=True)
    
    # Parse JSON output
    try:
        test_results = json.loads(result.stdout) if result.stdout else {}
    except:
        test_results = {"error": "Failed to parse test output", "raw": result.stdout[:1000]}
    
    # Extract failure details
    failure_info = {
        "script_name": script_name,
        "test_title": test_title,
        "timestamp": timestamp,
        "returncode": result.returncode,
        "test_results": test_results,
        "stderr": result.stderr[-2000:] if result.stderr else ""
    }
    
    # Try to extract specific error details from test results
    if "suites" in test_results:
        for suite in test_results["suites"]:
            for spec in suite.get("specs", []):
                for test in spec.get("tests", []):
                    for result_item in test.get("results", []):
                        if result_item.get("status") == "failed":
                            failure_info["error_message"] = result_item.get("error", {}).get("message", "")
                            failure_info["error_stack"] = result_item.get("error", {}).get("stack", "")
                            
                            # Get attachments (screenshots, traces)
                            attachments = result_item.get("attachments", [])
                            failure_info["screenshots"] = [
                                att.get("path") for att in attachments 
                                if att.get("name") == "screenshot"
                            ]
    
    # Try to capture current page state if browser is still open
    try:
        if _page:
            snapshot_result = await browser_snapshot(f"FAILURE_{script_name}_{timestamp}")
            failure_info["snapshot"] = snapshot_result
    except:
        failure_info["snapshot"] = "Could not capture page snapshot"
    
    # Save analysis report
    report_path = output_dir / f"analysis_{script_name}_{timestamp}.json"
    report_path.write_text(json.dumps(failure_info, indent=2))
    
    failure_info["analysis_report_path"] = str(report_path)
    
    return failure_info

@tool
async def browser_failure_snapshot(test_name: str) -> dict:
    """
    Capture snapshot at failure point for advanced debugging.
    DOES NOT call other tools (LangChain limitation).
    """
    async with _page_lock:
        page = await _get_page()

        client = await page.context.new_cdp_session(page)
        ax_tree = await client.send("Accessibility.getFullAXTree")

        INTERACTIVE_ROLES = {
            "button",
            "textbox",
            "link",
            "combobox",
            "checkbox",
            "radio",
            "menuitem"
        }

        actions = []
        ref_counter = 1

        for node in ax_tree["nodes"]:
            role = node.get("role", {}).get("value")
            name = node.get("name", {}).get("value")

            if not role or role not in INTERACTIVE_ROLES:
                continue
            if not name or not name.strip():
                continue

            locator = f"page.getByRole('{role}', {{ name: '{name}' }})"

            actions.append({
                "role": role,
                "label": name,
                "ref": f"e{ref_counter}",
                "locator": locator,
                "fallback_locators": []
            })
            ref_counter += 1

        snapshot = {
            "url": page.url,
            "page_name": f"FAIL_{test_name}",
            "page_type": "failure_page",
            "actions": actions
        }

        output_dir = Path("output/snapshots")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = test_name.replace(" ", "_").replace("/", "_")
        file_path = output_dir / f"FAIL_{safe_name}_{timestamp}.json"

        file_path.write_text(json.dumps(snapshot, indent=2))

        return {
            "test": test_name,
            "snapshot_file": str(file_path),
            "actions_captured": len(actions),
            "captured_at": datetime.now().isoformat()
        }

@tool
def update_test_script(script_name: str, updated_content: str) -> str:
    """
    Overwrite an existing Playwright test script safely.
    """
    script_path = Path("tests") / script_name

    if not script_path.exists():
        return f"ERROR: Script {script_name} not found."

    # Basic safety check
    if "test(" not in updated_content or "import" not in updated_content:
        return "ERROR: Invalid test content detected. Update aborted."

    script_path.write_text(updated_content)
    return f"Updated test script: {script_name}"