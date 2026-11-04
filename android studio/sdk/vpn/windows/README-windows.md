# Devsp8c on Windows - exact install

Same design as Linux: WireGuard (desktop 10.8.0.10) + Android Studio +
Devsp8c agent (10.8.0.10:18080, VPN only, Bearer token).
Devsp8c calls the agent through the VPN, never over the public internet.

## 1. Install the tools

Option A - winget (Windows Package Manager, in PowerShell as Administrator):

```powershell
winget install --id WireGuard.WireGuard -e
winget install --id Python.Python.3.12 -e
winget install --id Google.AndroidStudio -e
winget install --id Git.Git -e
```

Option B - manual downloads, if winget is not available:
- WireGuard for Windows: https://www.wireguard.com/install/
- Python 3.12+: https://www.python.org/downloads/windows/
  Tick "Add python.exe to PATH" during install.
- Android Studio: https://developer.android.com/studio
- Git for Windows: https://git-scm.com/download/win

Restart PowerShell after install so PATH updates take effect.

## 2. Android Studio setup

Open Android Studio, then in SDK Manager install:
- An Android SDK platform
- Android SDK Platform-Tools (adb)
- Android Emulator, and create an AVD

The SDK is normally at:
```
%LOCALAPPDATA%\Android\Sdk
```

Add adb and emulator to PATH for the current PowerShell session, and
permanently via System > Environment Variables if you want it every time:

```powershell
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
$env:Path += ";$env:ANDROID_HOME\platform-tools;$env:ANDROID_HOME\emulator"
adb devices
emulator -list-avds
```

## 3. WireGuard - desktop client (10.8.0.10)

Generate a keypair. In PowerShell, with WireGuard installed, you can use
the WireGuard GUI to generate keys, or use `wg` from an Administrator
PowerShell if it is on PATH:

```powershell
wg genkey | Out-File -Encoding ascii $env:TEMP\desktop-privatekey.txt
# Get the public key from that private key in the WireGuard GUI, or:
# wg pubkey < $env:TEMP\desktop-privatekey.txt
```

Copy the template from this repo folder:

```
wireguard\devsp8c-desktop.conf.example
```

Save a copy as `devsp8c.conf`, replace every `<...>` placeholder:
- `<DESKTOP_PRIVATE_KEY>` - your private key, never commit it to git
- `<SERVER_PUBLIC_KEY>` - the VPN server's public key
- `<SERVER_PUBLIC_IP_OR_HOSTNAME>` - the VPN server's address

In the WireGuard Windows app: Import Tunnel from File > select `devsp8c.conf`
> Activate. The desktop should then have VPN address 10.8.0.10.

Test in PowerShell:

```powershell
ping 10.8.0.1
# Also check in WireGuard: the tunnel should show a recent handshake
```

## 4. Devsp8c agent (10.8.0.10:18080)

From the `desktop-vpn-agent` folder, in PowerShell:

```powershell
$env:DEVSP8C_AGENT_TOKEN = -join ((48..57) + (97..102) | Get-Random -Count 48 | ForEach-Object {[char]$_})
# Save that token somewhere safe, outside git. Devsp8c needs it for every call.
$env:DEVSP8C_WORKSPACE = "$env:USERPROFILE\Devsp8cProjects"
New-Item -ItemType Directory -Force -Path $env:DEVSP8C_WORKSPACE | Out-Null
python agent.py --bind 10.8.0.10 --port 18080
```

Keep that PowerShell window open while Devsp8c needs the desktop.
For a permanent setup, run the same command as a Windows Scheduled Task
on logon, with the token stored as a task environment variable, not in git.

Test from Devsp8c, once its VPN is also up:

```powershell
curl -H "Authorization: Bearer <YOUR_TOKEN>" http://10.8.0.10:18080/status
```

## 5. Foreground / background from Devsp8c

Same API as Linux:

```powershell
# Foreground: list devices now
curl -X POST -H "Authorization: Bearer <YOUR_TOKEN>" -H "Content-Type: application/json" `
  -d '{"type":"adb_devices","mode":"foreground"}' http://10.8.0.10:18080/task

# Background: queue a Gradle build, then poll the task id
curl -X POST -H "Authorization: Bearer <YOUR_TOKEN>" -H "Content-Type: application/json" `
  -d '{"type":"gradle_build","project":"MyApp","mode":"background"}' http://10.8.0.10:18080/task
```

Project paths must be inside DEVSP8C_WORKSPACE. `MyApp` means
`%USERPROFILE%\Devsp8cProjects\MyApp`.

## Windows notes

- The agent binds to 10.8.0.10 only. Do not bind it to 0.0.0.0, and do
  not port-forward 18080 in your router. VPN-only is the security design.
- Windows Firewall may prompt the first time Python listens on the VPN
  interface. Allow it for private networks only, not public.
- If Android Studio does not launch from the agent, check that
  `studio64.exe` is on PATH, or open Android Studio once manually first.
- If the VPN drops, Devsp8c cannot reach 10.8.0.10:18080 at all.
  That is intentional: no VPN, no remote access.
