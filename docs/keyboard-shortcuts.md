# Keyboard Shortcuts & Navigation

## Overview

The MCP Manager TUI provides comprehensive keyboard shortcuts for efficient navigation and operation without requiring a mouse. All shortcuts are context-sensitive and discoverable through the status bar.

## Primary Actions (Always Available)

| Key | Action | Description |
|-----|--------|-------------|
| `A` | Add Server | Opens dialog to add a new MCP server |
| `E` | Edit Server | Edit the currently selected server |
| `D` | Deploy | Deploy selected server(s) to targets |
| `R` | Refresh | Refresh all data tables |
| `H` | Health Check | Run health checks on servers |
| `Q` | Quit | Quit application (with confirmation if changes pending) |

## Navigation

| Key | Action | Description |
|-----|--------|-------------|
| `Tab` | Next Pane | Switch focus between Server Registry and Deployment Status |
| `Shift+Tab` | Previous Pane | Switch focus in reverse direction |
| `Escape` | Cancel | Cancel current operation or close dialog |
| `Enter` | Default Action | Context-sensitive action (Edit in server pane, Deploy in deployment pane) |

## Context-Sensitive Actions

### Server Registry Pane

| Key | Action | Description |
|-----|--------|-------------|
| `Delete` | Remove Server | Remove selected server (with confirmation) |
| `Space` | Toggle Selection | Select/deselect server for batch operations |
| `E` | Edit Server | Edit selected server configuration |
| `Enter` | Edit Server | Same as `E` key |

### Deployment Status Pane

| Key | Action | Description |
|-----|--------|-------------|
| `U` | Undeploy | Remove server from selected platforms |
| `D` | Deploy | Deploy server to additional platforms |
| `Enter` | Deploy | Same as `D` key |

## Alternative Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| `F5` | Refresh | Alternative refresh shortcut |

## Dialog Shortcuts

### Confirmation Dialogs

| Key | Action | Description |
|-----|--------|-------------|
| `Y` | Yes | Confirm the action |
| `N` | No | Cancel the action |
| `Escape` | Cancel | Same as `N` |

### Deployment Dialog

| Key | Action | Description |
|-----|--------|-------------|
| `Space` | Toggle Target | Select/deselect deployment target |
| `Enter` | Confirm | Deploy to selected targets |
| `Escape` | Cancel | Cancel deployment |

## Visual Feedback

### Focus Indicators
- **Focused Pane**: Highlighted with accent border
- **Status Bar**: Shows context-sensitive help text
- **Current Selection**: Highlighted row in tables

### Status Bar Format
```
[HH:MM:SS] Status Message | Context-Sensitive Help
```

### Context Help Examples
- Server pane: `A:Add E:Edit Del:Remove D:Deploy H:Health R:Refresh Q:Quit Tab:Switch`
- Deployment pane: `D:Deploy U:Undeploy H:Health R:Refresh Q:Quit Tab:Switch`
- Dialog: `Enter:Confirm Esc:Cancel Y:Yes N:No`

## Multi-Selection Support

### Server Selection
- Use `Space` to select/deselect servers
- Selected servers are remembered for batch operations
- Deploy multiple servers at once
- Run health checks on selected servers

### Selection Feedback
- Status bar shows selection count: `3 server(s) selected`
- Visual indicators in table (implementation ready)

## Keyboard-First Design

### Principles
1. **Discoverability**: All shortcuts shown in footer and status bar
2. **Consistency**: Same keys perform similar actions across contexts
3. **Safety**: Destructive actions require confirmation
4. **Efficiency**: Common actions use single keystrokes
5. **Accessibility**: No mouse required for any functionality

### Best Practices
- Always check status bar for available shortcuts
- Use Tab to navigate between panes
- Use Space to select items before batch operations
- Press Escape to cancel any operation
- All confirmations support Y/N quick keys

## Implementation Features

### Context Awareness
- Different shortcuts based on focused pane
- Dynamic help text updates with context
- Actions only available when relevant
- Intelligent defaults for Enter key

### Error Handling
- Clear feedback for invalid operations
- Graceful handling of edge cases
- User-friendly error messages
- Safe operation cancellation

### Performance
- Instant keyboard response
- No blocking operations
- Smooth focus transitions
- Efficient table navigation

## Troubleshooting

### Common Issues

**Shortcut not working?**
- Check which pane has focus (look for highlighted border)
- Verify shortcut is available in current context
- Check status bar for available actions

**Can't navigate between panes?**
- Use Tab or Shift+Tab to switch focus
- Click on desired pane if keyboard navigation fails

**Actions not available?**
- Some actions require a selection first
- Switch to appropriate pane for the action
- Check if servers/deployments exist in tables

**Confirmation dialogs?**
- Use Y/N keys for quick confirmation
- Escape always cancels
- Enter confirms in most dialogs

## Future Enhancements

### Planned Features
- Vim-style navigation (j/k for up/down)
- Search functionality (/ key)
- Quick filter (f key)
- Batch operations on multiple selections
- Customizable shortcuts
- Keyboard shortcuts help screen (F1)

### Advanced Navigation
- Page up/down for large tables
- Home/End for table navigation
- Quick jump to first/last item
- Incremental search within tables