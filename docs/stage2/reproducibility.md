# Stage 2 Formal Reproducibility Record

This document records what can be verified for the saved final Stage 2
formal results. It distinguishes reproducible verification of the saved
snapshot from an exact computational rerun. Missing evidence is stated
explicitly rather than inferred.

## Canonical Results

The final outputs are the 30-seed directories below, not the historical or
diagnostic siblings under the same subject stage:

```text
results/jpetstore/03_stage2_nsga/robustness_final_30seeds/
results/daytrader/03_stage2_nsga/robustness_final_30seeds/
results/xerces-j/03_stage2_nsga/robustness_final_30seeds/
```

Each manifest records formal seeds `0..29`, a `config_snapshot`, the formal
input hashes, the Stage 1 Leiden partition hash, objective-space bounds, and
the fingerprints listed below.

## Saved-Output Integrity Snapshot

The current saved formal-output snapshot is listed in:

```text
results/cross_subject/03_stage2_nsga/final_statistics/formal_output_sha256sums.txt
```

It contains SHA-256 entries for 546 files across the three final 30-seed
directories. This protects the current saved snapshot from later unnoticed
changes; it was generated after the formal runs and therefore does not replace
a checksum manifest captured at run time.

## Verified Formal Execution Record

All three formal manifests record the following common execution identity:

| Item | Recorded value |
| --- | --- |
| Git commit | `ecfaa3ccb5a589645b719077abdf026aeb246946` |
| Working tree state | dirty; diff SHA-256 `88af6ea9f9a70313294303e9b1210bc10cfb45ab56a4a5bd3beb1891fc3da325` |
| Algorithm config SHA-256 | `37f4f1a096b0e485da87fc9644a7ad874f5654fa46df3bd77bb718e6425330fa` |
| Bounds file SHA-256 | `49957bae212eb06f1e93947ceb82c83aa570f74d73a30a84ba1c1a1b6a8a4c73` |
| Python | `3.13.7` on `macOS-26.5-arm64-arm-64bit-Mach-O` |
| NumPy | `2.4.4` |
| pymoo | `0.6.2` |
| Population / generations | `100` / `100` |
| Formal seed set | `0..29` per subject |

The saved source fingerprints are:

```text
experiments/02_stage2_nsga_structure_only/run.py                9396db54afb426303d558b38c4799f87a8e6ec7e400a0e4251874c25ec2afa4c
experiments/02_stage2_nsga_structure_only/run_robustness.py     d68ce297b43a926b5de3d5681b5d9e59be533eef79b895d9461155fccb585a2d
src/evo_ms/extraction/dependency_extractor.py                   90ac9dc6f653697dae975bc1b1df9318caac862ef9aecc0b5e58d191ca268a1a
src/evo_ms/optimization/encoding.py                             298f68772d293cb92fba1586c51c8331509afbb145392fddf5710c71441a6aa5
src/evo_ms/optimization/objectives.py                           b69801c9b8c234761ef59ca93d70e9668cd3a8fe39886391deff43b4c705ca96
src/evo_ms/optimization/problem.py                              356972e17e8b88c4104296ef9e3bb8d095ae45fa12fd424e50ab30c67f79f643
```

The current versions of those six files can be checked against the saved
manifests with `scripts/reproducibility/verify_stage2_formal_provenance.py`.

## Formal Input Identity

The normalized extraction CSVs are tracked inputs. The saved formal manifests
and the current files agree for `class_nodes.csv` and
`structural_dependencies.csv`.

| Subject | Classes | class_nodes SHA-256 | structural_dependencies SHA-256 | G_raw SHA-256 | Stage 1 Leiden partition SHA-256 |
| --- | ---: | --- | --- | --- | --- |
| JPetStore | 24 | `69b59fef4e0cf7feb7402d14beac895b1790db0906b2b6dc11c54743f431e7e0` | `b3a22590d19437abaef838eb05f7e4801f2f243cea18f52ab3e592e1f3d765c0` | `10327cabac7cc7bd0225b25e8cfd29163a9cc0ba67e11180e04bc88d59c36d80` | `7d48be144ba109eb9029441bc57fd5ab70917333ec9b61fc3063015f73f7b5d5` |
| DayTrader | 53 | `52539293e994a4fadfcb8874a04fbf176dc86a7ef71439d885f5a025d44ad2fd` | `95309d9ae0c21574768ad56eee0710e60f5ffcf66b1a9ddf466095bad0e8b2a0` | `7a93a133db3dc573532ec90a68674d8b8b939c8adc106c64fbd5449db697faef` | `90a727ad67cdb6f3c02b278d77b405b0acd65bb52019939dd3afd822c9132cd6` |
| Xerces-J | 814 | `05f132edcc6b9b1ceaa36e63abcd0707d9b4d000b5e168111a036fea315927f2` | `5e9a30af0b89d61a4aa4d639d9f379f7a50408706b6efad07c9fa028976dd09c` | `3795b4ab2c33a48f521f6242b791bf29f5a1c67364a3938d504594bae9c6a12e` | `d2478f556ca973c25a950bf5341f8a3585e41271cdb4533553da3f181f1d730b` |

## Subject Acquisition Record

The final Stage 2 computation reads the normalized extraction inputs above;
it does not rebuild the Java projects. The raw checkouts are intentionally not
versioned and are absent from this worktree. Therefore, the recorded input
hashes are authoritative for replaying Stage 2, while exact source-to-CSV
re-extraction cannot currently be guaranteed.

| Subject | Acquisition address | Build recipe in repository | Raw checkout revision |
| --- | --- | --- | --- |
| JPetStore | `https://github.com/mybatis/jpetstore-6.git` is the upstream acquisition candidate for the configured `org.mybatis.jpetstore` scope. The formal provenance did not record a URL. | `./mvnw clean package -DskipTests` or `mvn -f pom.xml clean package -DskipTests` | Not recorded; raw checkout absent. |
| DayTrader | `https://github.com/WASdev/sample.daytrader7.git` | `mvn -q -f pom.xml -DskipTests package`, then stage EJB and web classes | Not recorded; raw checkout absent. |
| Xerces-J | `https://github.com/apache/xerces2-j.git` | `build.sh ... clean prepare-src`, then Java 8-targeted `javac` invocation | Not recorded; raw checkout absent. |

The DayTrader and Xerces-J addresses are the defaults in their preparation
scripts. The JPetStore address is an upstream acquisition candidate, not proof
of the historical formal checkout. A future extraction must record each
checkout URL, immutable commit SHA, Java distribution/version, Maven or Ant
version, and the generated CSV hashes before overwriting any input.

## Dependency Evidence and Gap

`requirements.txt` at the formal Git commit is unpinned. A separate branch
commit, `b2ee9d09ab0e43a2c1178c0f0dfa6eb08ec25437`, contains a historical
direct-dependency lock recovered verbatim at:

```text
requirements/historical_stage2_lock_b2ee9d0.txt
```

It is not the final formal environment lock: it specifies NumPy `2.3.5`, while
all final formal manifests record NumPy `2.4.4`. The only package versions
directly evidenced by every formal manifest are retained in:

```text
requirements/stage2_formal_manifest_observed.txt
```

The formal manifests do not record a full `pip freeze`, wheel hashes, or the
versions of pandas, igraph, leidenalg, PyYAML, scipy, networkx, pytest, Java,
Maven, or Ant. Consequently, an exact fresh computational rerun cannot be
claimed from the saved evidence alone. Do not describe the historical lock as
the final formal environment.

## Verification Commands

Validate saved inputs, config/bounds hashes, formal seed layout, and core
source fingerprints without running NSGA-II:

```bash
python scripts/reproducibility/verify_stage2_formal_provenance.py --skip-environment
```

The same command without `--skip-environment` also requires the two recorded
runtime versions, Python `3.13.7`, NumPy `2.4.4`, and pymoo `0.6.2`.

Before any future formal rerun, create and preserve a full environment lock
with `python -m pip freeze --all`, record its SHA-256, pin the three raw source
commits, and run this verifier before writing a new output directory.
