from playwright.sync_api import sync_playwright
import time
import os

def run_cuj(page):
    print("Navigating to Server Status dashboard...")
    page.goto("http://localhost:8080/modules/ServerStatus.html")
    page.wait_for_timeout(1500)

    print("Checking LLM Tab...")
    page.evaluate("switchTab('llm')")
    page.wait_for_timeout(1000)

    page.screenshot(path="/home/jules/verification/screenshots/server_status_llm.png")
    page.wait_for_timeout(500)

    print("Test complete.")

if __name__ == "__main__":
    os.makedirs("/home/jules/verification/videos", exist_ok=True)
    os.makedirs("/home/jules/verification/screenshots", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir="/home/jules/verification/videos",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        page.add_init_script("""
            window.addEventListener('load', () => {
                localStorage.setItem('lyrn_admin_token', 'mock');
                localStorage.setItem('lyrn_core_url', 'http://localhost:8080');
            });
        """)
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
