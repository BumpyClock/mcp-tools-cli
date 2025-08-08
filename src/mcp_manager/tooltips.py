"""Tooltip System for MCP Manager TUI."""

from textual.widgets import Static
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual import events
from typing import Dict, Optional, Callable, List, Tuple
import asyncio
from datetime import datetime, timedelta


class TooltipContent:
    """Container for tooltip information."""
    
    def __init__(self, title: str, description: str, shortcuts: Optional[Dict[str, str]] = None, tips: Optional[List[str]] = None):
        """Initialize tooltip content."""
        self.title = title
        self.description = description
        self.shortcuts = shortcuts or {}
        self.tips = tips or []
        self.created_at = datetime.now()


class Tooltip(Static):
    """A tooltip widget that can be shown/hidden dynamically."""
    
    CSS = """
    Tooltip {
        display: none;
        position: absolute;
        z-index: 1000;
        background: $surface;
        border: solid $accent;
        padding: 1;
        max-width: 50;
        text-align: left;
    }
    
    Tooltip.visible {
        display: block;
    }
    
    .tooltip-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    .tooltip-description {
        color: $text;
        margin-bottom: 1;
    }
    
    .tooltip-shortcuts {
        color: $text-muted;
        text-style: italic;
    }
    
    .tooltip-tips {
        color: $warning;
        margin-top: 1;
    }
    """
    
    visible: reactive[bool] = reactive(False)
    
    def __init__(self, **kwargs):
        """Initialize tooltip."""
        super().__init__("", **kwargs)
        self.current_content: Optional[TooltipContent] = None
        self.auto_hide_timer: Optional[asyncio.Task] = None
    
    def watch_visible(self, visible: bool) -> None:
        """Update visibility class when visible changes."""
        if visible:
            self.add_class("visible")
        else:
            self.remove_class("visible")
    
    def show_tooltip(self, content: TooltipContent, x: int = 0, y: int = 0, auto_hide_delay: float = 0) -> None:
        """Show tooltip with given content at specified position."""
        self.current_content = content
        self._update_display()
        
        # Position tooltip
        self.styles.offset = (x, y)
        
        # Show tooltip
        self.visible = True
        
        # Set auto-hide timer if specified
        if auto_hide_delay > 0:
            self._set_auto_hide(auto_hide_delay)
    
    def hide_tooltip(self) -> None:
        """Hide the tooltip."""
        self.visible = False
        self._cancel_auto_hide()
    
    def _update_display(self) -> None:
        """Update tooltip display content."""
        if not self.current_content:
            return
        
        content_parts = []
        
        # Title
        if self.current_content.title:
            content_parts.append(f"[bold]{self.current_content.title}[/bold]")
        
        # Description
        if self.current_content.description:
            content_parts.append(self.current_content.description)
        
        # Shortcuts
        if self.current_content.shortcuts:
            shortcuts_text = []
            for key, action in list(self.current_content.shortcuts.items())[:3]:  # Show max 3
                shortcuts_text.append(f"[dim]{key}[/dim]: {action}")
            if shortcuts_text:
                content_parts.append("⌨️ " + " | ".join(shortcuts_text))
        
        # Tips
        if self.current_content.tips:
            tip_text = self.current_content.tips[0]  # Show first tip
            if len(tip_text) > 60:
                tip_text = tip_text[:57] + "..."
            content_parts.append(f"💡 {tip_text}")
        
        formatted_content = "\n".join(content_parts)
        self.update(formatted_content)
    
    def _set_auto_hide(self, delay: float) -> None:
        """Set auto-hide timer."""
        self._cancel_auto_hide()
        
        async def auto_hide():
            await asyncio.sleep(delay)
            self.hide_tooltip()
        
        self.auto_hide_timer = asyncio.create_task(auto_hide())
    
    def _cancel_auto_hide(self) -> None:
        """Cancel auto-hide timer."""
        if self.auto_hide_timer and not self.auto_hide_timer.done():
            self.auto_hide_timer.cancel()
            self.auto_hide_timer = None


class TooltipManager:
    """Manages tooltips throughout the application."""
    
    def __init__(self, app):
        """Initialize tooltip manager."""
        self.app = app
        self.tooltips: Dict[str, Tooltip] = {}
        self.tooltip_content: Dict[str, TooltipContent] = {}
        self.hover_timeout = 1.0  # Seconds to wait before showing tooltip
        self.hide_timeout = 0.5   # Seconds to wait before hiding tooltip
        self.hover_timers: Dict[str, asyncio.Task] = {}
        
        # Initialize tooltip content database
        self._setup_tooltip_content()
    
    def _setup_tooltip_content(self) -> None:
        """Initialize tooltip content for various UI elements."""
        self.tooltip_content.update({
            # Server Registry tooltips
            "server_table": TooltipContent(
                title="Server Registry",
                description="Shows all configured MCP servers and their status. Use Space to select multiple servers.",
                shortcuts={"A": "Add", "E": "Edit", "Del": "Remove", "Space": "Select"},
                tips=["Selected servers can be deployed together using batch operations"]
            ),
            
            "add_server_btn": TooltipContent(
                title="Add Server",
                description="Add a new MCP server configuration to your registry.",
                shortcuts={"A": "Add server", "Enter": "Confirm"},
                tips=["Server names must be unique across your configuration"]
            ),
            
            "edit_server_btn": TooltipContent(
                title="Edit Server", 
                description="Edit the configuration of the currently selected server.",
                shortcuts={"E": "Edit server", "Enter": "Save changes"},
                tips=["Changes take effect after saving and refreshing deployments"]
            ),
            
            "remove_server_btn": TooltipContent(
                title="Remove Server",
                description="Remove the selected server from your configuration.",
                shortcuts={"Del": "Remove server", "Y": "Confirm", "N": "Cancel"},
                tips=["This will undeploy the server from all platforms first"]
            ),
            
            # Deployment Matrix tooltips
            "deployment_matrix": TooltipContent(
                title="Deployment Matrix",
                description="Interactive matrix showing server deployment status across platforms. Click cells to toggle.",
                shortcuts={"Enter": "Toggle", "Space": "Select", "I": "Info", "D": "Deploy"},
                tips=["Red borders indicate configuration conflicts that need resolution"]
            ),
            
            "deploy_btn": TooltipContent(
                title="Deploy Selected",
                description="Deploy selected servers to their configured platforms.",
                shortcuts={"D": "Deploy", "Space": "Select items first"},
                tips=["Select servers and platforms before deploying to control exactly what gets deployed"]
            ),
            
            "undeploy_btn": TooltipContent(
                title="Undeploy Selected",
                description="Remove selected servers from their deployed platforms.",
                shortcuts={"U": "Undeploy", "Y": "Confirm removal"},
                tips=["This stops the servers and removes them from platform configurations"]
            ),
            
            "health_btn": TooltipContent(
                title="Health Check",
                description="Run comprehensive health checks on your servers.",
                shortcuts={"H": "Health check", "F5": "Force refresh"},
                tips=["Health checks verify server connectivity, configuration, and performance"]
            ),
            
            "resolve_btn": TooltipContent(
                title="Resolve Conflicts", 
                description="Identify and resolve deployment conflicts automatically or manually.",
                shortcuts={"C": "Check conflicts", "R": "Resolve", "I": "Ignore"},
                tips=["Resolving conflicts before deployment prevents errors and failures"]
            ),
            
            # View and navigation tooltips
            "view_btn": TooltipContent(
                title="Switch View",
                description="Cycle between different view modes: Registry, Project Focus, and Server Focus.",
                shortcuts={"V": "Switch view", "Tab": "Switch panes"},
                tips=["Different views show the same data organized for different workflows"]
            ),
            
            "status_bar": TooltipContent(
                title="Status Bar",
                description="Shows current operation status and context-sensitive keyboard shortcuts.",
                shortcuts={"F1": "Full help", "?": "Quick shortcuts"},
                tips=["The right side shows available shortcuts for your current context"]
            ),
            
            # Health Dashboard tooltips  
            "health_summary": TooltipContent(
                title="Health Summary",
                description="Overview of server health status with counts and alerts.",
                shortcuts={"M": "Toggle monitoring", "F5": "Refresh"},
                tips=["Background monitoring provides continuous health updates"]
            ),
            
            "health_table": TooltipContent(
                title="Server Health Details",
                description="Detailed health information for each server including response times and errors.",
                shortcuts={"Enter": "Details", "Space": "Select", "H": "Back to main"},
                tips=["Click servers to see detailed diagnostic information and logs"]
            ),
            
            # General UI tooltips
            "progress_bar": TooltipContent(
                title="Operation Progress",
                description="Shows progress of current deployment, health check, or other long-running operation.",
                shortcuts={"Esc": "Cancel operation"},
                tips=["Most operations can be cancelled safely if needed"]
            ),
            
            "cancel_btn": TooltipContent(
                title="Cancel Operation", 
                description="Stop the currently running operation.",
                shortcuts={"Esc": "Cancel", "Enter": "Confirm cancellation"},
                tips=["Cancelling is safe and will clean up any partial changes"]
            )
        })
    
    def create_tooltip(self, tooltip_id: str) -> Tooltip:
        """Create a new tooltip widget."""
        tooltip = Tooltip(id=f"tooltip-{tooltip_id}")
        self.tooltips[tooltip_id] = tooltip
        return tooltip
    
    def show_tooltip(self, tooltip_id: str, element_id: str, x: int = 0, y: int = 0) -> None:
        """Show tooltip for a UI element."""
        content = self.tooltip_content.get(element_id)
        if not content:
            return
        
        # Cancel any existing hover timer
        self._cancel_hover_timer(tooltip_id)
        
        # Get or create tooltip
        tooltip = self.tooltips.get(tooltip_id)
        if not tooltip:
            tooltip = self.create_tooltip(tooltip_id)
            # Add to app (this would need to be handled by the app)
        
        # Show tooltip immediately or after delay
        tooltip.show_tooltip(content, x, y)
    
    def show_tooltip_delayed(self, tooltip_id: str, element_id: str, x: int = 0, y: int = 0, delay: float = None) -> None:
        """Show tooltip after a delay (for hover behavior)."""
        delay = delay or self.hover_timeout
        
        async def show_after_delay():
            await asyncio.sleep(delay)
            self.show_tooltip(tooltip_id, element_id, x, y)
        
        # Cancel existing timer and start new one
        self._cancel_hover_timer(tooltip_id)
        self.hover_timers[tooltip_id] = asyncio.create_task(show_after_delay())
    
    def hide_tooltip(self, tooltip_id: str, delay: float = 0) -> None:
        """Hide tooltip immediately or after delay.""" 
        self._cancel_hover_timer(tooltip_id)
        
        tooltip = self.tooltips.get(tooltip_id)
        if not tooltip:
            return
        
        if delay > 0:
            async def hide_after_delay():
                await asyncio.sleep(delay)
                tooltip.hide_tooltip()
            
            asyncio.create_task(hide_after_delay())
        else:
            tooltip.hide_tooltip()
    
    def hide_all_tooltips(self) -> None:
        """Hide all visible tooltips."""
        for tooltip_id in list(self.hover_timers.keys()):
            self._cancel_hover_timer(tooltip_id)
        
        for tooltip in self.tooltips.values():
            tooltip.hide_tooltip()
    
    def _cancel_hover_timer(self, tooltip_id: str) -> None:
        """Cancel hover timer for a tooltip."""
        timer = self.hover_timers.get(tooltip_id)
        if timer and not timer.done():
            timer.cancel()
        if tooltip_id in self.hover_timers:
            del self.hover_timers[tooltip_id]
    
    def register_tooltip_content(self, element_id: str, content: TooltipContent) -> None:
        """Register custom tooltip content for an element."""
        self.tooltip_content[element_id] = content
    
    def get_tooltip_content(self, element_id: str) -> Optional[TooltipContent]:
        """Get tooltip content for an element."""
        return self.tooltip_content.get(element_id)


class TooltipMixin:
    """Mixin class to add tooltip functionality to widgets."""
    
    def __init__(self, *args, tooltip_manager: Optional[TooltipManager] = None, tooltip_content_id: Optional[str] = None, **kwargs):
        """Initialize tooltip mixin."""
        super().__init__(*args, **kwargs)
        self.tooltip_manager = tooltip_manager
        self.tooltip_content_id = tooltip_content_id or self.id
        self._tooltip_id = f"{self.id}_tooltip" if self.id else f"{id(self)}_tooltip"
    
    def on_enter(self, event: events.Enter) -> None:
        """Show tooltip on mouse enter."""
        if self.tooltip_manager and self.tooltip_content_id:
            # Get mouse position (simplified - in practice would need screen coordinates)
            self.tooltip_manager.show_tooltip_delayed(
                self._tooltip_id,
                self.tooltip_content_id,
                x=0, y=0  # Would calculate proper position
            )
        super().on_enter(event)
    
    def on_leave(self, event: events.Leave) -> None:
        """Hide tooltip on mouse leave."""
        if self.tooltip_manager:
            self.tooltip_manager.hide_tooltip(self._tooltip_id, delay=self.tooltip_manager.hide_timeout)
        super().on_leave(event)
    
    def on_focus(self, event: events.Focus) -> None:
        """Show tooltip on focus (for keyboard navigation)."""
        if self.tooltip_manager and self.tooltip_content_id:
            self.tooltip_manager.show_tooltip_delayed(
                self._tooltip_id,
                self.tooltip_content_id,
                delay=0.5  # Shorter delay for keyboard focus
            )
        super().on_focus(event)
    
    def on_blur(self, event: events.Blur) -> None:
        """Hide tooltip on blur."""
        if self.tooltip_manager:
            self.tooltip_manager.hide_tooltip(self._tooltip_id)
        super().on_blur(event)