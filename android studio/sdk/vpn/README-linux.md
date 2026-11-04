# Devsp8c on Linux - exact install

Target: a Linux desktop, Ubuntu/Debian commands below.
Fedora/RHEL equivalent is noted where it differs.

## 1. WireGuard + tools
```bash
sudo apt update
sudo apt install -y wireguard wireguard-tools python3 curl unzip git openjdk-17-jdk
# Fedora: sudo dnf install -y wireguard-tools python3 java-17-openjdk-devel
```

## 2. Android Studio
Download the Linux tarball from developer.android.com/studio, then:
```bash
tar -xzf android-studio-*.tar.gz -C ~/
~/android-studio/bin/studio.sh
```
In Android Studio > SDK Manager, install an SDK platform, Platform-Tools,
and an emulator AVD. Then add to `~/.bashrc`:
```bash
export ANDROID_HOME="$HOME/Android/Sdk"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
source ~/.bashrc
adb devices
emulator -list-avds
```

## 3. WireGuard - desktop client (10.8.0.10)
```bash
wg genkey | tee /tmp/desktop-privatekey | wg pubkey
# private key -> your devsp8c.conf, public key -> send to the VPN server admin only
sudo cp wireguard/devsp8c-desktop.conf.example /etc/wireguard/devsp8c.conf
sudo nano /etc/wireguard/devsp8c.conf
# Replace: <DESKTOP_PRIVATE_KEY>, <SERVER_PUBLIC_KEY>, <SERVER_PUBLIC_IP_OR_HOSTNAME>
sudo wg-quick up devsp8c
ping -c 3 10.8.0.1
ip addr show devsp8c
```

## 4. Devsp8c agent (10.8.0.10:18080)
From `desktop-vpn-agent/`:
```bash
export DEVSP8C_AGENT_TOKEN="$(openssl rand -hex 24)"
export DEVSP8C_WORKSPACE="$HOME/Devsp8cProjects"
mkdir -p "$DEVSP8C_WORKSPACE"
python3 agent.py --bind 10.8.0.10 --port 18080
```
Save that token somewhere safe, outside git. Devsp8c needs it for every call.

Test from Devsp8c, once its VPN is also up:
```bash
curl -H "Authorization: Bearer <YOUR_TOKEN>" http://10.8.0.10:18080/status
```

## 5. Optional: systemd user service (so it restarts on login)
Create `~/.config/systemd/user/devsp8c-agent.service`:
```ini
[Unit]
Description=Devsp8c Desktop Agent
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/python3 /home/<you>/desktop-vpn-agent/agent.py --bind 10.8.0.10 --port 18080
Environment=DEVSP8C_AGENT_TOKEN=<YOUR_TOKEN>
Environment=DEVSP8C_WORKSPACE=/home/<you>/Devsp8cProjects
Restart=on-failure

[Install]
WantedBy=default.target
```
Then:
```bash
systemctl --user daemon-reload
systemctl --user enable --now devsp8c-agent
systemctl --user status devsp8c-agent
```
Note: the agent binds to 10.8.0.10, so WireGuard must be up first.
If the service fails at boot, start it after `sudo wg-quick up devsp8c`.

## Troubleshooting, Linux-specific
- `wg-quick up` fails with "RTNETLINK answers: Operation not permitted": you need sudo, and a kernel with WireGuard support (most modern distros have it).
- `adb devices` says "command not found": your PATH edit did not load, or ANDROID_HOME is different. Check `ls ~/Android/Sdk/platform-tools/adb`.
- Agent says "adb not found": same PATH issue, the agent inherits the shell PATH it was started from.
- Devsp8c cannot reach 10.8.0.10:18080: check `wg show` on both ends, `ping 10.8.0.10` from Devsp8c, and that the agent is bound to 10.8.0.10, not 127.0.0.1.
- Firewall: `sudo ufw allow 51820/udp` on the VPN server only if you use UFW. Do not open 18080 to the internet.
