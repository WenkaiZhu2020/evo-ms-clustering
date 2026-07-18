# Formal reproducibility spot checks

Registered checks rerun JPetStore seed 7, DayTrader seed 13, and Xerces seed 29 into a temporary destination outside the repository. Scientific output files were compared byte-for-byte; variable runtime metadata, logs, provenance timestamps, and artifact ledgers were excluded.

- jpetstore seed 7: 8/8 scientific files byte-identical — **PASS**.
- daytrader seed 13: 8/8 scientific files byte-identical — **PASS**.
- xerces seed 29: 8/8 scientific files byte-identical — **PASS**.
