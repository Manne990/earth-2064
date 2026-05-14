#!/usr/bin/env zsh
/Applications/vice-arm64-sdl2-3.10/bin/x64sc \
  -default \
  -rsdev2 "127.0.0.1:25232" \
  -rsdev2ip232 \
  -rsuserbaud 2400 \
  -rsuserdev 1 \
  -userportdevice 2
