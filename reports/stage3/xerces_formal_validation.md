# Xerces Stage 3 formal validation

This report validates saved formal artifacts only. It makes no Stage 2
versus Stage 3 effectiveness or statistical claim.

- Seeds: 30/30 passed.
- Algorithm fingerprint: `c8d68cdadd19e61b576e487136ec78b8f16f50ef85e4e1bafb732c325818fb3c`.
- Aggregate formal-run SHA-256: `ab6e80eac03841ae0954afea1abd4c7c455fffc2020353dade938c4216ba04f1`.
- Aggregate canonicalization: seed and artifact paths are sorted deterministically;
  timestamps in `run_metadata.json` are excluded before aggregate artifact hashing.
- Seed-0 compatibility: accepted; commit differences are reporting, validation, and launch-record changes only.

## Distribution summary

- Runtime seconds min/mean/median/max: 68.098065 / 69.864617 / 69.629797 / 73.264108
- 4D front size min/mean/median/max: 100 / 100.000 / 100.000 / 100
- Projected front size min/mean/median/max: 72 / 82.767 / 82.500 / 90
- Projected HV min/mean/median/max/std: 0.122724169480 / 0.135617948050 / 0.133867906207 / 0.154916628945 / 0.008861101901
- f_semantic across all 4D rows min/mean/max: 0.378584877780 / 0.680196578357 / 0.984776796626
- Selected cluster-count distribution: `{"29": 2, "30": 8, "31": 20}`.
- Redundancy rho min/mean/median/max: 0.892765633157 / 0.923489059885 / 0.925803746634 / 0.980374978627

## Per-seed results

| seed | runtime (s) | 4D front | projected front | projected HV | selected solution | clusters | selected f_semantic | rho | status |
|---:|---:|---:|---:|---:|---|---:|---:|---:|---|
| 0 | 70.860656 | 100 | 76 | 0.143997162671 | `seed0_solution014` | 30 | 0.382252877133 | 0.903572489405 | PASS |
| 1 | 69.194093 | 100 | 84 | 0.141880997107 | `seed1_solution012` | 30 | 0.383979899147 | 0.928682440355 | PASS |
| 2 | 69.872821 | 100 | 81 | 0.125396853140 | `seed2_solution013` | 31 | 0.380367393250 | 0.925834916010 | PASS |
| 3 | 68.806789 | 100 | 78 | 0.141038129130 | `seed3_solution009` | 31 | 0.383979899147 | 0.953039303930 | PASS |
| 4 | 68.848649 | 100 | 90 | 0.138141856867 | `seed4_solution014` | 31 | 0.382449985917 | 0.919468222040 | PASS |
| 5 | 70.196572 | 100 | 82 | 0.125823219574 | `seed5_solution017` | 31 | 0.382086673709 | 0.892765633157 | PASS |
| 6 | 72.905674 | 100 | 83 | 0.124630590848 | `seed6_solution014` | 31 | 0.382462913976 | 0.937077707771 | PASS |
| 7 | 71.913425 | 100 | 82 | 0.133154405395 | `seed7_solution013` | 31 | 0.380102713398 | 0.927926360211 | PASS |
| 8 | 71.308975 | 100 | 81 | 0.132474390418 | `seed8_solution014` | 30 | 0.380102713398 | 0.912495987091 | PASS |
| 9 | 71.101602 | 100 | 77 | 0.140170014723 | `seed9_solution016` | 31 | 0.382863708029 | 0.892870644304 | PASS |
| 10 | 73.264108 | 100 | 83 | 0.150729809273 | `seed10_solution013` | 31 | 0.382533693302 | 0.935133124111 | PASS |
| 11 | 71.151810 | 100 | 81 | 0.128532679613 | `seed11_solution013` | 31 | 0.383074457113 | 0.926645444485 | PASS |
| 12 | 70.052615 | 100 | 83 | 0.140852391958 | `seed12_solution010` | 30 | 0.383979899147 | 0.942849256280 | PASS |
| 13 | 68.617511 | 100 | 72 | 0.139152989382 | `seed13_solution015` | 29 | 0.383979899147 | 0.910455776949 | PASS |
| 14 | 68.995247 | 100 | 89 | 0.131377996710 | `seed14_solution015` | 30 | 0.380102713398 | 0.906570096430 | PASS |
| 15 | 68.244145 | 100 | 82 | 0.135445074579 | `seed15_solution013` | 31 | 0.383979899147 | 0.925772577258 | PASS |
| 16 | 68.098065 | 100 | 82 | 0.154841916847 | `seed16_solution011` | 30 | 0.382088677482 | 0.924259517066 | PASS |
| 17 | 68.585523 | 100 | 80 | 0.154916628945 | `seed17_solution015` | 31 | 0.382833701111 | 0.904373863630 | PASS |
| 18 | 70.331057 | 100 | 85 | 0.126325202034 | `seed18_solution015` | 31 | 0.383974640760 | 0.911791179118 | PASS |
| 19 | 70.646012 | 100 | 85 | 0.131924179103 | `seed19_solution014` | 31 | 0.382695729922 | 0.939009535011 | PASS |
| 20 | 70.053825 | 100 | 81 | 0.148303097875 | `seed20_solution012` | 29 | 0.393621046982 | 0.930357035704 | PASS |
| 21 | 70.197590 | 100 | 90 | 0.131880611617 | `seed21_solution011` | 31 | 0.389121850075 | 0.929624962496 | PASS |
| 22 | 68.935611 | 100 | 82 | 0.134581407019 | `seed22_solution014` | 31 | 0.379999597603 | 0.932493249325 | PASS |
| 23 | 69.386774 | 100 | 77 | 0.125464396082 | `seed23_solution017` | 31 | 0.382268618645 | 0.908514302516 | PASS |
| 24 | 68.987813 | 100 | 83 | 0.127312807350 | `seed24_solution018` | 31 | 0.382064010771 | 0.898130507446 | PASS |
| 25 | 68.709752 | 100 | 89 | 0.140319180380 | `seed25_solution016` | 31 | 0.382077016956 | 0.906516090722 | PASS |
| 26 | 68.876494 | 100 | 87 | 0.122724169480 | `seed26_solution014` | 30 | 0.380359187013 | 0.932546849983 | PASS |
| 27 | 68.925333 | 100 | 85 | 0.139934086347 | `seed27_solution002` | 31 | 0.383979899147 | 0.980374978627 | PASS |
| 28 | 70.029137 | 100 | 89 | 0.125382927038 | `seed28_solution013` | 31 | 0.381401589475 | 0.947782464941 | PASS |
| 29 | 68.840823 | 100 | 84 | 0.131829269977 | `seed29_solution011` | 30 | 0.383979899147 | 0.917737280168 | PASS |

## Integrity scope

Every 4D front, projected front, Hypervolume, representative selection,
partition scope, objective recomputation, redundancy diagnostic, and
per-artifact hash was independently checked from disk. No Wilcoxon test,
Bonferroni correction, or cross-stage effectiveness conclusion was run.

The launcher lock was removed only after OS process checks confirmed that
no launcher or Xerces runner remained active.
