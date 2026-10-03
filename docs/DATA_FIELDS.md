# JARVIS `dft_3d` Field Snapshot (measured 2026-10-04)

Verified live via `jarvis.db.figshare.data("dft_3d")` — 93,902 rows.
Probe output: `docs/data_fields_probe.txt` (git-ignored; regenerate with the probe snippet).

## Fields used by `src/data.py`

| Field | Meaning | Notes |
|---|---|---|
| `jid` | Stable material id (`JVASP-xxxx`) | Pool id space |
| `formula` | Composition string | Input to Magpie/fallback featurization |
| `optb88vdw_bandgap` | Band gap (eV), fully populated | **Target label** — the oracle column |
| `ehull` | Energy above hull (eV/atom), fully populated | Optional stability filter (disabled by default) |

## Measured pool statistics (seed 0, pool=15000)

| Filter | Top-set fraction | n |
|---|---|---|
| gap ∈ [1.2, 1.8], ehull < 0.1 | 0.63% | 94 |
| gap ∈ [1.2, 1.8] | 3.42% | 513 |
| **gap ∈ [1.0, 2.0] (chosen default)** | **5.83%** | **874** |
| gap ∈ [1.0, 2.0], ehull < 0.1 | 0.89% | 134 |

Decision (recorded in spec.md Assumptions + constitution v1.0.1 amendment): ehull filter
disabled by default — stable materials are ~7% of dft_3d so any solar window × ehull<0.1
lands near ~1%, too sparse for clean 10-seed statistics. Ehull is reported post-hoc on the
final shortlist by the Analysis agent.

## Gotchas

- `mbj_bandgap` is string-typed with `'na'` entries — never use it as the label column.
- Full column list lives in the probe output (60+ columns incl. `formation_energy_peratom`,
  `spillage`, `slme`).
