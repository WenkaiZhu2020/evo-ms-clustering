# Atomic report writes

Reports are written to a same-filesystem temporary file, flushed and fsynced, then atomically replaced. Partial temporary files are distinguishable and are never treated as accepted reports.
