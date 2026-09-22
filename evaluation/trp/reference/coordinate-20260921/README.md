# Explicit residue mapping development reference

This is the existing 2xqh/A development case, not an independent biological
evaluation. Input label intervals are derived from the archived mmCIF mapping
and must recover the original GeomeTRe author intervals exactly.

The mapper checks all 206 requested residues, rejects ambiguous/missing sites,
checks CA coordinates against the target PDB, and refuses noncontiguous author
units. It returns explicit pairs and hashes; it never guesses a numeric offset.

The real Docker execution consumes `mapping.json` intervals and reproduces the
reference CSV byte for byte (12 units). `execution.json` records the command,
image digest, outputs and hashes. This is a standalone preprocessing adapter;
automatic agent integration, SIFTS and predicted models are still pending.

Reproduce the mapper with `script/tesis/map_residue_units.py --help` and its
checks with the Gemmi environment:

```sh
.bioinformatica/trp-python/bin/python -m unittest discover -s script/tesis -p test_residue_units.py
```
