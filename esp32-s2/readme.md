# Programming ESP32-S2

## Erase flash
```bash
esptool erase_flash
```

## Program MicroPython
```bash
esptool --baud 460800 write_flash 0x1000 .\ESP32_GENERIC_S2-20250911-v1.26.1.bin
```