#!/usr/bin/env python3
"""
LeetLoop Application Launcher
This is the main entry point when running the bundled executable.
It handles:
- First-time setup (.env configuration)
- Starting the background service
- Opening the browser to the app
"""

import os
import sys
import time
import webbrowser
from pathlib import Path
from dotenv import load_dotenv

# Add src to path so we can import run_service
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from run_service import (
    load_app_config,
    port_is_open,
    server_is_running,
    stop_recorded_agent,
    spawn_background_agent,
    wait_for_server,
    server_url,
    run_server,
)


def setup_env_first_run():
    """Interactive setup for first-time users."""
    env_file = PROJECT_ROOT / ".env"
    
    if env_file.exists():
        return  # Already set up
    
    print()
    print("=" * 60)
    print("LeetLoop - First Time Setup")
    print("=" * 60)
    print()
    print("We need your OpenAI API key to generate study plans.")
    print("Get one at: https://platform.openai.com/api-keys")
    print()
    
    openai_key = input("Enter your OpenAI API key: ").strip()
    
    if not openai_key:
        print("\n✗ Setup cancelled - API key required")
        sys.exit(1)
    
    # Create .env file
    env_content = f"OPENAI_API_KEY={openai_key}\n"
    env_file.write_text(env_content)
    
    print()
    print("✓ Setup complete! Configuration saved to .env")
    print()


def main():
    """Main launcher entry point."""
    
    # Change to project root
    os.chdir(str(PROJECT_ROOT))
    
    # Setup on first run
    setup_env_first_run()
    
    # Load environment
    load_dotenv(PROJECT_ROOT / ".env")
    
    config = load_app_config()
    url = server_url(config)
    
    print()
    print("=" * 60)
    print("LeetLoop")
    print("=" * 60)
    print()
    
    # Check if server is already running
    if server_is_running(config):
        print("✓ LeetLoop is already running")
        print(f"  Opening: {url}")
        webbrowser.open(url)
        return
    
    # Stop any stale processes
    if port_is_open(config):
        print("Stopping stale background service...")
        stop_recorded_agent()
        time.sleep(2)
    
    # Start the background service
    print("Starting LeetLoop background service...")
    spawn_background_agent()
    
    # Wait for server to start
    if wait_for_server():
        print("✓ Service started successfully")
        print(f"  Opening: {url}")
        webbrowser.open(url)
        
        # Keep launcher alive so app stays running
        print()
        print("LeetLoop is running in the background.")
        print("Close this window when you're done, or press Ctrl+C.")
        print()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down LeetLoop...")
            stop_recorded_agent()
            sys.exit(0)
    else:
        print("✗ Failed to start LeetLoop service")
        sys.exit(1)


if __name__ == "__main__":
    main()
