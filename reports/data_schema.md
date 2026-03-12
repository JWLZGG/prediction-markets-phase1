\# Data Schema — Prediction Markets Phase 1



\## 1. Raw market ingestion table

Source: Polymarket Gamma API  

Output file: `data/processed/polymarket\_markets\_raw.parquet`



\### Fields

\- `market\_id`: unique market identifier

\- `question`: market title/question

\- `description`: market description

\- `category`: market category

\- `active`: active flag

\- `closed`: closed flag

\- `archived`: archived flag

\- `volume`: raw volume field

\- `liquidity`: raw liquidity field

\- `end\_date`: market end date/time

\- `created\_at`: market creation timestamp

\- `outcomes`: raw outcomes field

\- `outcome\_prices`: raw outcome prices field

\- `raw\_market`: full raw payload



\## 2. Cleaned market table

Output file: `data/processed/markets.parquet`



\### Fields

\- `market\_id`

\- `platform`

\- `question`

\- `category`

\- `open\_ts`

\- `close\_ts`

\- `duration\_hours`

\- `resolved\_outcome`

\- `label\_status`

\- `volume`

\- `liquidity`



\### Notes

\- `resolved\_outcome` is currently inferred only for high-confidence terminal rows

\- `label\_status` categories:

&nbsp; - `yes\_won`

&nbsp; - `no\_won`

&nbsp; - `double\_zero`

&nbsp; - `ambiguous`

&nbsp; - `invalid`



\## 3. Planned snapshot table

Planned output files:

\- `data/processed/features\_open.parquet`

\- `data/processed/features\_mid.parquet`

\- `data/processed/features\_24h.parquet`



\### Planned fields

\- `market\_id`

\- `platform`

\- `snapshot\_type`

\- `target\_ts`

\- `snapshot\_ts`

\- `time\_to\_resolution\_hours`

\- `market\_implied\_prob`

\- `volume\_to\_date`

\- `open\_interest\_to\_date` (if available)

\- `category`

\- `resolved\_outcome`

\- `label\_status`



\## 4. Labeling logic

Current label source:

\- high-confidence inference from parsed `outcomePrices`



\### High-confidence rules

\- `\[~1, ~0]` => `yes\_won`

\- `\[~0, ~1]` => `no\_won`

\- `\[0, 0]` => `double\_zero`

\- anything else => `ambiguous` or `invalid`



\### Next step

For unresolved rows, derive labels from price-history or token-level historical data using `clobTokenIds`.

