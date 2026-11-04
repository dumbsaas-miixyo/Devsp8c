# Devsp8c on Linux - Ubuntu, Fedora, and Arch

Same goal on all three: WireGuard (desktop 10.8.0.10) + Android Studio +
Devsp8c agent (10.8.0.10:18080, VPN only, Bearer token).
Android Studio itself is installed the same way on all three after the
system packages: download the Linux tarball, extract, run studio.sh.

## Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y wireguard wireguard-tools python3 curl unzip git openjdk-17-jdk \
  libc6 libstdc++6 zlib1g libncurses6 libx11-6 libxext6 libxrender1 libxtst6 libxi6 libfreetype6 libxft2
```

## Fedora

```bash
sudo dnf update -y
sudo dnf install -y wireguard-tools python3 curl unzip git java-17-openjdk-devel \
  libstdc++ zlib ncurses-compat-libs libX11 libXext libXrender libXtst libXi freetype libXft
# If wireguard-tools is not in your Fedora repos, enable RPM Fusion first, then retry.
```

## Arch Linux

```bash
sudo pacman -Syu
sudo pacman -S --needed wireguard-tools python curl unzip git jdk17-openjdk \
  gcc-libs zlib ncurses libx11 libxext libxrender libxtst libxi freetype2 libxft
# Arch also has android-studio in the AUR if you prefer: yay -S android-studio
# The tarball method below works on Arch too and avoids AUR maintenance.
```

## Android Studio - all distros

```bash
# Download from https://developer.android.com/studio (Linux tarball)
tar -xzf android-studio-*.tar.gz -C ~/
~/android-studio/bin/studio.sh
```

In Android Studio > SDK Manager install: an SDK platform, Platform-Tools,
Android Emulator, and create an AVD. Then add to ~/.bashrc (or ~/.zshrc):

```bash
export ANDROID_HOME="$HOME/Android/Sdk"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
```

Then reload and test:

```bash
source ~/.bashrc
adb devices
emulator -list-avds
```

## WireGuard - all distros

```bash
wg genkey | tee /tmp/desktop-privatekey | wg pubkey
# private key -> your config, public key -> send to the VPN server admin ONLY
sudo cp wireguard/devsp8c-desktop.conf.example /etc/wireguard/devsp8c.conf
sudo nano /etc/wireguard/devsp8c.conf
# Replace: <DESKTOP_PRIVATE_KEY>, <SERVER_PUBLIC_KEY>, <SERVER_PUBLIC_IP_OR_HOSTNAME>
sudo wg-quick up devsp8c
ping -c 3 10.8.0.1
ip addr show devsp8c
```

## Devsp8c agent - all distros

From the desktop-vpn-agent folder:

```bash
export DEVSP8C_AGENT_TOKEN="$(openssl rand -hex 24)"
export DEVSP8C_WORKSPACE="$HOME/Devsp8cProjects"
mkdir -p "$DEVSP8C_WORKSPACE"
python3 agent.py --bind 10.8.0.10 --port 18080
```

Test from Devsp8c once its VPN is up:

```bash
curl -H "Authorization: Bearer <YOUR_TOKEN>" http://10.8.0.10:18080/status
```

## Distro notes

- Ubuntu: `apt` is the only package step that differs. The rest is identical.
- Fedora: SELinux can block unusual ports. The agent is VPN-only on
  10.8.0.10:18080, so do not open 18080 in firewalld to the internet.
  If `wg-quick` fails, check `sudo dnf install kernel-devel` for your kernel.
- Arch: you must keep the system updated (`pacman -Syu`) before installing
  new packages, or dependency versions can mismatch. AUR android-studio
  is convenient but updates lag the tarball; use the tarball if you want
  the newest Android Studio immediately.
