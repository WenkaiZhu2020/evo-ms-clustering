# Resume and partial-output safety

The runner does not resume by mixing partial scientific reports. A complete report set is acceptable only when its manifest/source HEAD and frozen source-artifact hashes match; partial, different-head, and different-hash sets are rejected and regenerated into an isolated destination.
