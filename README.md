# RemConn

This little project began as a script I chucked together to manage connections on my MacBook and Linux VMs. The problem being:

- No free tool similar to MobaXterm 
- Didn't want to remember aliases for connections and messy config files

I've continually updated it to suit my needs, and make it less "clunky". Thanks to AI, I've been able to implement multiple improvements at pace which have enhanced the UI and connection management aspects.

This is tool is lightweight and simple to use and manage. There is likely other improvements to be made, but for now things work as required.

Personally, I've found this tool useful for day to day working, as well as other events like CTF's. Especially those that cover larger scenarios with multiple hosts and connection types (SSH, RDP etc.).

## Prerequisites

Like most Python projects, creating a Virtual Environment is the recommended approach and can be setup like so:

```
git clone https://github.com/Pir00t/RemConn.git

cd RemConn

python -m venv <venv_name>

# For Linux/Mac activate the environment
source <venv_name>/bin/activate
```

There is one primary requirement for the GUI element to work, which can be installed within your environment like so:

```
pip install PyQt6
```

GNU 'screen' - If not installed, utilise the package manager relevant to your OS.

---

## Features

- Edit Connections: Full editing capabilities with category switching
- Auto-backup: Creates timestamped backups before saving
- Configuration Validation: Validates structure when loading

**Will run SSH command via Windows Command Prompt, though lacks "screen" feature**

## Usage Notes

Connection Search/Filter (per tab): Real-time filtering as you type in the search box

Keyboard Shortcuts:

- Enter: Connect to selected
- Ctrl+S: Save config
- Ctrl+N: Add new connection
- Ctrl+E: Edit selected connection
- Delete: Delete selected connection

Mouse Operations:

- Double-click to Connect: Simple and intuitive connection method
- Right-click Context Menu: For common operations

## Potential Upgrades

- Usage
  - Logging
  - Test connection before saving
- Security Features
  - Encrypt config file
  - SSH key selection
- UI 
  - Visual connection indicator
  - Last connected timestamp
  - Show connection details

---

Should anyone actually stumble across this and find it useful or have suggestions on improvements, feel free to reach out or submit a pull request!
