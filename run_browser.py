#!/usr/bin/env python3
"""
VideoGen Project Browser Launcher
Run this script to start the Gradio web interface for browsing and editing video generation projects.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from gradio_project_browser import create_interface

if __name__ == "__main__":
    print("Starting VideoGen Project Browser...")
    print("The interface will be available at: http://localhost:7860")
    print("Press Ctrl+C to stop the server")
    
    try:
        interface = create_interface()
        interface.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            show_error=True,
            inbrowser=True
        )
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)
