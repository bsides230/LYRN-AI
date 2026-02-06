import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("==========================================")
    print("       UNIVERSAL SERVER SETUP WIZARD")
    print("==========================================")
    print()

def get_os_type():
    system = platform.system().lower()
    if "termux" in os.environ.get("PREFIX", "") or "ANDROID_ROOT" in os.environ:
        return "android"
    if system == "windows": return "windows"
    if system == "linux": return "linux"
    if system == "darwin": return "mac"
    return "unknown"

def install_dependencies():
    print("\n--- Installing Dependencies ---")
    try:
        # Ensure requirements.txt uses nvidia-ml-py
        req_path = Path("requirements.txt")
        if req_path.exists():
            content = req_path.read_text()
            if "pynvml" in content and "nvidia-ml-py" not in content:
                print("Updating requirements.txt to use nvidia-ml-py...")
                content = content.replace("pynvml", "nvidia-ml-py")
                req_path.write_text(content)

        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed successfully.")
    except Exception as e:
        print(f"Error installing dependencies: {e}")
    input("Press Enter to continue...")

def install_tailscale(os_type):
    print("\n--- Installing Tailscale ---")
    if os_type == "windows":
        print("On Windows, please download Tailscale from https://tailscale.com/download/windows")
    elif os_type == "mac":
        print("On macOS, please download Tailscale from the App Store or https://tailscale.com/download/mac")
    elif os_type == "android":
        print("On Android, please install the Tailscale app from the Play Store.")
    else: # Linux
        print("Attempting to install Tailscale using the official install script.")
        try:
            cmd = "curl -fsSL https://tailscale.com/install.sh | sh"
            subprocess.check_call(cmd, shell=True)
            print("\nTailscale installation script completed.")
            print("You may need to run 'sudo tailscale up' to connect.")
        except Exception as e:
            print(f"Error installing Tailscale: {e}")
    input("Press Enter to continue...")

def setup_app(app_name, app_dir, default_port):
    print(f"\n--- Setup {app_name} ---")
    app_path = Path(app_dir)
    app_path.mkdir(exist_ok=True)

    # 1. Port
    current_port = default_port
    port_file = app_path / "port.txt"
    if port_file.exists():
        current_port = port_file.read_text().strip()

    print(f"Current Port: {current_port}")
    choice = input(f"Change port for {app_name}? (Y/N): ").strip().upper()
    if choice == 'Y':
        new_port = input("Enter new port: ").strip()
        if new_port.isdigit():
            port_file.write_text(new_port)
            print("Port updated.")
        else:
            print("Invalid port. Keeping current.")

    # 2. Token
    token_file = app_path / "admin_token.txt"
    if not token_file.exists():
        print("Generating Admin Token...")
        try:
            # Run token generator in app dir
            subprocess.check_call([sys.executable, "../token_generator.py"], cwd=app_path)
        except Exception as e:
            print(f"Error generating token: {e}")
    else:
        print("Admin Token already exists.")
        if input("Regenerate Token? (Y/N): ").strip().upper() == 'Y':
             try:
                subprocess.check_call([sys.executable, "../token_generator.py"], cwd=app_path)
             except Exception as e:
                print(f"Error: {e}")

    print(f"\n{app_name} Setup Complete.")
    input("Press Enter to continue...")

def main():
    os_type = get_os_type()
    while True:
        clear_screen()
        print_header()
        print(f"Detected System: {os_type.upper()}")
        print()
        print("1. Install Dependencies")
        print("2. Install Tailscale")
        print("3. Setup LYRN (Chat/AI)")
        print("4. Setup RemoDash (Control)")
        print("Q. Quit")
        print()

        choice = input("Select an option: ").strip().upper()

        if choice == '1':
            install_dependencies()
        elif choice == '2':
            install_tailscale(os_type)
        elif choice == '3':
            setup_app("LYRN", "LYRN_v5", "8240")
        elif choice == '4':
            setup_app("RemoDash", "RemoDash", "8000")
        elif choice == 'Q':
            break

if __name__ == "__main__":
    main()
