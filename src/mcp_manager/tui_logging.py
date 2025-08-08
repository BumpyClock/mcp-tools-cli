"""TUI-specific logging system that doesn't interfere with the interactive interface."""

import logging
import structlog
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from collections import deque
import threading
import time


class TUILogHandler(logging.Handler):
    """Custom logging handler for TUI that collects messages without displaying them immediately."""
    
    def __init__(self, max_messages: int = 100):
        super().__init__()
        self.messages = deque(maxlen=max_messages)
        self._lock = threading.Lock()
    
    def emit(self, record):
        """Collect log record without displaying it."""
        try:
            msg = self.format(record)
            timestamp = time.strftime('%H:%M:%S')
            
            with self._lock:
                self.messages.append({
                    'timestamp': timestamp,
                    'level': record.levelname,
                    'message': msg,
                    'raw_record': record
                })
        except Exception:
            self.handleError(record)
    
    def get_recent_messages(self, count: Optional[int] = None) -> List[dict]:
        """Get recent log messages."""
        with self._lock:
            if count is None:
                return list(self.messages)
            else:
                return list(self.messages)[-count:]
    
    def clear_messages(self):
        """Clear all stored messages."""
        with self._lock:
            self.messages.clear()


class TUILogger:
    """Logging manager for TUI applications."""
    
    def __init__(self, console: Console):
        self.console = console
        self.handler = TUILogHandler()
        self.debug_visible = False
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging for TUI mode."""
        # Configure structlog for TUI
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                # Use a simple renderer for TUI
                structlog.processors.KeyValueRenderer(key_order=['timestamp', 'level'])
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Set up root logger to use our custom handler
        root_logger = logging.getLogger()
        
        # Remove existing handlers to prevent console spam
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add our TUI handler
        formatter = logging.Formatter('%(message)s')
        self.handler.setFormatter(formatter)
        root_logger.addHandler(self.handler)
        root_logger.setLevel(logging.WARNING)  # Only show warnings/errors by default
    
    def set_debug_mode(self, enabled: bool):
        """Enable or disable debug message collection."""
        self.debug_visible = enabled
        root_logger = logging.getLogger()
        if enabled:
            root_logger.setLevel(logging.DEBUG)
        else:
            root_logger.setLevel(logging.WARNING)
    
    def show_debug_panel(self, max_messages: int = 10):
        """Display recent debug messages in a muted panel."""
        if not self.debug_visible:
            return
        
        messages = self.handler.get_recent_messages(max_messages)
        if not messages:
            return
        
        # Create debug content
        debug_text = Text()
        for msg in messages:
            level = msg['level']
            timestamp = msg['timestamp']
            message = msg['message']
            
            # Style based on log level
            if level == 'DEBUG':
                style = "dim blue"
            elif level == 'INFO':
                style = "dim cyan"
            elif level == 'WARNING':
                style = "dim yellow"
            elif level == 'ERROR':
                style = "dim red"
            else:
                style = "dim"
            
            debug_text.append(f"[{timestamp}] {level}: {message}\n", style=style)
        
        # Show debug panel at bottom
        debug_panel = Panel(
            debug_text,
            title="[dim]🐛 Debug Messages[/dim]",
            border_style="dim",
            height=min(len(messages) + 2, 8)  # Limit height
        )
        
        self.console.print(debug_panel)
    
    def clear_debug_messages(self):
        """Clear all debug messages."""
        self.handler.clear_messages()
    
    def toggle_debug_visibility(self) -> bool:
        """Toggle debug message visibility and return new state."""
        self.debug_visible = not self.debug_visible
        self.set_debug_mode(self.debug_visible)
        return self.debug_visible


def setup_tui_logging(console: Console) -> TUILogger:
    """Setup logging for TUI mode."""
    return TUILogger(console)


def setup_cli_logging(verbose: bool = False):
    """Setup logging for CLI mode (original behavior)."""
    import logging
    
    # Configure structlog for CLI
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not verbose else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set log level
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(message)s",
        level=level,
    )