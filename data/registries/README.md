# Commercial and evidence registers

The eleven versioned CSV files below retain their **original research vintage** and must not be blindly summed or deduplicated by row count.

| File | Scope |
|---|---|
| V09_evidence_register.csv | Cargo OD research starting evidence |
| V10_evidence_register.csv | China–Magadan–USA network source facts |
| V11_commercial_cards.csv | 30 shipper/carrier/route research cards |
| V11_source_register.csv | 39 dated source cards |
| V12_RFQ_docket.csv | 14 request cases |
| V12_verified_rates.csv | Public carrier rate components |
| V13_RFQ_documents.csv | 15 evidence-gathering requests |
| V13_evidence_quotes.csv | Door-to-door source and rate observations |
| V13_source_register.csv | Source evidence and boundaries |
| V14_RFQ_register.csv | 15 prepared requests, NOT SENT |
| V14_source_register.csv | Source provenance for V14 |

V09, V10 and V11 CSV values were originally displayed by the Files reading connector with table wrappers. The GitHub .csv files had those wrappers removed, and their row and field counts were checked (V09: 17 × 8; V10: 26 × 7; V11 cards: 30 × 20; V11 sources: 39 × 7). These are **semantic CSV conversions**, not guaranteed byte-identical to source files; original byte hashes are in `provenance/` and the separate binary archive.

For canonical fields refer to [schema](../schemas/observation.schema.json) and [evidence rules](../../docs/EVIDENCE_STANDARD.md).
