# NEA database schema and normalisation analysis

The primary local SQLite store has these entities (see `storage.py`):

| Relation | Primary key | Foreign keys | Other attributes |
|---|---|---|---|
| profiles | id | none | name (unique) |
| strategies | id | profile_id -> profiles.id | name, source, settings (JSON text), created; unique(profile_id,name) |
| runs | id | strategy_id -> strategies.id (nullable) | symbol, timeframe, timestamp, stats_json (JSON text) |
| fills | id | run_id -> runs.id | date, side, price, quantity, pnl |

**Functional dependencies (scalar attributes):** profile id determines profile name; strategy id determines its profile, name, rule source, settings and creation timestamp; run id determines strategy association, instrument, timeframe, timestamp and cached summary; fill id determines its run, date, side, price, quantity and pnl. The additional `(profile_id, name)` unique key identifies a strategy and should be addressed as a candidate key.

**Why the decomposition helps:** profile details are stored once rather than copied into every strategy; strategy definitions are not copied into each run; run attributes are not duplicated across each fill. Primary/foreign key integrity restricts mismatched references and reduces update anomalies. Foreign keys are enabled per connection in `Store.db()`.

**Important qualification:** JSON blobs in `strategies.settings` and `runs.stats_json` embed structured logical values rather than a fully decomposed set of atomic relational columns. This is a deliberate tradeoff for flexible strategy settings and cheap retrieval of derived report metrics. It is defensible for a prototype, but a rigorous claim that *all logical attributes* conform to strict 1NF/3NF would require either clarifying that these are opaque documents or decomposing their inner attributes into separate relational tables. Cached derived statistics are also intentionally redundant with fills/results. The separate historical-price cache has `candles` and `downloads` relations; inspect `data_sources.py` for its compound-key design.

For NEA documentation, present this as a *largely normalised relational core with intentional JSON denormalisation*, unless schema is redesigned and retested. Do not claim strict formal 3NF compliance without discussing this distinction.
