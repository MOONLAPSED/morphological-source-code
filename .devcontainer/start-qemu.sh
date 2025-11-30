#!/bin/bash
IMG="/.devcontainer/qemu_image.img"
PORT=12345

qemu-system-x86_64 \
  -enable-kvm \
  -m 4096 \
  -smp 4 \
  -cpu host \
  -device usb-ehci,id=ehci \
  -device usb-kbd \
  -vga std \
  -display sdl,grab=on \
  -k en-us \
  -drive file="$IMG",format=qcow2 \
  -chardev socket,id=ch1,host=127.0.0.1,port=$PORT,server,nowait \
  -device virtserialport,chardev=ch1,name=org.qemu.guest_port.0
