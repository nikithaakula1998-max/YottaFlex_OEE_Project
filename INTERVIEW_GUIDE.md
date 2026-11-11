# Interview guide — say it naturally

**What did you build?** I built a synthetic factory monitoring pipeline. It creates plants, lines, machines, shifts, products and orders, records machine activity and production/quality events, and calculates OEE for each machine and shift.

**Why start with master data?** A production order must point to a real machine, shift and product. Generating parents first prevents invalid references.

**Why append-only events?** If a machine stops and restarts, both transitions matter. Overwriting the latest status would lose the downtime history and make OEE impossible to audit.

**What is availability?** Productive running minutes divided by planned production minutes. We exclude scheduled breaks, but include unexpected downtime in the denominator.

**What is performance?** Ideal time needed to make the recorded units divided by actual running time. It reveals slow operation.

**What is quality?** Good units divided by all produced units. Scrap is bad output; rework is tracked separately.

**Why use fixed seed?** Running the same generator twice should produce the same records and checksums, which makes debugging and evaluation fair.

**How do you handle anomalies?** I label suspect events separately and quarantine them from aggregates instead of silently pretending they are valid.

**What would you improve?** Add rigorous interval sweep overlap detection, complete shift coverage reconciliation, correction events with references, full QC-to-count reconciliation, SQLite persistence, more realistic state distributions and dashboard charts. I would prioritize correctness and tests before visual polish.

**How is this different from the previous supply shortage challenge?** The previous project compared demand with inventory and supplier constraints. This project reconstructs equipment efficiency from time-series events and production/quality outcomes.

**Explain a simple example:** A shift is 480 minutes with 30 planned break minutes. If a machine runs 405 minutes, availability is 405/450 = 90%. If performance is 80% and quality is 95%, OEE is 68.4%.

**Be transparent:** This starter has basic validation and 5 labelled anomaly categories. Some negative scenarios are representative labels and need deeper implementation for a production system. Never claim full-scale results without running the full profile.
