# M5: Omnigraph, O2b on kept connections: batch `m5f-20261116T021553Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `4212c994a384b7a887b34ba6ec88fc5c5afa731a` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 3 (0 races, 0 case suites, 0 visibility)
- Runs added in M5: 0 thread-mode races, 3 O2b cost curves, 0 O6 parity runs, 0 O4 clean-stop transfers
- Harness commits in this batch: `4212c99`

## O2b disjoint-claim cost curve

Measured repetitions only; warm-ups stay in the evidence and are left out here. This is the cost of documented behaviour, not a correctness verdict.

| Engine | Build | Storage | Gate (ms) | N | Valid / measured repetitions | Attempts, median [IQR] | Wasted attempts, median [IQR] | Attempts per agent, median / max (medians) | Time to all claimed, median [IQR] (ms) | Claim latency p50 / p99, medians (ms) | Holder check failed (measured repetitions) | Agents that did not claim (measured repetitions) | Read retries after a dropped kept connection (measured repetitions) | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| omnigraph | v0.15.0 | local | 55 | 1 | 5 / 5 | 1 [1–1] | 0 [0–0] | 1 / 1 | 40.37 [32.89–49.92] | 35.80 / 35.80 | 0 of 5 | 0 | 0 | `20261116T021606Z-a0862379` |
| omnigraph | v0.15.0 | local | 55 | 2 | 5 / 5 | 3 [3–3] | 1 [1–1] | 1.50 / 2 | 84.60 [79.44–87.15] | 38.26 / 38.33 | 0 of 5 | 0 | 0 | `20261116T021606Z-a0862379` |
| omnigraph | v0.15.0 | local | 55 | 5 | 5 / 5 | 15 [15–15] | 10 [10–10] | 3 / 5 | 232.87 [194.70–254.74] | 39.51 / 40.90 | 0 of 5 | 0 | 0 | `20261116T021606Z-a0862379` |
| omnigraph | v0.15.0 | local | 55 | 10 | 5 / 5 | 55 [55–55] | 45 [45–45] | 5.50 / 10 | 698.79 [570.57–734.07] | 63.90 / 80.14 | 0 of 5 | 0 | 0 | `20261116T021606Z-a0862379` |
| omnigraph | v0.15.0 | local | 55 | 25 | 5 / 5 | 325 [325–325] | 300 [300–300] | 13 / 25 | 4213.24 [4022.85–4490.48] | 162.75 / 286.97 | 0 of 5 | 0 | 0 | `20261116T021606Z-a0862379` |
| omnigraph | v0.15.0 | local | 55 | 50 | 5 / 5 | 1269 [1267–1271] | 1219 [1217–1221] | 25.50 / 50 | 18788.19 [18542.11–19316.06] | 395.55 / 651.69 | 0 of 5 | 0 | 0 | `20261116T021606Z-a0862379` |
| omnigraph | edge-b2dbaff | local | 55 | 1 | 5 / 5 | 1 [1–1] | 0 [0–0] | 1 / 1 | 40.02 [31.70–45.84] | 35.09 / 35.09 | 0 of 5 | 0 | 0 | `20261116T022103Z-8b10eb2d` |
| omnigraph | edge-b2dbaff | local | 55 | 2 | 5 / 5 | 3 [3–3] | 1 [1–1] | 1.50 / 2 | 71.83 [69.00–87.43] | 30.73 / 31.67 | 0 of 5 | 0 | 0 | `20261116T022103Z-8b10eb2d` |
| omnigraph | edge-b2dbaff | local | 55 | 5 | 5 / 5 | 15 [15–15] | 10 [10–10] | 3 / 5 | 248.73 [202.85–252.51] | 43.24 / 46.14 | 0 of 5 | 0 | 0 | `20261116T022103Z-8b10eb2d` |
| omnigraph | edge-b2dbaff | local | 55 | 10 | 5 / 5 | 55 [55–55] | 45 [45–45] | 5.50 / 10 | 724.83 [593.53–736.39] | 69.32 / 85.66 | 0 of 5 | 0 | 0 | `20261116T022103Z-8b10eb2d` |
| omnigraph | edge-b2dbaff | local | 55 | 25 | 5 / 5 | 325 [325–325] | 300 [300–300] | 13 / 25 | 3888.41 [3873.20–4137.58] | 157.54 / 286.87 | 0 of 5 | 0 | 0 | `20261116T022103Z-8b10eb2d` |
| omnigraph | edge-b2dbaff | local | 55 | 50 | 5 / 5 | 1264 [1263–1272] | 1214 [1213–1222] | 25.50 / 50 | 19181.40 [18590.94–19740.56] | 392.38 / 666.47 | 0 of 5 | 0 | 0 | `20261116T022103Z-8b10eb2d` |
| falkordb | 6.0.4 (graph module 60004) | – | 40 | 1 | 5 / 5 | 1 [1–1] | 0 [0–0] | 1 / 1 | 0.96 [0.93–1.14] | 0.96 / 0.96 | 0 of 5 | 0 | 0 | `20261116T022558Z-e0fff930` |
| falkordb | 6.0.4 (graph module 60004) | – | 40 | 2 | 5 / 5 | 2 [2–2] | 0 [0–0] | 1 / 1 | 1.40 [1.16–1.54] | 1.31 / 1.31 | 0 of 5 | 0 | 0 | `20261116T022558Z-e0fff930` |
| falkordb | 6.0.4 (graph module 60004) | – | 40 | 5 | 5 / 5 | 5 [5–5] | 0 [0–0] | 1 / 1 | 1.62 [1.59–1.73] | 1.41 / 1.53 | 0 of 5 | 0 | 0 | `20261116T022558Z-e0fff930` |
| falkordb | 6.0.4 (graph module 60004) | – | 40 | 10 | 5 / 5 | 10 [10–10] | 0 [0–0] | 1 / 1 | 2.50 [2.31–2.57] | 1.65 / 2.22 | 0 of 5 | 0 | 0 | `20261116T022558Z-e0fff930` |
| falkordb | 6.0.4 (graph module 60004) | – | 40 | 25 | 5 / 5 | 25 [25–25] | 0 [0–0] | 1 / 1 | 5.07 [4.96–5.26] | 2.77 / 4.19 | 0 of 5 | 0 | 0 | `20261116T022558Z-e0fff930` |
| falkordb | 6.0.4 (graph module 60004) | – | 40 | 50 | 5 / 5 | 50 [50–50] | 1 [0–1] | 1 / 1 | 9.89 [9.77–10.01] | 4.66 / 8.21 | 0 of 5 | 11 (refused) | 0 | `20261116T022558Z-e0fff930` |
