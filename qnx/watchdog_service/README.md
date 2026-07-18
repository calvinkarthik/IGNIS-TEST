# Watchdog service

The watchdog owns edge child processes, detects exits, restarts a service at most three times per 60-second window, and leaves the rest of the system running. The target heartbeat/pulse adapter should extend exit supervision with stale-heartbeat detection. `failure-demo.sh` terminates inference only; the watchdog must report degradation and recovery.

