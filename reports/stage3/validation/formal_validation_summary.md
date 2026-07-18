# Stage 3B formal seed validation

Seed 0 is the accepted validation output; seeds 1–29 are the formal outputs. Every Stage 3A and Stage 3B result was independently loaded and validated against its frozen contract. No seed 0 formal rerun occurred.

| subject | Stage 3A valid | Stage 3B valid | expected paired seeds |
|---|---:|---:|---:|
| jpetstore | 30 | 30 | 30 |
| daytrader | 30 | 30 | 30 |
| xerces | 30 | 30 | 30 |

Formal result sets are complete only when all 30 paired seed IDs are present and pass. The complete inventory is in `formal_seed_inventory.csv`; the per-seed audit is in `formal_validation_per_seed.csv`.
