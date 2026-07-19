#!/bin/sh
cd ~/IGNISv1/IGNIS-TEST
while true; do
  rm -f /dev/shmem/ignis-lcd-writer.lock
  echo "$(date): starting run-poc.sh" >> /tmp/ignis-watchdog.log
  sh poc/pi/run-poc.sh >> /tmp/ignis-run.log 2>&1
  echo "$(date): run-poc.sh exited, restarting in 2s" >> /tmp/ignis-watchdog.log
  sleep 2
done
