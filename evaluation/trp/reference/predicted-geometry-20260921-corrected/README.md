# Bounded geometry of an AlphaFold model

Source: archived AF-P69905-F1 model v6, API metadata and PAE used in F5.
This is a development demonstration on hemoglobin, not a known tandem-repeat
positive and not an independently annotated structural benchmark.

The first execution (`../predicted-geometry-20260921`) used two supplied
segments and failed upstream: a circle cannot be fitted to two centers.
That failure is retained. The adapter now rejects fewer than three units
before starting GeomeTRe. This run partitions the same 10–30 region into
three seven-residue segments. No confidence threshold was changed.

Source inspection retains pLDDT 0–100, original entry identity, AFDB API,
PAE axes and versioned source URLs. A CA-only PDB transports coordinates;
it has no fictitious EXPDTA or PDB HEADER. `afdb` in the raw geometry CSV is
only a transport filename code, not a deposited PDB accession. The manifest
and execution record bind it to AF-P69905-F1. pLDDT stays in the PDB B field
with an explicit REMARK; GeomeTRe's CSV contains geometric angles and TM-score,
not experimental displacement values.

The guard requires the digest of the prepared proposal, rejects changes and
stale outputs, records process failures, and bounds Docker to 2 CPU, 2 GiB,
120 seconds, no network and a read-only container root. The writable output
mount has no aggregate disk quota. This is a standalone trusted CLI route,
not an extension of `trp_prepare/trp_run` or a claim of physical validity.

Reproduce with `script/tesis/predicted_geometry.py prepare` into a fresh directory
and `run --digest` after reviewing its proposal. Requires the pinned local
GeomeTRe image and Gemmi 0.7.5. `execution.json` records the successful run;
`geometry.csv` has three unit rows plus mean and standard deviation.
