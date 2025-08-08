"""Health Dashboard widgets for the TUI."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Static, DataTable, ProgressBar, Sparkline
from textual.reactive import reactive
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from mcp_manager.health_monitor import HealthMonitor, HealthStatus, HealthCheckResult, ServerHealthHistory


class HealthSummaryCard(Static):
    """Summary card showing overall health statistics."""
    
    def __init__(self, health_monitor: HealthMonitor, **kwargs):
        super().__init__(**kwargs)
        self.health_monitor = health_monitor
        self.update_timer = None
    
    def on_mount(self) -> None:
        """Start updating when mounted."""
        self.update_display()
        # Set up periodic updates
        self.update_timer = self.set_interval(5.0, self.update_display)
    
    def update_display(self) -> None:
        """Update the summary display."""
        summary = self.health_monitor.get_overall_health_summary()
        
        # Create visual summary
        total = summary["total_servers"]
        healthy = summary["healthy"]
        warning = summary["warning"]
        critical = summary["critical"]
        health_percentage = summary["health_percentage"]
        
        # Health indicator
        if health_percentage >= 90:
            health_icon = "🟢"
            health_color = "green"
        elif health_percentage >= 70:
            health_icon = "🟡"
            health_color = "yellow"
        else:
            health_icon = "🔴"
            health_color = "red"
        
        # Format last check time
        last_check = summary["last_check"]
        if last_check:
            time_diff = datetime.now() - last_check
            if time_diff < timedelta(minutes=1):
                last_check_str = "just now"
            elif time_diff < timedelta(hours=1):
                minutes = int(time_diff.total_seconds() / 60)
                last_check_str = f"{minutes}m ago"
            else:
                last_check_str = last_check.strftime("%H:%M")
        else:
            last_check_str = "never"
        
        # Monitoring status
        monitoring_status = "🔄 Active" if summary.get("monitoring_active", False) else "⏸️  Paused"
        
        content = f"""[bold]📊 Health Overview[/bold]

{health_icon} Overall Health: [bold {health_color}]{health_percentage}%[/bold {health_color}] ({healthy}/{total} healthy)

📈 Server Status:
  🟢 Healthy: {healthy}
  🟡 Warning: {warning}  
  🔴 Critical: {critical}
  ⚪ Unknown: {summary["unknown"]}

⏱️  Last Check: {last_check_str}
{monitoring_status}
📊 Total Checks: {summary.get("total_checks_performed", 0)}"""
        
        self.update(content)


class ServerHealthTable(DataTable):
    """Table showing health status for all servers."""
    
    def __init__(self, health_monitor: HealthMonitor, **kwargs):
        super().__init__(**kwargs)
        self.health_monitor = health_monitor
        self.update_timer = None
    
    def on_mount(self) -> None:
        """Initialize table when mounted."""
        # Add columns
        self.add_columns(
            "Server", "Status", "Health", "Last Check", "Response Time", "Issues"
        )
        
        # Load initial data
        self.refresh_data()
        
        # Set up periodic updates
        self.update_timer = self.set_interval(10.0, self.refresh_data)
    
    def refresh_data(self) -> None:
        """Refresh the health table data."""
        # Clear existing rows
        self.clear()
        
        # Re-add columns (cleared by clear())
        if not self.columns:
            self.add_columns(
                "Server", "Status", "Health", "Last Check", "Response Time", "Issues"
            )
        
        # Get all server health histories
        servers = self.health_monitor.registry.list_servers()
        
        for server_name in sorted(servers.keys()):
            history = self.health_monitor.get_server_health_history(server_name)
            
            if not history or not history.history:
                # No health data yet
                self.add_row(
                    server_name,
                    "⚪ Unknown",
                    "0%",
                    "Never",
                    "-",
                    "Not checked"
                )
                continue
            
            # Get latest result
            latest = history.history[-1]
            
            # Status with emoji
            status_emoji, status_color, _ = latest.status.value
            status_text = f"{status_emoji} {latest.status.name.title()}"
            
            # Health score
            health_score = f"{history.health_score}%"
            
            # Last check time
            time_diff = datetime.now() - latest.timestamp
            if time_diff < timedelta(minutes=1):
                last_check = "just now"
            elif time_diff < timedelta(hours=1):
                minutes = int(time_diff.total_seconds() / 60)
                last_check = f"{minutes}m ago"
            elif time_diff < timedelta(days=1):
                hours = int(time_diff.total_seconds() / 3600)
                last_check = f"{hours}h ago"
            else:
                last_check = latest.timestamp.strftime("%m/%d")
            
            # Response time
            response_time = f"{latest.response_time:.2f}s"
            
            # Issues/message
            issues = latest.message[:30] + "..." if len(latest.message) > 30 else latest.message
            
            self.add_row(
                server_name,
                status_text,
                health_score,
                last_check,
                response_time,
                issues
            )


class ServerHealthDetail(Container):
    """Detailed view of a single server's health."""
    
    def __init__(self, health_monitor: HealthMonitor, **kwargs):
        super().__init__(**kwargs)
        self.health_monitor = health_monitor
        self.selected_server: Optional[str] = None
    
    def compose(self) -> ComposeResult:
        """Create the detail view layout."""
        yield Static("Select a server to view details", id="health-detail-content")
    
    def show_server_details(self, server_name: str) -> None:
        """Show detailed health information for a server."""
        self.selected_server = server_name
        self.update_details()
    
    def update_details(self) -> None:
        """Update the detailed view."""
        if not self.selected_server:
            content_widget = self.query_one("#health-detail-content", Static)
            content_widget.update("Select a server to view details")
            return
        
        history = self.health_monitor.get_server_health_history(self.selected_server)
        if not history or not history.history:
            content_widget = self.query_one("#health-detail-content", Static)
            content_widget.update(f"No health data available for {self.selected_server}")
            return
        
        latest = history.history[-1]
        
        # Build detailed information
        content = f"[bold]🔍 Health Details: {self.selected_server}[/bold]\n\n"
        
        # Current status
        status_emoji, status_color, _ = latest.status.value
        content += f"Current Status: {status_emoji} [bold {status_color}]{latest.status.name.title()}[/bold {status_color}]\n"
        content += f"Health Score: {history.health_score}%\n"
        content += f"Last Check: {latest.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"Response Time: {latest.response_time:.3f}s\n"
        content += f"Message: {latest.message}\n\n"
        
        # Check details
        if latest.details and "checks" in latest.details:
            content += "[bold]📋 Check Results:[/bold]\n"
            for check in latest.details["checks"]:
                check_status = check.get("status", "unknown")
                check_emoji = "✅" if check_status == "healthy" else "⚠️" if check_status == "warning" else "❌"
                content += f"  {check_emoji} {check['name'].title()}: {check.get('message', 'No message')}\n"
            content += "\n"
        
        # Health history
        content += "[bold]📊 Recent History:[/bold]\n"
        for i, result in enumerate(reversed(history.history[-5:])):
            result_emoji, _, _ = result.status.value
            age = datetime.now() - result.timestamp
            if age < timedelta(minutes=1):
                time_str = "now"
            elif age < timedelta(hours=1):
                time_str = f"{int(age.total_seconds()/60)}m"
            else:
                time_str = f"{int(age.total_seconds()/3600)}h"
            
            content += f"  {result_emoji} {time_str}: {result.message[:40]}\n"
        
        # Additional stats
        if history.last_healthy:
            last_healthy_age = datetime.now() - history.last_healthy
            if last_healthy_age < timedelta(minutes=1):
                healthy_str = "just now"
            elif last_healthy_age < timedelta(hours=1):
                healthy_str = f"{int(last_healthy_age.total_seconds()/60)} minutes ago"
            else:
                healthy_str = f"{int(last_healthy_age.total_seconds()/3600)} hours ago"
            content += f"\n🟢 Last Healthy: {healthy_str}\n"
        
        if history.consecutive_failures > 0:
            content += f"🔴 Consecutive Failures: {history.consecutive_failures}\n"
        
        # Update the display
        content_widget = self.query_one("#health-detail-content", Static)
        content_widget.update(content)


class HealthDashboard(Container):
    """Main health monitoring dashboard container."""
    
    def __init__(self, health_monitor: HealthMonitor, **kwargs):
        super().__init__(**kwargs)
        self.health_monitor = health_monitor
        self.summary_card: Optional[HealthSummaryCard] = None
        self.health_table: Optional[ServerHealthTable] = None
        self.detail_view: Optional[ServerHealthDetail] = None
    
    def compose(self) -> ComposeResult:
        """Create the dashboard layout."""
        with Grid(id="health-grid"):
            # Top row: Summary card
            self.summary_card = HealthSummaryCard(
                self.health_monitor, 
                id="health-summary", 
                classes="health-widget"
            )
            yield self.summary_card
            
            # Middle row: Health table
            self.health_table = ServerHealthTable(
                self.health_monitor, 
                id="health-table",
                classes="health-widget"
            )
            yield self.health_table
            
            # Bottom row: Detail view
            self.detail_view = ServerHealthDetail(
                self.health_monitor,
                id="health-detail",
                classes="health-widget"
            )
            yield self.detail_view
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in health table."""
        if event.data_table == self.health_table:
            try:
                # Get the server name from the selected row
                row_data = self.health_table.get_row_at(event.cursor_row)
                server_name = str(row_data[0])
                
                # Show details for selected server
                if self.detail_view:
                    self.detail_view.show_server_details(server_name)
                    
            except (IndexError, ValueError):
                pass  # Ignore selection errors
    
    def refresh_all(self) -> None:
        """Refresh all dashboard components."""
        if self.summary_card:
            self.summary_card.update_display()
        if self.health_table:
            self.health_table.refresh_data()
        if self.detail_view and self.detail_view.selected_server:
            self.detail_view.update_details()
    
    def on_mount(self) -> None:
        """Set up dashboard when mounted."""
        # Register for health monitor callbacks
        self.health_monitor.add_status_callback(self._on_health_update)
    
    def on_unmount(self) -> None:
        """Clean up when unmounted."""
        # Unregister from health monitor callbacks
        self.health_monitor.remove_status_callback(self._on_health_update)
    
    def _on_health_update(self, server_name: str, result: HealthCheckResult) -> None:
        """Handle real-time health updates."""
        # This will be called from the health monitor thread
        # Schedule UI update on the main thread
        self.call_later(self._update_ui_after_health_change)
    
    def _update_ui_after_health_change(self) -> None:
        """Update UI after health status change."""
        # Refresh summary (health table refreshes automatically)
        if self.summary_card:
            self.summary_card.update_display()
        
        # Update detail view if it's showing the updated server
        if (self.detail_view and 
            self.detail_view.selected_server and 
            self.detail_view.selected_server):
            self.detail_view.update_details()


class HealthAlertBanner(Static):
    """Banner for showing health alerts."""
    
    def __init__(self, health_monitor: HealthMonitor, **kwargs):
        super().__init__(**kwargs)
        self.health_monitor = health_monitor
        self.current_alerts: List[str] = []
    
    def on_mount(self) -> None:
        """Start monitoring for alerts."""
        self.health_monitor.add_status_callback(self._check_for_alerts)
        self.update_alerts()
    
    def on_unmount(self) -> None:
        """Stop monitoring for alerts."""
        self.health_monitor.remove_status_callback(self._check_for_alerts)
    
    def _check_for_alerts(self, server_name: str, result: HealthCheckResult) -> None:
        """Check for new alerts."""
        self.call_later(self.update_alerts)
    
    def update_alerts(self) -> None:
        """Update alert display."""
        alerts = []
        
        # Check for critical servers
        summary = self.health_monitor.get_overall_health_summary()
        critical_count = summary["critical"]
        
        if critical_count > 0:
            alerts.append(f"🚨 {critical_count} server(s) in critical state")
        
        # Check for servers with consecutive failures
        for history in self.health_monitor.health_history.values():
            if history.consecutive_failures >= 3:
                alerts.append(f"⚠️ {history.server_name}: {history.consecutive_failures} consecutive failures")
        
        # Update display
        if alerts:
            alert_text = " • ".join(alerts)
            self.update(f"[bold red]ALERTS:[/bold red] {alert_text}")
            self.display = True
        else:
            self.display = False
    
    def has_alerts(self) -> bool:
        """Check if there are active alerts."""
        return len(self.current_alerts) > 0