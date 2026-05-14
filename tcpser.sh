#!/usr/bin/env zsh
pkill tcpser

tcpser -v 25232 -p 6400 -S 2400 -l 4 -i"s5=20" \
  -n 2064=127.0.0.1:2064
