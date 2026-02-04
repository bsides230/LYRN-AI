import os
import time
import subprocess
from playwright.sync_api import sync_playwright

def verify_dashboard():
    # Start a simple HTTP server
    server = subprocess.Popen(["python3", "-m", "http.server", "8081"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Started HTTP server on port 8081")
    time.sleep(2)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 720})

            # 1. Load Dashboard
            url = "http://localhost:8081/LYRN_v5/dashboard.html"
            print(f"Navigating to {url}")
            page.goto(url)

            # Dismiss Welcome/Connection Popups if they appear
            try:
                # Connection Popup
                if page.is_visible("#connection-popup", timeout=2000):
                    print("Dismissing Connection Popup...")
                    page.click("#connection-popup .win-btn") # Close button
                    time.sleep(0.5)

                # Welcome Popup
                if page.is_visible("#welcome-popup", timeout=2000):
                    print("Dismissing Welcome Popup...")
                    page.click("#welcome-popup .win-btn")
                    time.sleep(0.5)
            except Exception as e:
                print(f"Popup handling error (might be fine): {e}")

            # Wait for dock to render
            page.wait_for_selector("#floating-dock")

            # 2. Click Settings Button
            print("Clicking Settings button...")
            page.click("#btn_settings")
            time.sleep(1) # Animation

            # 3. Screenshot General Tab
            print("Screenshotting General Settings...")
            page.screenshot(path="verification/settings_general.png")

            # 4. Switch to Layouts Tab
            print("Switching to Layouts tab...")
            page.click("button.tab-btn:has-text('Layouts')")
            time.sleep(0.5)

            # 5. Screenshot Layouts Tab
            print("Screenshotting Layouts Settings...")
            page.screenshot(path="verification/settings_layouts.png")

            # 6. Test Window Resize Constraint
            # Open a window first
            print("Opening Chat window...")
            page.click("#btn_mod_chat")
            time.sleep(1)

            # Move window to bottom right edge
            print("Moving window to edge...")
            # page.evaluate logic to move window
            page.evaluate("""() => {
                const win = document.getElementById('win_mod_chat');
                if(win) {
                    win.style.left = '1200px';
                    win.style.top = '600px';
                }
            }""")

            page.screenshot(path="verification/window_edge.png")

            # Resize viewport to be smaller
            print("Resizing viewport...")
            page.set_viewport_size({"width": 800, "height": 600})
            time.sleep(1) # Wait for resize event handler

            # Take screenshot to see if it moved back
            print("Screenshotting after resize...")
            page.screenshot(path="verification/window_constrained.png")

            browser.close()
    finally:
        server.terminate()
        print("Server stopped")

if __name__ == "__main__":
    verify_dashboard()
