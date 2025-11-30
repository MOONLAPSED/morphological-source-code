@echo off
REM Adjust path to your qemu-system-x86_64 binary and image path
set QEMU=qemu-system-x86_64
set IMG=linux.qcow2
set MEM=4096
set CPU=host
set CORES=4

"%QEMU%" ^
 -enable-kvm ^
 -m %MEM% ^
 -cpu %CPU% ^
 -smp %CORES% ^
 -device usb-ehci,id=ehci ^
 -device usb-kbd ^
 -vga std ^
 -display sdl,grab=on,window-close=on ^
 -k en-us ^
 -netdev user,id=net0,hostfwd=tcp::2222-:22 ^
 -device virtio-net-pci,netdev=net0 ^
 -drive file=%IMG%,format=qcow2,if=virtio
