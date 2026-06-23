---
description: Guide to configure Raspberry Pi Zero 2W as a USB-HID Gadget for Black Box AI
---

# Setup Hardware: Raspberry Pi Zero 2W USB Gadget Mode

This guide details how to configure a Raspberry Pi Zero 2W to act as a USB peripheral (Camera/HID Device) using the Linux USB Gadget API (`libcomposite`). This allows the Pi to be plugged into a host computer via USB and emulate a capture device or input device.

## Prerequisites
- Raspberry Pi Zero 2W
- MicroSD Card (Debian Bookworm Lite recommended)
- Micro USB Data Cable (Connect to the USB data port, not the power port)

## Step 1: Enable DWC2 Modules
To enable the USB controller in peripheral mode:

1.  Edit `/boot/firmware/config.txt` (or `/boot/config.txt` on older OS):
    ```ini
    dtoverlay=dwc2
    ```

2.  Edit `/boot/firmware/cmdline.txt`:
    Add `modules-load=dwc2` after `rootwait`.
    ```text
    ... rootwait modules-load=dwc2 ...
    ```

3.  Reboot the Pi:
    ```bash
    sudo reboot
    ```

## Step 2: Enable LibComposite
Ensure the module is loaded:
```bash
sudo echo "libcomposite" >> /etc/modules
sudo modprobe libcomposite
```

## Step 3: Create the Gadget Script
We will create a script to define the USB descriptors.

1.  Create `/usr/bin/blackbox_usb`:
    ```bash
    sudo nano /usr/bin/blackbox_usb
    ```

2.  Add the following content (Bash script):
    ```bash
    #!/bin/bash
    cd /sys/kernel/config/usb_gadget/
    mkdir -p g1
    cd g1

    # Define USB IDs (Custom or Generic)
    echo 0x1d6b > idVendor  # Linux Foundation
    echo 0x0104 > idProduct # Multifunction Composite Gadget
    echo 0x0100 > bcdDevice # v1.0.0
    echo 0x0200 > bcdUSB    # USB 2.0

    # Define English Strings
    mkdir -p strings/0x409
    echo "fedcba9876543210" > strings/0x409/serialnumber
    echo "BlackBox AI" > strings/0x409/manufacturer
    echo "BlackBox Vision Unit" > strings/0x409/product

    # --- Config 1 ---
    mkdir -p configs/c.1/strings/0x409
    echo "Config 1: UVC" > configs/c.1/strings/0x409/configuration
    echo 250 > configs/c.1/MaxPower

    # --- Function: UVC (Video) ---
    # For now, we set up UVC to emulate a webcam.
    # Note: Full UVC setup requires complex descriptor config.
    # We will use the 'uvc-gadget' tool or pre-configured module in future steps.
    # This block enables the interface.
    mkdir -p functions/uvc.usb0
    
    # Link function to config
    ln -s functions/uvc.usb0 configs/c.1/

    # --- Enable the Gadget ---
    ls /sys/class/udc > UDC
    ```

    > **Note**: For full UVC streaming, you will need to configure `uvc.usb0` parameters (streaming/control headers) which is quite verbose. We recommend using [uvc-gadget](https://github.com/wlhe/uvc-gadget) for the actual streaming application once this interface is up.

3.  Make executable:
    ```bash
    sudo chmod +x /usr/bin/blackbox_usb
    ```

## Step 4: Run at Boot
Create a systemd service to initialize the gadget on boot.

1.  Create `/etc/systemd/system/blackbox-usb.service`:
    ```ini
    [Unit]
    Description=Black Box USB Gadget Setup
    After=network.target

    [Service]
    Type=oneshot
    ExecStart=/usr/bin/blackbox_usb
    RemainAfterExit=yes

    [Install]
    WantedBy=multi-user.target
    ```

2.  Enable and Start:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable blackbox-usb
    sudo systemctl start blackbox-usb
    ```

## Verification
Connect the Pi Zero 2W USB **Data Port** (marked USB, not PWR) to your PC.
Run `lsusb` (Linux) or check Device Manager (Windows). You should see "BlackBox Vision Unit".
