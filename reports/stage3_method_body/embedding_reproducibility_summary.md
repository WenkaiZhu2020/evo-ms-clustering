# Stage 3B embedding reproducibility summary

Canonical and reproducibility runs encoded all three subjects in the same loaded frozen MPS/float16/batch-8 SentenceTransformer runtime. The second run used a separate clean temporary output directory.

Raw `embeddings.npy` bytes, class mappings, per-row embedding hashes, aggregate embedding hashes, token-length files, and metadata excluding explicitly variable timestamps, elapsed times, output paths, and run labels were compared.

Result: byte-identical reproduction passed for JPetStore, DayTrader, and Xerces.

Canonical output root: `/Users/zhuwenkai/Desktop/evo-ms-clustering-stage2-formal/data/embeddings/declaration_method_body`
Reproducibility output root: `/private/tmp/stage3b-embedding-repro.pCJKSX`

No nearest-neighbour file or semantic graph was generated.
