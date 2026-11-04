#!/usr/bin/env bash
# Devsp8c Desktop Agent - Linux install (Ubuntu/Debian tested)
# Run on the Linux desktop that will run Android Studio.
# This installs WireGuard, Python, and Android Studio prerequisites.
# It does NOT install your WireGuard private keys - you fill those in
# devsp8c-desktop.conf from the template, and you set your own token.
set -euo pipefail

echo "=== 1. System update + WireGuard + Python ==="
sudo apt update
sudo apt install -y wireguard wireguard-tools python3 python3-pip \
  curl unzip git openjdk-17-jdk libc6 libstdc++6 zlib1g libncurses6 \
  libx11-6 libxext6 libxrender1 libxtst6 libxi6 libfreetype6 libxft2

echo "=== 2. Android Studio ==="
echo "Download Android Studio for Linux from:"
echo "  https://developer.android.com/studio"
echo "Then, for example:"
echo "  tar -xzf android-studio-*.tar.gz -C ~/  # check the real filename"
echo "  ~/android-studio/bin/studio.sh"
echo ""
echo "In Android Studio, use SDK Manager to install:"
echo "  - Android SDK Platform + a system image"
echo "  - Android SDK Platform-Tools (adb)"
echo "  - Android Emulator + an AVD"
echo ""
echo "Then add adb / emulator to PATH in ~/.bashrc or ~/.zshrc:"
echo '  export ANDROID_HOME="$HOME/Android/Sdk"'
echo '  export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"'
echo ""
echo "Test: adb devices   (should list, even if empty, not 'command not found')"
echo "Test: emulator -list-avds"

echo "=== 3. WireGuard client config ==="
echo "Copy the template and edit it:"
echo "  sudo cp wireguard/devsp8c-desktop.conf.example /etc/wireguard/devsp8c.conf"
echo "  sudo nano /etc/wireguard/devsp8c.conf   # replace all <...> placeholders"
echo "Generate a keypair on this desktop if you have not already:"
echo "  wg genkey | tee /tmp/desktop-privatekey | wg pubkey"
echo "  # Put the private key in devsp8c.conf, send ONLY the public key to the server admin"
echo ""
echo "Bring the tunnel up:"
echo "  sudo wg-quick up devsp8c"
echo "  ping -c 3 10.8.0.1    # VPN server"
echo "  ip addr show devsp8c  # should show 10.8.0.10/24"

echo "=== 4. Devsp8c agent ==="
echo "From this folder (desktop-vpn-agent):"
echo '  export DEVSP8C_AGENT_TOKEN="$(openssl rand -hex 24)"  # save this, Devsp8c needs it'
echo '  echo "Your token (save it securely, do not commit it): $DEVSP8C_AGENT_TOKEN"'
echo '  export DEVSP8C_WORKSPACE="$HOME/Devsp8cProjects"'
echo '  mkdir -p "$DEVSP8C_WORKSPACE"'
echo '  python3 agent.py --bind 10.8.0.10 --port 18080'
echo ""
echo "From Devsp8c, test (after VPN is up on both ends):"
echo '  curl -H "Authorization: Bearer <YOUR_TOKEN>" http://10.8.0.10:18080/status'
echo ""
echo "Optional: run the agent as a systemd user service so it survives reboots."
echo "See README-linux.md in this folder for the service file."
