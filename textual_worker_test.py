#!/usr/bin/env python3
"""
Test script to verify the correct Textual worker pattern.
This demonstrates the fix for the run_worker argument passing issue.
"""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Static
from typing import List, Dict, Any
import time

class WorkerTestApp(App):
    """Test app for demonstrating correct worker usage."""
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Button("Test Worker with Args", id="test-btn")
        yield Static("Click the button to test worker with arguments", id="status")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press to test worker."""
        if event.button.id == "test-btn":
            # Test arguments to pass to worker
            server_names = ["server1", "server2", "server3"]
            platform_keys = ["platform1", "platform2"]
            
            # CORRECT WAY: Use lambda to capture arguments
            self.run_worker(
                lambda: self.test_worker(server_names, platform_keys),
                thread=True,
                exclusive=True
            )
    
    def test_worker(self, server_names: List[str], platform_keys: List[str]) -> Dict[str, Any]:
        """Worker function that receives arguments correctly."""
        try:
            # Simulate work
            total_work = len(server_names) * len(platform_keys)
            completed = 0
            
            self.call_from_thread(self.update_status, f"Processing {len(server_names)} servers...")
            
            for server in server_names:
                for platform in platform_keys:
                    # Simulate processing each combination
                    time.sleep(0.5)
                    completed += 1
                    progress_msg = f"Processing {server} on {platform} ({completed}/{total_work})"
                    self.call_from_thread(self.update_status, progress_msg)
            
            self.call_from_thread(self.update_status, "✓ All work completed successfully!")
            return {"success": True, "processed": completed}
            
        except Exception as e:
            self.call_from_thread(self.update_status, f"Error: {str(e)}")
            return {"error": str(e)}
    
    def update_status(self, message: str) -> None:
        """Update the status display."""
        status = self.query_one("#status", Static)
        status.update(message)

if __name__ == "__main__":
    app = WorkerTestApp()
    app.run()