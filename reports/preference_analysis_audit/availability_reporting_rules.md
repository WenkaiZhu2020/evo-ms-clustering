# Availability reporting rules

Every conditional summary uses denominator 30. Unavailable seeds are excluded
from medians, means, IQRs, bootstrap inputs, and external aggregates; they are
not assigned zero and are not replaced by the conservative profile. The source
reports expose eligibility and availability explicitly. Negative realised Q
loss is retained under the frozen unclamped relative-loss formula. Budget
eligibility is `q_loss <= budget + 1e-12`.

The audit does not silently rewrite accepted source reports. Any wording review
flag is recorded in `availability_wording_audit.csv`.
