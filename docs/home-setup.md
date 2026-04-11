# Home Setup

This page covers running the Squareberg hub on an always-on home server (a NAS, mini-PC, Raspberry Pi, etc.) so that all the devices on your local network can reach it from a browser.

The setup has two parts: installing and configuring the hub for LAN access (the same on every Linux server), and configuring it to start automatically on boot (which differs slightly between platforms).

!!! warning "No built-in authentication"
    The hub does not currently ship with authentication. Once you bind it to your LAN, **anyone on the same network can access it and any installed app**. This is generally fine for a trusted home network, but make sure that:

    - Your router's firewall blocks port `9100` from the public internet (this is the default for almost all home routers — they only forward ports you explicitly configure).
    - You trust everyone on your Wi-Fi (consider a guest network for visitors).
    - You do **not** expose the hub through a port-forward, reverse proxy, or VPN-less tunnel without putting an authentication layer in front of it.

## Prerequisites

| Tool | Notes |
|------|-------|
| Linux server with SSH access | NAS, mini-PC, Raspberry Pi, VPS, etc. |
| Python ≥ 3.10 | Pre-installed on most NAS systems; otherwise install via your package manager |
| `uv` | A single static binary, installable with one command |

You will also need to know your server's **LAN IP address** (e.g. `192.168.1.50`). Most home routers let you assign a static DHCP lease so the address doesn't change.

## 1. Install `uv` and the Hub

SSH into your server, then:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Make sure uv is on PATH for the current shell
source ~/.bashrc   # or ~/.profile, depending on your shell

# Install the hub as a global tool
uv tool install squareberg-hub
```

Verify:

```bash
sqb --help
```

## 2. Bind the Hub to Your LAN

By default the hub binds to `127.0.0.1` (localhost), which is only reachable from the server itself. To make it accessible to other devices on your network, edit the user config:

```bash
sqb config edit
```

Change the `host` value from `127.0.0.1` to `0.0.0.0`:

```toml
[hub]
host = "0.0.0.0"
port = 9100
```

`0.0.0.0` means "listen on every network interface", which lets other devices on your LAN connect to the hub. The port `9100` is the default — you can change it if it conflicts with another service.

!!! tip "Where is the config file?"
    `sqb config path` prints the path. By default it lives at `~/.config/squareberg/config.toml`. You can also use `sqb config show` to print the current settings, or `sqb config reset` to restore defaults.

## 3. Test It Manually

Start the hub in the foreground to make sure everything works:

```bash
sqb start
```

From another device on your network, open `http://<server-ip>:9100/` in a browser. You should see the Squareberg dashboard. Stop the hub with `Ctrl-C` once you've confirmed it works.

## 4. Start on Boot

Choose the section that matches your server.

### Linux (systemd)

Most modern Linux distributions use systemd. This includes **TrueNAS Scale**, **Debian/Ubuntu**, **Fedora**, **Raspberry Pi OS**, and most VPS images. Unraid uses a different init system — see its community plugins for "User Scripts" or use a Docker container instead.

Create a systemd unit file at `/etc/systemd/system/squareberg.service`:

```ini
[Unit]
Description=Squareberg Hub
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=YOUR_USERNAME
ExecStart=/home/YOUR_USERNAME/.local/bin/sqb start
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Replace `YOUR_USERNAME` with the user you installed `uv` and the hub under. If `sqb` is on a different path, find it with `which sqb`.

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now squareberg.service
sudo systemctl status squareberg.service
```

The hub will now start automatically on every boot. View live logs with:

```bash
journalctl -u squareberg.service -f
```

### Synology DSM

Synology's DSM is Linux-based but does not expose `systemctl` to user services. The recommended way to start a script on boot is the built-in **Task Scheduler**.

1. **Enable SSH** on the NAS: *Control Panel → Terminal & SNMP → Enable SSH service*. SSH in as an admin user.
2. **Install the hub** following the instructions in steps 1-3 above. Make a note of the absolute path printed by `which sqb` — you will need it in a moment.
3. **Open Task Scheduler**: *Control Panel → Task Scheduler*.
4. Click *Create → Triggered Task → User-defined script*.
5. **General** tab:
    - Task name: `Squareberg Hub`
    - User: the same admin user you installed under (not `root` unless you installed as root)
    - Event: `Boot-up`
    - Pre-task: leave empty
    - Enabled: yes
6. **Task Settings** tab:
    - In *Run command → User-defined script*, paste:
      ```bash
      /var/services/homes/YOUR_USERNAME/.local/bin/sqb start >> /var/services/homes/YOUR_USERNAME/squareberg.log 2>&1 &
      ```
    - Replace `YOUR_USERNAME` with your DSM admin username, and adjust the path if `which sqb` returned something different.
7. Click *OK* and reboot the NAS to verify. You can also right-click the task and choose *Run* to test without rebooting.

Logs end up at `~/squareberg.log` in the user's home directory. You can tail them over SSH with `tail -f ~/squareberg.log`.

!!! note "QNAP"
    QNAP's QTS is similar to DSM in spirit. The closest equivalent is creating an autorun script via the App Center's *AutoRun* feature (or by editing `/etc/config/autorun.sh` if you have SSH access). The install steps in sections 1-3 are unchanged. Refer to QNAP's documentation on persistent autorun scripts — the exact procedure varies by QTS version.

## 5. Accessing the Hub

Open `http://<server-ip>:9100/` from any device on your local network — laptop, phone, tablet — and you should see the dashboard. Bookmark it for convenience.

## Updating

To upgrade to a newer release of the hub:

```bash
uv tool upgrade squareberg-hub
sudo systemctl restart squareberg.service   # systemd
# or, on Synology: stop and start the task in Task Scheduler
```

Apps installed via `sqb app add` are independent of the hub package and are not affected by upgrades.
