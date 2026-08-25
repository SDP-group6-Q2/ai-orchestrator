# Manuals agent — setup and test questions

## Setup (one-time, and after pulling changes to this file)

1. Make sure a Postgres server is reachable at whatever `POSTGRES_HOST`/`POSTGRES_PORT` you have in `.env` (copy `.env.example` to `.env` and fill in your own credentials if you haven't already).
2. Create the `assistant` database, enable pgvector, and load the fleet dataset:
   ```bash
   python -m src.db.startup
   ```
   Safe to rerun — it skips creating the database/tables if they already exist, but always reloads the xlsx sheet tables from scratch.
3. Run any command below. The **first** query for a given `--machine-id` also indexes that machine's manual PDF (chunks + embeds ~100-260 pages depending on the manual) before answering, so it's noticeably slower than later queries for the same machine.

Add `--show-retrieval` to any command to print the pgvector candidates and the chunks kept after reranking, before the final result — useful for checking *why* an answer came out the way it did.

machine_id → company_id pairs (get this wrong and the request should be rejected — see the tenant-mismatch tests below):

| machine_id | company_id | manual |
| --- | --- | --- |
| MCH-0001, MCH-0002, MCH-0003 | CMP-001 | 15610, 17203, 17579 |
| MCH-0004, MCH-0005 | CMP-003 | 17478, A4344 |
| MCH-0006 | CMP-004 | A2064 |
| MCH-0007, MCH-0008 | CMP-002 | A2055, A2132 |

---

## Tests

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-0004 --company-id CMP-003 --question "What does error E204 mean?"
```

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-0004 --company-id CMP-003 --question "What safety checks should I do before maintenance on this machine?"
```

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-0004 --company-id CMP-003 --question "What is the lubrication schedule for this machine?"
```

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-9999 --company-id CMP-001 --question "What does error E204 mean?"
```

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-0001 --company-id CMP-001 --question "How many closing heads does this machine have?"
```

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-0002 --company-id CMP-001 --question "How do I replace the compensating springs?"
```

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-0002 --company-id CMP-001 --question "What should I do before operating on the caps selection equipment?"
```

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-0007 --company-id CMP-002 --question "What lubricant should I use for this machine?"
```

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-0007 --company-id CMP-002 --question "How do I adjust the threading roller lateral load?"
```

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-0007 --company-id CMP-002 --question "How should this machine be scrapped or disposed of?"
```

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-0004 --company-id CMP-001 --question "What does error E204 mean?"
```

### Real error codes present in the MCH-0004 (17478) manual

E204 does not exist in this manual — the first test above is a genuine negative case, not a mistake. These do exist and should return a grounded, cited answer:

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-0004 --company-id CMP-003 --question "What does error E20 mean?" --show-retrieval
```

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-0004 --company-id CMP-003 --question "What does error E15 mean?"
```

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-0004 --company-id CMP-003 --question "What does error E11 mean?"
```

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-0004 --company-id CMP-003 --question "What does error E10 mean?"
```

### Tenant boundary (mismatched company_id should always be rejected)

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-0007 --company-id CMP-004 --question "What lubricant should I use for this machine?"
```

```bash
python -m src.run_specialist_in_terminal manuals --machine-id MCH-0001 --company-id CMP-002 --question "How many closing heads does this machine have?"
```
