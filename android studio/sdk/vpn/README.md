# Devsp8c Desktop VPN + Android Studio Agent

## The idea in plain terms
Android Studio stays on your desktop. Devsp8c does NOT replace it.
Devsp8c reaches your desktop through a private VPN tunnel, and talks to
a small agent on that desktop. The agent can open projects, list devices,
start an emulator, and run Gradle builds in foreground or background.
Nothing here is exposed to the public internet.

## Network - the IP and port Devsp8c uses

| What | Address / Port | Notes |
|---|---|---|
| VPN subnet | 10.8.0.0/24 | Private only, not routable on the internet |
| VPN server | 10.8.0.1 | WireGuard, UDP 51820 |
| Your desktop (VPN client) | 10.8.0.10 | |
| Devsp8c agent on desktop | **10.8.0.10:18080** | TCP, VPN only, Bearer token required |
| Devsp8c IDE (VPN client) | 10.8.0.20 | |
| ADB on desktop | 127.0.0.1:5037 | Local only, NOT over VPN, NOT public |

So the answer to "what IP and port does Devsp8c use?":
- Tunnel: WireGuard UDP **51820** to the VPN server
- Agent: **http://10.8.0.10:18080** from Devsp8c, with a Bearer token

These are private addresses. They only work when the VPN is up.
Do not port-forward 18080 or 51820 from your router to the internet
unless you know exactly why - the design is VPN-only on purpose.

## Install on a desktop (Windows / macOS / Linux)

1. Install WireGuard from wireguard.com, and Android Studio from
   developer.android.com/studio. In Android Studio, install a JDK,
   an Android SDK, platform-tools (adb), and at least one emulator AVD.
2. Generate WireGuard keys (on the server, and on the desktop):
   ```
   wg genkey | tee privatekey | wg pubkey > publickey
   ```
   Never commit private keys to git. Put them in the WireGuard config
   files only, on each machine.
3. Copy the templates in `wireguard/`:
   - Server: `wg0.conf` on your VPN server (GCP VM, or your own server)
   - Desktop: `devsp8c-desktop.conf` in WireGuard on your desktop
   Replace every `<...>` placeholder, including the server's public IP
   or hostname, and the peer public keys.
4. Bring the tunnel up on both ends. Test from the desktop:
   ```
   ping 10.8.0.1
   ```
   and from Devsp8c:
   ```
   ping 10.8.0.10
   ```
5. On the desktop, set a token and a workspace, then run the agent:
   ```
   export DEVSP8C_AGENT_TOKEN="generate-a-long-random-token"
   export DEVSP8C_WORKSPACE="$HOME/Devsp8cProjects"
   mkdir -p "$DEVSP8C_WORKSPACE"
   python3 agent.py --bind 10.8.0.10 --port 18080
   ```
   Keep that terminal / service running while Devsp8c needs the desktop.
   On Windows, use PowerShell `$env:DEVSP8C_AGENT_TOKEN="..."` and
   `python agent.py --bind 10.8.0.10 --port 18080`.

## Use it from Devsp8c

Foreground - do it now, wait for a quick answer:
```
curl -H "Authorization: Bearer <TOKEN>" http://10.8.0.10:18080/status
curl -X POST -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"type":"adb_devices","mode":"foreground"}' http://10.8.0.10:18080/task
```

Background - queue a long Gradle build, poll for the result:
```
curl -X POST -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"type":"gradle_build","project":"MyApp","mode":"background"}' http://10.8.0.10:18080/task
# -> {"task_id":"..."}
curl -H "Authorization: Bearer <TOKEN>" http://10.8.0.10:18080/task/<task_id>
```

Open a project in Android Studio (foreground launch):
```
curl -X POST -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"type":"open_project","project":"MyApp","mode":"foreground"}' http://10.8.0.10:18080/task
```
Project paths must be inside DEVSP8C_WORKSPACE. `MyApp` means
`$DEVSP8C_WORKSPACE/MyApp`.

## Foreground vs background, honestly
- Foreground in this agent means "launch / run now". It cannot force
  Android Studio to the front on a locked or headless desktop on every OS.
  It launches it and reports success or the error.
- Background means the job is queued and keeps running while Devsp8c
  polls. A Gradle build sent as background will not die when Devsp8c
  disconnects, but it will die if you shut the desktop down.
- If the VPN drops, Devsp8c cannot reach 10.8.0.10:18080 at all.
  That is the kill-switch behaviour you wanted: no VPN, no remote access.

## What to do next, in order
1. Confirm this network plan fits: is 10.8.0.0/24 free on your network,
   or does it clash with something you already use?
2. Tell me your desktop OS (Windows / macOS / Linux) and I will give you
   the exact WireGuard + Android Studio install commands for that OS.
3. Once GitHub repo selection is confirmed, I can push this folder to
   dumbsaas-miixyo/Devsp8c - it is not pushed yet.
