from playwright.sync_api import sync_playwright
import time
import os

def run_cuj(page):
    print("Navigating to Model Manager dashboard...")
    # Add token before navigating
    page.goto("http://localhost:8080/modules/ModelManager.html")
    page.wait_for_timeout(1500)

    # We must inject token then reload so init script picks it up correctly if the listener fired too late
    page.evaluate("localStorage.setItem('lyrn_admin_token', 'mock'); localStorage.setItem('lyrn_core_url', 'http://localhost:8080');")
    page.reload()
    page.wait_for_timeout(1500)

    print("Clicking favorites button...")
    page.evaluate("toggleFavorites()")
    page.wait_for_timeout(1500)

    page.screenshot(path="/home/jules/verification/screenshots/model_manager_favorites.png")
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
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
