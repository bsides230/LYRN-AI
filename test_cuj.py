from playwright.sync_api import sync_playwright
import time
import os

def run_cuj(page):
    print("Navigating to LYRN dashboard...")
    page.goto("http://localhost:8080/modules/ClaudeCode.html")
    page.wait_for_timeout(1500)

    print("Testing Claude Code UI Elements...")
    # Mock some run items
    page.evaluate("""
        const list = document.getElementById('run-list');
        list.innerHTML = `
            <div class="run-item">
                <div class="row">
                    <span class="label">run_test_123</span>
                    <span class="run-status completed">completed</span>
                </div>
                <div class="meta">oneshot · diff · ✓ approved</div>
            </div>
        `;
    """)
    page.wait_for_timeout(1000)

    print("Checking UI...")
    page.screenshot(path="/home/jules/verification/screenshots/claude_code.png")
    page.wait_for_timeout(1000)

    # Done
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
        # Mock token to bypass fetch issues
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
