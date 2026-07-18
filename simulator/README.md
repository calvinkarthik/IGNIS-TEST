# IGNIS laptop simulator

The simulator speaks the production 32-byte framed TCP protocol. It is a laptop substitute for the QNX Pi, never a claim of hardware verification.

```powershell
backend\.venv\Scripts\python -m simulator.ignis_simulator.cli --scenario confirmed_fire
backend\.venv\Scripts\python -m simulator.ignis_simulator.cli --scenario inference_failure
backend\.venv\Scripts\python -m simulator.ignis_simulator.cli --scenario confirmed_fire --fault fragmented
```

Available faults: `fragmented`, `coalesced`, `disconnect_reconnect`, `out_of_order`, `invalid_length`, and `invalid_token`.

