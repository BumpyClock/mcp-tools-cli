"""Context-Sensitive Help System for MCP Manager TUI."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Grid
from textual.widgets import Static, Input, DataTable, Button, Markdown, Tabs, Tab
from textual.screen import ModalScreen
from textual import events
from textual.binding import Binding
from typing import Dict, List, Optional, Callable
import re

from .help_content import help_content, HelpSection


class HelpSearchResults(DataTable):
    """Search results table for help content."""
    
    def __init__(self, on_select: Callable[[str], None], **kwargs):
        """Initialize search results table."""
        super().__init__(**kwargs)
        self.on_select = on_select
        self.add_columns("Title", "Category", "Keywords")
        self.cursor_type = "row"
    
    def update_results(self, section_ids: List[str]) -> None:
        """Update the search results with matching sections."""
        self.clear()
        
        for section_id in section_ids:
            section = help_content.get_section(section_id)
            if section:
                keywords = ", ".join(section.keywords[:3])  # Show first 3 keywords
                if len(section.keywords) > 3:
                    keywords += "..."
                self.add_row(section.title, section.category.title(), keywords, key=section_id)
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in search results."""
        if event.row_key:
            self.on_select(str(event.row_key.value))


class HelpContentViewer(Markdown):
    """Enhanced markdown viewer for help content."""
    
    def __init__(self, **kwargs):
        """Initialize help content viewer."""
        super().__init__("", **kwargs)
        self.current_section: Optional[HelpSection] = None
    
    def show_section(self, section: HelpSection) -> None:
        """Display a help section with enhanced formatting."""
        self.current_section = section
        
        # Build formatted content
        content_parts = [
            f"# {section.title}\n",
            f"*Category: {section.category.title()}*\n",
            section.content,
        ]
        
        # Add shortcuts section if available
        if section.shortcuts:
            content_parts.extend([
                "\n## Keyboard Shortcuts\n",
                "| Key | Action |",
                "|-----|--------|"
            ])
            for key, action in section.shortcuts.items():
                content_parts.append(f"| `{key}` | {action} |")
        
        # Add tips section if available
        if section.tips:
            content_parts.extend([
                "\n## Tips & Tricks\n"
            ])
            for tip in section.tips:
                content_parts.append(f"💡 {tip}\n")
        
        # Add see also section if available
        if section.see_also:
            content_parts.extend([
                "\n## See Also\n",
                f"Related topics: {', '.join(section.see_also)}"
            ])
        
        formatted_content = "\n".join(content_parts)
        self.update(formatted_content)


class QuickHelpPanel(Static):
    """Quick help panel for current context shortcuts."""
    
    def __init__(self, **kwargs):
        """Initialize quick help panel.""" 
        super().__init__("", **kwargs)
        self.current_context = ""
    
    def update_context(self, context: str) -> None:
        """Update help panel for specific context."""
        if context == self.current_context:
            return
            
        self.current_context = context
        shortcuts = help_content.get_keyboard_shortcuts_for_context(context)
        
        if shortcuts:
            # Format shortcuts as compact display
            shortcut_text = " | ".join([
                f"[bold]{key}[/bold]:{action.split()[0]}" 
                for key, action in list(shortcuts.items())[:8]  # Show first 8
            ])
            self.update(f"💡 {shortcut_text}")
        else:
            self.update("💡 Press F1 for help, ? for shortcuts")


class HelpModal(ModalScreen):
    """Modal help screen with search and navigation."""
    
    BINDINGS = [
        Binding("escape", "dismiss", "Close", priority=True),
        Binding("ctrl+f", "focus_search", "Search", priority=True), 
        Binding("f3", "next_search", "Next", show=False),
        Binding("shift+f3", "prev_search", "Previous", show=False),
    ]
    
    CSS = """
    HelpModal {
        align: center middle;
    }
    
    #help-dialog {
        width: 90%;
        height: 85%;
        border: thick $primary;
        background: $surface;
    }
    
    #search-bar {
        dock: top;
        height: 3;
        border-bottom: solid $accent;
        padding: 1;
    }
    
    #search-input {
        width: 70%;
    }
    
    #category-tabs {
        dock: top;
        height: 3;
    }
    
    #content-area {
        height: 100%;
    }
    
    #results-pane {
        width: 30%;
        border-right: solid $accent;
    }
    
    #content-pane {
        width: 70%;
        padding: 1;
    }
    
    #quick-actions {
        dock: bottom;
        height: 3;
        border-top: solid $accent;
    }
    
    .help-button {
        margin: 0 1;
    }
    
    HelpSearchResults {
        height: 100%;
    }
    
    HelpContentViewer {
        height: 100%;
        scrollbar-gutter: stable;
    }
    """
    
    def __init__(self, initial_context: Optional[str] = None, **kwargs):
        """Initialize help modal."""
        super().__init__(**kwargs)
        self.initial_context = initial_context
        self.search_results: Optional[HelpSearchResults] = None
        self.content_viewer: Optional[HelpContentViewer] = None
        self.search_input: Optional[Input] = None
        self.category_tabs: Optional[Tabs] = None
        self.current_search_results: List[str] = []
        self.search_index = 0
    
    def compose(self) -> ComposeResult:
        """Compose the help modal layout."""
        with Vertical(id="help-dialog"):
            yield Static("📖 MCP Manager Help System", id="help-title", classes="section-header")
            
            # Search bar
            with Horizontal(id="search-bar"):
                self.search_input = Input(placeholder="Search help content...", id="search-input")
                yield self.search_input
                yield Button("Search", id="search-btn", classes="help-button")
                yield Button("Clear", id="clear-btn", classes="help-button")
            
            # Category tabs - will be populated in on_mount
            self.category_tabs = Tabs()
            yield self.category_tabs
            
            # Main content area
            with Horizontal(id="content-area"):
                # Search results pane
                with Vertical(id="results-pane"):
                    yield Static("📋 Help Topics", classes="section-header")
                    self.search_results = HelpSearchResults(
                        on_select=self._show_section,
                        id="search-results"
                    )
                    yield self.search_results
                
                # Content viewer pane
                with Vertical(id="content-pane"):
                    yield Static("📄 Content", classes="section-header")
                    self.content_viewer = HelpContentViewer(id="content-viewer")
                    yield self.content_viewer
            
            # Quick actions
            with Horizontal(id="quick-actions"):
                yield Button("🏠 Getting Started", id="getting-started-btn", classes="help-button")
                yield Button("⌨️ Shortcuts", id="shortcuts-btn", classes="help-button")
                yield Button("🔧 Troubleshooting", id="troubleshooting-btn", classes="help-button")
                yield Button("❌ Close", id="close-btn", classes="help-button")
    
    def on_mount(self) -> None:
        """Initialize help modal when mounted."""
        # Add category tabs now that the widget is mounted
        if self.category_tabs:
            try:
                categories = ["All"] + help_content.get_all_categories()
                for category in categories:
                    tab = Tab(category.title(), id=f"tab-{category.lower()}")
                    self.category_tabs.add_tab(tab)
            except Exception as e:
                # If adding tabs fails, continue without them
                pass
        
        # Show all topics initially
        self._update_search_results()
        
        # Show context-specific help if provided
        if self.initial_context:
            section = help_content.get_contextual_help(self.initial_context)
            if section:
                self._show_section_by_id(self.initial_context)
            else:
                self._show_section_by_id("getting_started")
        else:
            self._show_section_by_id("getting_started")
        
        # Focus search input
        if self.search_input:
            self.search_input.focus()
    
    def _update_search_results(self, query: str = "") -> None:
        """Update search results based on query."""
        if query.strip():
            results = help_content.search_content(query)
        else:
            results = list(help_content._content.keys())
        
        self.current_search_results = results
        if self.search_results:
            self.search_results.update_results(results)
    
    def _show_section(self, section_id: str) -> None:
        """Show a help section in the content viewer."""
        section = help_content.get_section(section_id)
        if section and self.content_viewer:
            self.content_viewer.show_section(section)
    
    def _show_section_by_id(self, section_id: str) -> None:
        """Show section and select it in results."""
        self._show_section(section_id)
        # Also select it in search results if visible
        if self.search_results and section_id in self.current_search_results:
            # Find the row and select it
            for row_index in range(self.search_results.row_count):
                if self.search_results.get_row_at(row_index) and str(self.search_results.rows[row_index].key.value) == section_id:
                    self.search_results.cursor_row = row_index
                    break
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            query = event.value
            self._update_search_results(query)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "search-btn":
            if self.search_input:
                self._update_search_results(self.search_input.value)
        elif event.button.id == "clear-btn":
            if self.search_input:
                self.search_input.value = ""
                self._update_search_results()
        elif event.button.id == "getting-started-btn":
            self._show_section_by_id("getting_started")
        elif event.button.id == "shortcuts-btn":
            self._show_section_by_id("keyboard_shortcuts")
        elif event.button.id == "troubleshooting-btn":
            self._show_section_by_id("troubleshooting")
        elif event.button.id == "close-btn":
            self.dismiss()
    
    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle category tab selection."""
        if event.tab.id:
            category = event.tab.id.replace("tab-", "")
            if category == "all":
                results = list(help_content._content.keys())
            else:
                results = help_content.get_sections_by_category(category)
            
            self.current_search_results = results
            if self.search_results:
                self.search_results.update_results(results)
    
    def action_focus_search(self) -> None:
        """Focus the search input (Ctrl+F)."""
        if self.search_input:
            self.search_input.focus()
    
    def action_next_search(self) -> None:
        """Go to next search result (F3)."""
        if self.current_search_results and self.search_results:
            self.search_index = (self.search_index + 1) % len(self.current_search_results)
            self.search_results.cursor_row = self.search_index
            section_id = self.current_search_results[self.search_index]
            self._show_section(section_id)
    
    def action_prev_search(self) -> None:
        """Go to previous search result (Shift+F3)."""
        if self.current_search_results and self.search_results:
            self.search_index = (self.search_index - 1) % len(self.current_search_results)
            self.search_results.cursor_row = self.search_index
            section_id = self.current_search_results[self.search_index]
            self._show_section(section_id)
    
    def action_dismiss(self) -> None:
        """Close the help modal (Escape)."""
        self.dismiss()


class HelpSystem:
    """Main help system coordinator."""
    
    def __init__(self, app):
        """Initialize help system."""
        self.app = app
        self.quick_help_panel: Optional[QuickHelpPanel] = None
        
    def setup_help_system(self) -> None:
        """Set up help system components."""
        # Help system is set up when components are created
        pass
    
    def show_contextual_help(self, context: str) -> None:
        """Show context-sensitive help."""
        modal = HelpModal(initial_context=context)
        self.app.push_screen(modal)
    
    def show_full_help(self) -> None:
        """Show the full help system."""
        modal = HelpModal()
        self.app.push_screen(modal)
    
    def show_keyboard_shortcuts(self, context: Optional[str] = None) -> None:
        """Show keyboard shortcuts help."""
        if context:
            section = help_content.get_contextual_help(context)
            if section and section.shortcuts:
                # Show shortcuts for specific context
                shortcuts_text = "\n".join([
                    f"**{key}** - {action}" 
                    for key, action in section.shortcuts.items()
                ])
                # For now, use the full help modal
                # In future, could show a compact shortcuts overlay
                self.show_contextual_help(context)
            else:
                self.show_contextual_help("keyboard_shortcuts")
        else:
            self.show_contextual_help("keyboard_shortcuts")
    
    def get_status_bar_help(self, context: str) -> str:
        """Get concise help text for status bar."""
        shortcuts = help_content.get_keyboard_shortcuts_for_context(context)
        if shortcuts:
            # Create compact help text for status bar
            main_shortcuts = {}
            
            # Prioritize most important shortcuts
            priority_keys = ['A', 'E', 'D', 'R', 'H', 'V', 'Q', 'Tab']
            for key in priority_keys:
                if key in shortcuts:
                    action = shortcuts[key].split()[0]  # First word of action
                    main_shortcuts[key] = action
            
            # Add any remaining shortcuts up to limit
            for key, action in shortcuts.items():
                if len(main_shortcuts) >= 8:  # Limit to avoid cluttering
                    break
                if key not in main_shortcuts:
                    main_shortcuts[key] = action.split()[0]
            
            help_text = " ".join([f"{key}:{action}" for key, action in main_shortcuts.items()])
            return help_text
        
        return "F1:Help ?:Shortcuts"
    
    def get_context_tips(self, context: str) -> List[str]:
        """Get tips for current context.""" 
        return help_content.get_tips_for_context(context)
    
    def create_quick_help_panel(self) -> QuickHelpPanel:
        """Create a quick help panel for embedding in the UI."""
        self.quick_help_panel = QuickHelpPanel()
        return self.quick_help_panel
    
    def update_quick_help(self, context: str) -> None:
        """Update quick help panel for new context."""
        if self.quick_help_panel:
            self.quick_help_panel.update_context(context)