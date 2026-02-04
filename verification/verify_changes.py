from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Read token
        try:
            with open("admin_token.txt", "r") as f:
                token = f.read().strip()
        except:
            token = ""
            print("Warning: admin_token.txt not found")

        try:
            # 1. Verify Snapshot Builder Header
            print("Verifying Snapshot Builder...")
            page.goto("http://localhost:8080/modules/Snapshot%20Builder.html")

            # Inject Token & Core URL
            if token:
                page.evaluate(f"localStorage.setItem('lyrn_admin_token', '{token}')")
            page.evaluate("localStorage.setItem('lyrn_core_url', 'http://localhost:8080')")
            page.reload()

            page.wait_for_selector("h1.panel-title", timeout=5000)

            # Check for new elements
            if page.is_visible("#snapshot-select"):
                print("Snapshot Select found.")
            else:
                print("ERROR: Snapshot Select NOT found.")

            if page.is_visible("button[onclick='rwiLoadFromDropdown()']"):
                print("Load Button found.")
            else:
                print("ERROR: Load Button NOT found.")

            # Note: Selector matching onclick content can be tricky if quotes differ
            # Just taking screenshot for visual confirm mostly, but let's try

            page.screenshot(path="verification/snapshot_builder.png")
            print("Snapshot Builder screenshot taken.")

            # 2. Verify Settings
            print("Verifying Settings...")
            page.goto("http://localhost:8080/modules/Settings.html")

            # Inject Token & Core URL
            if token:
                page.evaluate(f"localStorage.setItem('lyrn_admin_token', '{token}')")
            page.evaluate("localStorage.setItem('lyrn_core_url', 'http://localhost:8080')")
            page.reload()

            page.wait_for_selector("#worker-timeout-input", timeout=5000)

            # Check value (should be default 1800)
            # Wait a bit for async fetch
            time.sleep(1)
            timeout_val = page.input_value("#worker-timeout-input")
            print(f"Worker Timeout Value: {timeout_val}")

            page.screenshot(path="verification/settings.png")
            print("Settings screenshot taken.")

            # 3. Verify Chat Input History
            print("Verifying Chat Input History...")
            page.goto("http://localhost:8080/modules/Chat%20Interface.html")

            # Inject Token & Core URL & MOCK HISTORY
            if token:
                page.evaluate(f"localStorage.setItem('lyrn_admin_token', '{token}')")
            page.evaluate("localStorage.setItem('lyrn_core_url', 'http://localhost:8080')")
            page.evaluate("localStorage.setItem('lyrn_chat_input_history', JSON.stringify(['Command 2', 'Command 1']))")
            page.reload()

            page.wait_for_selector("#chat-input", timeout=5000)

            input_el = page.locator("#chat-input")

            # Now test Arrow Up (History should be loaded)
            input_el.click() # Ensure focus

            # Initial State: Empty
            print(f"Initial: '{input_el.input_value()}'")

            page.keyboard.press("ArrowUp")
            val1 = input_el.input_value()
            print(f"ArrowUp 1: {val1}") # Should be Command 2

            page.keyboard.press("ArrowUp")
            val2 = input_el.input_value()
            print(f"ArrowUp 2: {val2}") # Should be Command 1

            page.keyboard.press("ArrowDown")
            val3 = input_el.input_value()
            print(f"ArrowDown 1: {val3}") # Should be Command 2

            page.keyboard.press("ArrowDown")
            val4 = input_el.input_value()
            print(f"ArrowDown 2: {val4}") # Should be empty string

            page.screenshot(path="verification/chat_history.png")
            print("Chat History screenshot taken.")

        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="verification/error.png")

        browser.close()

if __name__ == "__main__":
    run()
