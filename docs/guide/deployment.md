# Running as a Service

By default, `sqb start` runs the hub in the foreground. For persistent operation — surviving terminal sessions, auto-starting on login — you need to run it under a service manager.

## macOS: launchd

macOS uses `launchd` for user-space service management. Create a plist file at `~/Library/LaunchAgents/dev.squareberg.hub.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>dev.squareberg.hub</string>

  <key>ProgramArguments</key>
  <array>
    <!-- Adjust this path to match your squareberg venv -->
    <string>/Users/YOUR_USERNAME/Code/squareberg-hub/.venv/bin/sqb</string>
    <string>start</string>
  </array>

  <key>WorkingDirectory</key>
  <string>/Users/YOUR_USERNAME/Code/squareberg-hub</string>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>/Users/YOUR_USERNAME/.local/share/squareberg/logs/hub.stdout.log</string>

  <key>StandardErrorPath</key>
  <string>/Users/YOUR_USERNAME/.local/share/squareberg/logs/hub.stderr.log</string>
</dict>
</plist>
```

Replace `YOUR_USERNAME` with your macOS username, and adjust the `WorkingDirectory` and `ProgramArguments` paths to match your actual installation.

### Enable and Start

```bash
# Load the service (registers with launchd)
launchctl load ~/Library/LaunchAgents/dev.squareberg.hub.plist

# Verify it is running
launchctl list | grep squareberg
```

The hub will now start automatically on login. `KeepAlive: true` means launchd will restart it if it exits unexpectedly.

### Stop and Disable

```bash
# Stop the service for this session
launchctl stop dev.squareberg.hub

# Unload (disable autostart)
launchctl unload ~/Library/LaunchAgents/dev.squareberg.hub.plist
```

### Check Logs

```bash
tail -f ~/.local/share/squareberg/logs/hub.stdout.log
tail -f ~/.local/share/squareberg/logs/hub.stderr.log
```

---

## Linux: systemd User Service

On Linux, `systemd --user` manages per-user services without requiring root. Create the service file at `~/.config/systemd/user/squareberg.service`:

```ini
[Unit]
Description=Squareberg Hub
After=network.target

[Service]
Type=simple
# Adjust the paths below to match your installation
ExecStart=/home/YOUR_USERNAME/Code/squareberg-hub/.venv/bin/sqb start
WorkingDirectory=/home/YOUR_USERNAME/Code/squareberg-hub
Restart=on-failure
RestartSec=5s

# Log to the systemd journal; also readable via journalctl
StandardOutput=journal
StandardError=journal
SyslogIdentifier=squareberg

[Install]
WantedBy=default.target
```

Replace `YOUR_USERNAME` and the paths as needed.

### Enable and Start

```bash
# Reload systemd to pick up the new unit file
systemctl --user daemon-reload

# Enable autostart on login
systemctl --user enable squareberg

# Start now
systemctl --user start squareberg

# Check status
systemctl --user status squareberg
```

### Autostart Without Login (Lingering)

By default, user services only run while the user is logged in. To keep the hub running even after you log out:

```bash
loginctl enable-linger $USER
```

!!! warning
    `enable-linger` requires a system administrator or `sudo` access on most distributions.

### Stop and Disable

```bash
systemctl --user stop squareberg
systemctl --user disable squareberg
```

### Check Logs

```bash
# Follow the journal for the squareberg unit
journalctl --user -u squareberg -f

# Show last 100 lines
journalctl --user -u squareberg -n 100
```

Per-app logs (captured by the hub) are still written to `~/.local/share/squareberg/logs/` and can be tailed with `sqb app logs <name> -f`.
