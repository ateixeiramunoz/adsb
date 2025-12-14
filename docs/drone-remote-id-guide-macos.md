# Remote ID & DJI DroneID Capture Guide - macOS

> **Purpose**: Guide for testing and experimenting with drone Remote ID capture on macOS (MacBook Pro).
>
> **Important**: macOS has significant limitations for monitor mode. This guide is for **testing only**. For production deployments, use the [Raspberry Pi guide](./drone-remote-id-guide-raspberry-pi.md).
>
> **Last Updated**: December 2024

---

## Table of Contents

1. [Overview & Limitations](#overview--limitations)
2. [Hardware Compatibility](#hardware-compatibility)
3. [Enabling Monitor Mode on macOS](#enabling-monitor-mode-on-macos)
4. [Disabling Monitor Mode Safely](#disabling-monitor-mode-safely)
5. [Capturing Packets](#capturing-packets)
6. [Using Wireshark](#using-wireshark)
7. [RemoteIDReceiver on macOS](#remoteidreceiver-on-macos)
8. [Alternative: Virtual Machine Approach](#alternative-virtual-machine-approach)
9. [Troubleshooting](#troubleshooting)
10. [References](#references)

---

## Overview & Limitations

### macOS Monitor Mode Reality Check

| Feature | macOS Support | Notes |
|---------|---------------|-------|
| Monitor Mode | Partial | Built-in Wi-Fi only, via `airport` utility |
| Packet Capture | Yes | Saved to pcap file, not real-time streaming |
| Packet Injection | No | Apple's drivers don't support injection |
| Real-time Scapy | Limited | Scapy has issues with macOS monitor mode |
| External USB Adapters | Very Limited | Most monitor-mode adapters lack macOS drivers |
| Internet During Capture | No | Wi-Fi disconnects during monitor mode |

### What This Means for Remote ID Capture

1. **You can capture packets** - but to a file, not real-time processing
2. **You lose internet** - your Mac disconnects from Wi-Fi during capture
3. **RemoteIDReceiver won't work directly** - it expects Linux-style monitor mode
4. **Offline analysis works** - capture pcap, analyze later

### Recommendation

For serious Remote ID work, use a **Raspberry Pi**. Use macOS for:
- Quick testing
- Analyzing captured pcap files
- Development and debugging
- Running the web interface while Pi does capture

---

## Hardware Compatibility

### Your MacBook Pro (2022/2023)

| MacBook Pro | Wi-Fi Chip | Monitor Mode |
|-------------|------------|--------------|
| 14" 2021 (M1 Pro/Max) | Apple/Broadcom | Limited |
| 14" 2022 (M2 Pro/Max) | Apple/Broadcom | Limited |
| 14" 2023 (M3 Pro/Max) | Apple/Broadcom | Limited |

All Apple Silicon Macs use similar Broadcom-derived Wi-Fi chips with the same limitations.

### External USB Adapters on macOS

**Bad news**: Most Linux-compatible monitor mode adapters **don't work on macOS** because:
1. No macOS drivers available
2. Apple Silicon (M1/M2/M3) further complicates driver support
3. Even Intel Macs have limited USB Wi-Fi support

| Adapter | macOS Support |
|---------|---------------|
| Alfa AWUS036ACHM | No driver |
| Alfa AWUS036ACH | No driver |
| Panda PAU09 | No driver |
| TP-Link adapters | Mostly no |

**The only reliable option is the built-in Wi-Fi** via Apple's `airport` utility.

---

## Enabling Monitor Mode on macOS

### Method 1: Using `airport` Utility (Recommended)

The `airport` command is Apple's hidden Wi-Fi diagnostic tool.

#### Step 1: Create an Alias (Optional)

```bash
# Add to your ~/.zshrc or ~/.bash_profile
alias airport='/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport'

# Reload shell
source ~/.zshrc
```

#### Step 2: Find Your Wi-Fi Interface

```bash
# List network interfaces
networksetup -listallhardwareports

# Output will show something like:
# Hardware Port: Wi-Fi
# Device: en0
```

Your Wi-Fi interface is typically `en0`.

#### Step 3: Disconnect from Current Network

```bash
# Disassociate from any connected network
sudo airport -z

# Or via networksetup
networksetup -setairportpower en0 off
networksetup -setairportpower en0 on
```

#### Step 4: Start Monitor Mode Capture

```bash
# Start sniffing on channel 6 (common for 2.4 GHz)
sudo airport en0 sniff 6

# For channel 1
sudo airport en0 sniff 1

# For channel 11
sudo airport en0 sniff 11
```

**What happens:**
- Terminal will show: `Capturing 802.11 frames on en0.`
- A pcap file is created at `/tmp/airportSniffXXXXXX.cap`
- Your Mac **loses internet connectivity**
- Press `Ctrl+C` to stop

#### Step 5: Find Your Capture File

```bash
# List capture files
ls -la /tmp/airportSniff*.cap

# Most recent file
ls -t /tmp/airportSniff*.cap | head -1
```

### Method 2: Using Wireshark (GUI)

1. Open **Wireshark**
2. Go to **Capture > Options**
3. Select your Wi-Fi interface (en0)
4. Check **Monitor mode** checkbox
5. Click **Start**

**Note**: This may not work on all macOS versions and requires Wireshark to be installed with the ChmodBPF package.

---

## Disabling Monitor Mode Safely

### Method 1: Stop the Capture (Recommended)

```bash
# If airport is running in foreground
# Just press Ctrl+C

# The interface automatically returns to managed mode
```

### Method 2: Force Reset Wi-Fi

```bash
# Turn Wi-Fi off and on
networksetup -setairportpower en0 off
sleep 2
networksetup -setairportpower en0 on

# Or via System Settings > Wi-Fi > Toggle off/on
```

### Method 3: Network Service Reset

```bash
# If Wi-Fi is stuck
sudo ifconfig en0 down
sudo ifconfig en0 up

# Rejoin your network
networksetup -setairportnetwork en0 "YourNetworkName" "YourPassword"
```

### Method 4: Full Network Reset (Last Resort)

```bash
# Remove network preferences (will forget all saved networks!)
sudo rm /Library/Preferences/SystemConfiguration/com.apple.airport.preferences.plist
sudo rm /Library/Preferences/SystemConfiguration/NetworkInterfaces.plist
sudo rm /Library/Preferences/SystemConfiguration/preferences.plist

# Reboot
sudo reboot
```

### Emergency Recovery

If Wi-Fi is completely broken:
1. Connect via Ethernet (USB-C adapter)
2. Go to **System Settings > Network**
3. Click **Wi-Fi** > **Details** > **Forget This Network** for problematic networks
4. Restart Mac

---

## Capturing Packets

### Quick Capture Script

Create `~/bin/capture-wifi.sh`:

```bash
#!/bin/bash

CHANNEL="${1:-6}"
DURATION="${2:-60}"
OUTPUT_DIR="$HOME/Documents/wifi-captures"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="$OUTPUT_DIR/capture_ch${CHANNEL}_${TIMESTAMP}.pcap"

mkdir -p "$OUTPUT_DIR"

echo "=== Wi-Fi Packet Capture ==="
echo "Channel: $CHANNEL"
echo "Duration: $DURATION seconds"
echo "Output: $OUTPUT_FILE"
echo ""
echo "Starting capture... (Ctrl+C to stop early)"
echo "WARNING: You will lose internet connectivity!"
echo ""

# Disassociate first
sudo /System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -z

# Start capture with timeout
timeout $DURATION sudo /System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport en0 sniff $CHANNEL &
CAPTURE_PID=$!

# Wait for capture to finish or user interrupt
wait $CAPTURE_PID

# Find and move the capture file
LATEST_CAPTURE=$(ls -t /tmp/airportSniff*.cap 2>/dev/null | head -1)
if [ -n "$LATEST_CAPTURE" ]; then
    mv "$LATEST_CAPTURE" "$OUTPUT_FILE"
    echo ""
    echo "Capture saved to: $OUTPUT_FILE"
    echo "File size: $(du -h "$OUTPUT_FILE" | cut -f1)"
else
    echo "No capture file found!"
fi

# Restore Wi-Fi
echo "Restoring Wi-Fi..."
networksetup -setairportpower en0 off
sleep 1
networksetup -setairportpower en0 on

echo "Done!"
```

Make it executable:
```bash
chmod +x ~/bin/capture-wifi.sh
```

Usage:
```bash
# Capture on channel 6 for 60 seconds
~/bin/capture-wifi.sh 6 60

# Capture on channel 1 for 120 seconds
~/bin/capture-wifi.sh 1 120
```

### Multi-Channel Capture Script

Create `~/bin/capture-all-channels.sh`:

```bash
#!/bin/bash

OUTPUT_DIR="$HOME/Documents/wifi-captures"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CHANNELS="1 6 11"  # 2.4 GHz non-overlapping channels
DURATION=30        # Seconds per channel

mkdir -p "$OUTPUT_DIR"

echo "=== Multi-Channel Wi-Fi Capture ==="
echo "Channels: $CHANNELS"
echo "Duration per channel: $DURATION seconds"
echo ""

# Disassociate
sudo /System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -z

for ch in $CHANNELS; do
    echo "Capturing channel $ch..."
    OUTPUT_FILE="$OUTPUT_DIR/capture_ch${ch}_${TIMESTAMP}.pcap"

    timeout $DURATION sudo /System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport en0 sniff $ch &
    wait $!

    LATEST=$(ls -t /tmp/airportSniff*.cap 2>/dev/null | head -1)
    if [ -n "$LATEST" ]; then
        mv "$LATEST" "$OUTPUT_FILE"
        echo "  Saved: $OUTPUT_FILE"
    fi
done

# Restore Wi-Fi
networksetup -setairportpower en0 off
sleep 1
networksetup -setairportpower en0 on

echo ""
echo "All captures complete!"
ls -la "$OUTPUT_DIR"/*_${TIMESTAMP}.pcap
```

---

## Using Wireshark

### Installing Wireshark on macOS

```bash
# Using Homebrew
brew install --cask wireshark

# Or download from https://www.wireshark.org/download.html
```

### Analyzing Captured Files

1. Open Wireshark
2. **File > Open** and select your `.pcap` file
3. Apply filters for Remote ID / Drone traffic

### Useful Wireshark Filters

```
# All beacon frames (Remote ID uses these)
wlan.fc.type_subtype == 0x08

# Vendor-specific action frames
wlan.fc.type_subtype == 0x0d

# Filter by specific OUI (Organizationally Unique Identifier)
wlan.sa[0:3] == 60:60:1f    # Example DJI OUI

# Open Drone ID / Remote ID frames
# Look for NAN (Neighbor Awareness Networking) frames
wlan.fc.type == 0 && wlan.fc.subtype == 13

# Search for specific strings
frame contains "DJI"
```

### Exporting Drone Data

After filtering, you can:
1. **File > Export Specified Packets** - Save filtered results
2. **Statistics > Endpoints** - See all devices
3. **Right-click packet > Follow > Stream** - See full communication

---

## RemoteIDReceiver on macOS

### Why It Doesn't Work Directly

RemoteIDReceiver uses Linux commands:
```python
os.system(f"ip link set {device} down")      # Linux only
os.system(f"iwconfig {device} mode monitor") # Linux only
os.system(f"ip link set {device} up")        # Linux only
```

These don't exist on macOS.

### Workaround: Analyze Pcap Files

You can capture on macOS and analyze with RemoteIDReceiver's parsing:

```bash
# 1. Capture packets (creates pcap file)
sudo airport en0 sniff 6
# Ctrl+C to stop

# 2. Clone RemoteIDReceiver
git clone https://github.com/cyber-defence-campus/RemoteIDReceiver.git
cd RemoteIDReceiver/Receiver

# 3. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Run with pcap file (if supported)
# Check if main.py supports --pcap flag
python3 ./backend/dronesniffer/main.py --help
```

### Workaround: Run Backend Separately

1. **Capture on macOS** - Use `airport` to create pcap files
2. **Transfer to Pi** - Send pcap to Raspberry Pi via SCP
3. **Analyze on Pi** - Process with full RemoteIDReceiver

```bash
# On Mac - capture
sudo airport en0 sniff 6
# Ctrl+C after capturing

# Transfer to Pi
scp /tmp/airportSniff*.cap pi@raspberrypi.local:~/captures/

# On Pi - analyze
cd /opt/RemoteIDReceiver/Receiver
source venv/bin/activate
# Process the pcap file
```

---

## Alternative: Virtual Machine Approach

Run Linux in a VM for full monitor mode support.

### Option 1: UTM (Recommended for Apple Silicon)

1. Download [UTM](https://mac.getutm.app/) (free)
2. Download [Ubuntu ARM64 ISO](https://ubuntu.com/download/server/arm)
3. Create VM with USB passthrough for Wi-Fi adapter

**Limitation**: Most USB Wi-Fi adapters still won't work because of driver issues.

### Option 2: Parallels Desktop

1. Install Parallels Desktop
2. Install Ubuntu Linux
3. Pass through USB adapter
4. Install Linux drivers in VM

### Option 3: Docker (Limited)

Docker on macOS doesn't have access to raw Wi-Fi - **not suitable for monitor mode**.

---

## Troubleshooting

### "Operation not permitted"

```bash
# Grant Terminal full disk access
# System Settings > Privacy & Security > Full Disk Access > Add Terminal

# Or use sudo
sudo airport en0 sniff 6
```

### "airport: command not found"

```bash
# Use full path
/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport

# Or create alias
alias airport='/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport'
```

### Wi-Fi Won't Reconnect After Capture

```bash
# Force reset
networksetup -setairportpower en0 off
sleep 3
networksetup -setairportpower en0 on

# If still stuck, reboot
sudo reboot
```

### No Capture File Created

```bash
# Check if airport is running
ps aux | grep airport

# Check /tmp for files
ls -la /tmp/airportSniff*

# Try running without timeout
sudo airport en0 sniff 6
# Wait a few seconds, then Ctrl+C
```

### Wireshark Can't Enable Monitor Mode

```bash
# Install ChmodBPF
# This should be done during Wireshark installation

# Check if ChmodBPF is running
ls -la /dev/bpf*

# Manually fix permissions
sudo chmod 644 /dev/bpf*
```

### Capture File is Empty

- Make sure there's Wi-Fi activity on the channel
- Try different channels (1, 6, 11)
- Ensure you're close to the signal source
- Check that the capture actually started (no errors)

---

## References

### Apple Documentation

- [Wireless Diagnostics](https://support.apple.com/guide/wireless-diagnostics/welcome/mac)
- [Wi-Fi Network Diagnostics](https://support.apple.com/en-us/HT202663)

### Tools

| Tool | Purpose | Link |
|------|---------|------|
| Wireshark | Packet analysis | [wireshark.org](https://www.wireshark.org/) |
| tcpdump | Command-line capture | Built into macOS |
| airport | Wi-Fi diagnostics | Built into macOS (hidden) |

### Useful Commands Reference

```bash
# Show Wi-Fi info
airport -I

# Scan for networks
airport -s

# Disassociate from network
sudo airport -z

# Start monitor mode capture
sudo airport en0 sniff <channel>

# List network interfaces
networksetup -listallhardwareports

# Toggle Wi-Fi
networksetup -setairportpower en0 off
networksetup -setairportpower en0 on

# Get current channel
airport -I | grep channel
```

---

## Summary: macOS vs Raspberry Pi

| Feature | macOS | Raspberry Pi |
|---------|-------|--------------|
| Monitor Mode | Limited (built-in only) | Full (with USB adapter) |
| Real-time Processing | No | Yes |
| RemoteIDReceiver | Workarounds only | Full support |
| External Adapters | Mostly unsupported | Wide support |
| Production Use | Not recommended | Recommended |
| Testing/Development | Suitable | Suitable |
| Pcap Analysis | Excellent (Wireshark) | Good |

**Bottom Line**: Use macOS for quick tests and analysis. Use Raspberry Pi for actual drone monitoring.

---

*For production deployment, see [Raspberry Pi Guide](./drone-remote-id-guide-raspberry-pi.md)*
