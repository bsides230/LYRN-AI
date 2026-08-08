from playwright.sync_api import sync_playwright

def run_cuj(page):
    # Using file path
    import os
    file_path = f"file://{os.path.abspath('LYRN_v6/modules/DeltaManager.html')}"
    page.goto(file_path)
    page.evaluate("localStorage.setItem('lyrn_admin_token', 'lyrn')")
    page.evaluate("localStorage.setItem('lyrn_core_url', 'http://localhost:8080')")
    page.evaluate("localStorage.setItem('lyrn_theme', 'dark')")

    # Reload to apply token
    page.goto(file_path)
    page.wait_for_timeout(1000)

    # Fill form
    page.locator("#inp-name").fill("My Cool Delta")
    page.wait_for_timeout(500)
    page.locator("#inp-script").fill("echo 'this is a delta test'")
    page.wait_for_timeout(500)
    page.locator("#inp-update-time").fill("5m")
    page.wait_for_timeout(500)
    page.locator("#inp-notes").fill("Testing delta manager")
    page.wait_for_timeout(500)

    # Save
    page.locator("text=Save Delta").click()
    page.wait_for_timeout(1000)

    # Take screenshot
    page.screenshot(path="verification.png")
    page.wait_for_timeout(1000)

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir="/home/jules/verification/videos",
            viewport={'width': 1280, 'height': 720}
        )
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
