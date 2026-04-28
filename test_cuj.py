from playwright.sync_api import sync_playwright
import os

def run_cuj(page):
    # Navigate to the local file using file://
    file_path = f"file://{os.path.abspath('LYRN_v6/dashboard.html')}"
    page.goto(file_path)
    page.wait_for_timeout(1000)

    # Bypass auth and welcome popup via localStorage
    page.evaluate("localStorage.setItem('lyrn_admin_token', 'lyrn')")
    page.evaluate("localStorage.setItem('lyrn_core_url', 'http://localhost:8080')")
    page.evaluate("localStorage.setItem('lyrn-welcome-hidden', 'true')")
    page.evaluate("localStorage.setItem('lyrn-conn-hidden', 'true')")

    # Ensure mod_job_mgr is active
    settings = page.evaluate("localStorage.getItem('lyrn-settings') || '{}'")
    import json
    settings_obj = json.loads(settings)
    if 'activeModules' not in settings_obj:
        settings_obj['activeModules'] = ['mod_chat', 'mod_claude_code', 'mod_builder', 'mod_file_tree', 'mod_models', 'mod_model_manager', 'mod_logs', 'mod_server_status', 'mod_job_mgr']
    elif 'mod_job_mgr' not in settings_obj['activeModules']:
        settings_obj['activeModules'].append('mod_job_mgr')
    page.evaluate(f"localStorage.setItem('lyrn-settings', '{json.dumps(settings_obj)}')")

    page.reload()
    page.wait_for_timeout(1000)

    # Click the Job Manager icon in the dock to open the window
    page.locator("#btn_mod_job_mgr").click()
    page.wait_for_timeout(2000)

    # Switch to the Job Manager iframe
    frame = page.frame_locator("#win_mod_job_mgr iframe")

    # The settings button doesn't work locally without a valid token and server responding correctly
    # Let's bypass Settings completely and focus on the UI flow: Database Overlay

    # Click "Database" in the iframe toolbar
    frame.get_by_role("button", name="Database").click()
    page.wait_for_timeout(1000)

    # Click "Edit" in the database overlay
    frame.locator("#dbEditBtn").click()
    page.wait_for_timeout(1000)

    # Click "Done" (was Edit)
    frame.locator("#dbEditBtn").click()
    page.wait_for_timeout(500)

    # Take screenshot at the final state
    page.screenshot(path="/home/jules/verification/screenshots/verification.png")
    page.wait_for_timeout(1000)

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
