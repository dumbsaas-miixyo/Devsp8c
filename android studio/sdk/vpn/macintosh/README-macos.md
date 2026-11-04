# Devsp8c on Macintosh (macOS) - exact install

Same design as Linux and Windows: WireGuard (desktop 10.8.0.10) +
Android Studio + Devsp8c agent (10.8.0.10:18080, VPN only, Bearer token).
Devsp8c calls the agent through the VPN, never over the public internet.

## 1. Install the tools

Option A - Homebrew (recommended on macOS):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install --cask android-studio
brew install python git
brew install wireguard-tools
# For the WireGuard GUI app, also get WireGuard from the Mac App Store
# if you prefer a GUI tunnel over the command line.
```

Option B - manual downloads:
- Android Studio for Mac: https://developer.android.com/studio
  (choose Apple Silicon or Intel to match your Mac)
- Python: https://www.python.org/downloads/macos/
- WireGuard for macOS: Mac App Store, or https://www.wireguard.com/install/

## 2. Android Studio setup

Open Android Studio, then in SDK Manager install:
- An Android SDK platform
- Android SDK Platform-Tools (adb)
- Android Emulator, and create an AVD

The SDK is normally at:
```
~/Library/Android/sdk
```

Add adb and emulator to PATH in ~/.zshrc (macOS default shell is zsh):

```bash
cat >> ~/.zshrc << 'EOF'
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
EOF
source ~/.zshrc
adb devices
emulator -list-avds
```

## 3. WireGuard - desktop client (10.8.0.10)

Generate a keypair:

```bash
wg genkey | tee /tmp/desktop-privatekey | wg pubkey
# private key -> your config, public key -> send to the VPN server admin ONLY
```

Copy the template from this repo folder:

```
wireguard/devsp8c-desktop.conf.example
```

Save a copy as `devsp8c.conf`, replace every `<...>` placeholder:
- `<DESKTOP_PRIVATE_KEY>` - your private key, never commit it to git
- `<SERVER_PUBLIC_KEY>` - the VPN server's public key
- `<SERVER_PUBLIC_IP_OR_HOSTNAME>` - the VPN server's address

Bring the tunnel up, either:
- In the WireGuard macOS app: Import Tunnel from File > select `devsp8c.conf` > Activate, or
- From Terminal with wireguard-tools:

```bash
sudo cp devsp8c.conf /opt/homebrew/etc/wireguard/devsp8c.conf
# Intel Macs use /usr/local/etc/wireguard/ instead of /opt/homebrew/etc/wireguard/
sudo wg-quick up devsp8c
ping -c 3 10.8.0.1
ifconfig devsp8c
```

The desktop should then have VPN address 10.8.0.10.

## 4. Devsp8c agent (10.8.0.10:18080)

From the `desktop-vpn-agent` folder, in Terminal:

```bash
export DEVSP8C_AGENT_TOKEN="$(openssl rand -hex 24)"
# Save that token somewhere safe, outside git. Devsp8c needs it for every call.
export DEVSP8C_WORKSPACE="$HOME/Devsp8cProjects"
mkdir -p "$DEVSP8C_WORKSPACE"
python3 agent.py --bind 10.8.0.10 --port 18080
```

Keep that Terminal window open while Devsp8c needs the desktop.
For a permanent setup, use a launchd plist in `~/Library/LaunchAgents/`
that runs the same command on login, with the token in the plist
environment, not in git.

Test from Devsp8c, once its VPN is also up:

```bash
curl -H "Authorization: Bearer <YOUR_TOKEN>" http://10.8.0.10:18080/status
```

## 5. Foreground / background from Devsp8c

Same API as Linux and Windows:

```bash
# Foreground: list devices now
curl -X POST -H "Authorization: Bearer <YOUR_TOKEN>" -H "Content-Type: application/json" \
  -d '{"type":"adb_devices","mode":"foreground"}' http://10.8.0.10:18080/task

# Background: queue a Gradle build, then poll the task id
curl -X POST -H "Authorization: Bearer <YOUR_TOKEN>" -H "Content-Type: application/json" \
  -d '{"type":"gradle_build","project":"MyApp","mode":"background"}' http://10.8.0.10:18080/task
```

Project paths must be inside DEVSP8C_WORKSPACE. `MyApp` means
`~/Devsp8cProjects/MyApp`.

## macOS notes

- Apple Silicon vs Intel matters for Android Studio and for the
  Homebrew path (/opt/homebrew vs /usr/local). Pick the download and
  path that matches your Mac.
- macOS may ask for permission the first time Python listens on a network
  interface, and the first time Android Studio / emulator runs. Allow
  those prompts, or the agent and emulator will fail silently.
- The agent binds to 10.8.0.10 only. Do not bind it to 0.0.0.0, and do
  not port-forward 18080 in your router. VPN-only is the security design.
- If the VPN drops, Devsp8c cannot reach 10.8.0.10:18080 at all.
  That is intentional: no VPN, no remote access.
- Background tasks on macOS: the agent keeps running while its Terminal
  / launchd job is alive. If the Mac sleeps, background Gradle builds
  pause until it wakes.
