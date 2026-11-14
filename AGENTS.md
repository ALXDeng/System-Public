# AGENTS.md

Instructions for any agent working in this repository. Read this first, then the docs it points to.

## What this project is

A hackathon entry for the System Public Challenge, **Visualize Challenge 3**: which common medications make heat more
dangerous, and what should prescribers and health systems do about it. The deliverable is a visual evidence map built
on the System Public Graph (a knowledge graph of statistical findings extracted from peer-reviewed papers).

The key fact to carry into any work: **direct drug-and-heat evidence in the graph is thin** (about 6 findings in the
CSV snapshot, roughly a dozen once the live API is included). Most of the usable evidence is a two-hop path,
`drug → physiological effect ← heat`.

## Hackathon stance (set by the user, 2026-11-14)

This is a hackathon proof of concept. **The primary goal is to impress the judges.**

- **Be bold.** Thin evidence is usable. One study, an API-only row, or a two-hop bridge can carry a claim. Do not
  drop material or water down the story because the evidence base is small.
- **Stay grounded.** Every claim shown must trace to something real: a row in the graph (CSV or API), a paper, or a
  named outside source. Never invent a number, a study, or a source. "Grounded" is the only hard line.
- **Be aware, don't be paralysed.** When something is noisy, unclear or possibly inaccurate, record it in
  `docs/CAVEATS.md` and carry on. Do not stack hedges onto the presentation itself; keep the caveats in the register
  and in a short methods note, so we can answer if a judge asks.
- **Prefer the impressive option** when two approaches are equally grounded: novelty, clarity and a strong visual
  beat completeness.
- **Check what headlines.** Anything on a headline slide or the main visual gets its abstract checked first
  (PubMed efetch by PMID is quick). That is the one verification step worth the time.

## Read before doing anything

| File | What it tells you |
|---|---|
| `docs/CHALLENGE.md` | The brief, verbatim |
| `docs/DATA.md` | Tables, joins, field completeness, what is missing, traversal quirks |
| `docs/MAPPINGS.md` | The heat, drug-class and bridge vocabularies; concept IDs; what a bridge proves |
| `docs/FINDINGS.md` | Numbered findings with evidence and verification status; open questions |
| `docs/CAVEATS.md` | Register of everything noisy, unclear or possibly inaccurate |
| `docs/LOG.md` | What has been done so far, in order, and what was decided |
| `reference/*.csv` | Concept inventories: drug-side, heat-side, and bridge concepts |

## Documentation rules (mandatory)

The user wants the process and the findings recorded as the work happens, so later sessions can pick up without
re-deriving anything. In every session that changes code, data or conclusions:

1. **Log the process.** Append an entry to `docs/LOG.md`: date, goal, steps taken, decisions and their reasons,
   files touched, what was left undone. Append only; do not rewrite earlier entries.
2. **Record findings.** Add each new result to `docs/FINDINGS.md` with the next F-number, the script or query it came
   from, and an honest status (`verified`, `computed`, `provisional`). If a finding changes, add a new one and mark the
   old one `Superseded by F#`.
3. **Keep the reference docs true.** If a vocabulary, pattern, concept list or data fact changes, update
   `docs/MAPPINGS.md` or `docs/DATA.md` in the same piece of work. Patterns live in code
   (`scripts/heat_meds_lib.py`); the docs describe them and must not drift.
4. **Move answered questions.** When an item under "Open questions" in `FINDINGS.md` is resolved, remove it there and
   record the answer as a finding.
5. **Note anything doubtful.** Add a row to `docs/CAVEATS.md` whenever data, a match, or an extracted value looks
   noisy or possibly wrong. Keep going; the register is for awareness, not a gate.
6. **Log links and inputs the user gives** (URLs, keys' locations, documents) in `docs/LOG.md` and, if they are data
   sources, in `docs/DATA.md`. Never write a secret value into a doc.
7. Do this before reporting the work as done, not as a later clean-up.

## How to work with the data

- The data is not in git. If `data/graph.db` is missing, run `sh scripts/fetch_data.sh` from the repo root
  (1.1 GB download, about a minute to load).
- Only the Python 3.9 standard library is available (no pandas, numpy, matplotlib; no node). Use `sqlite3` and `csv`.
  Charts are hand-written HTML/SVG.
- Run scripts as `python3 -I scripts/<name>.py ...` from the repo root. The downloaded files are untrusted input:
  keep scripts out of `data/`, and pass paths as arguments.
- A full scan of the associations table with the name patterns takes about 3 minutes.
- **API key:** stored in `.env` at the repo root as `SYSTEM_API_KEY` (git-ignored). Never print it, commit it, or
  copy it into docs. Send it as the `x-api-key` header. Limit: **10,000 requests per day**; cache responses
  (`data/api/cache/`) and note in `docs/LOG.md` roughly how many requests a session used.
- **Two sources, different trust.** The CSV snapshot (2.0M findings) is the quality-filtered set. The API (5.9M
  findings) adds ungrounded variables and rows the provider removed for quality. Always carry the `api_status` tag
  (`in_csv`, `api_only_ungrounded`, `api_only_grounded_suspect`) on API rows. API-only rows are usable under the
  hackathon stance, but log them in `docs/CAVEATS.md` terms and check the abstract before headlining.
- API behaviour is documented in `docs/DATA.md` ("Live API"). Docs: https://docs.system.com/system/public/v1.0-api-documentation

## Method rules learned so far

- Find the drug end and the heat end by **variable name**; use **concepts** only for the middle node. Concept-level
  traversal alone loses the heat context.
- **Read the matched rows** before reporting a count as a result. Keyword matches have produced false hits
  ("ARB" as a river basin, insulin as a biomarker, fever control as "temperature").
- Treat edge direction as unreliable. Skip self-loops.
- A bridge is a shared-pathway hypothesis from two different populations. Never present it as evidence that the drug
  and heat interact in one person. Label it in any visual.
- Extracted statistics are mostly unchecked against the papers (the checked ones are listed in `docs/CAVEATS.md` C14).
  Extraction can get the number right and the label wrong, or the reverse; the abstract settles it.
- Absence from the graph is not evidence of absence. Say "not in the graph", not "no evidence".
- Prescriber specialty, guidance documents, storage/stability and absorption evidence are not in the graph. They need
  outside sources, and anything from outside must be labelled as such in the output.

## Scripts

| Script | Purpose | Output |
|---|---|---|
| `scripts/fetch_data.sh` | Download snapshot and build the database | `data/raw/`, `data/graph.db` |
| `scripts/load_sqlite.py` | CSV → SQLite with indexes | `data/graph.db` |
| `scripts/heat_meds_lib.py` | **Source of truth** for heat patterns and drug classes | (library) |
| `scripts/heat_meds.py` | Find direct heat × medication findings | `data/derived/heat_med_findings.csv`, `summary.json`, `storage_findings.csv` |
| `scripts/pathways.py` | Drug class × mechanism and heat × mechanism counts | `data/derived/pathways.json` |
| `scripts/bridges.py` | Concept inventories for traversal | `reference/*.csv` |
| `scripts/api_harvest.py` | Pull every finding touching a heat variable from the live API, tag by `api_status` | `data/api/heat_associations.csv`, `heat_med_api.csv`, `cache/` |
| `scripts/build_explainer.py` + `explainer_template.html` | Build the dataset explainer page | `data-explainer.html` |

`graph-explainer.html` is hand-written; its edge data was copied from SQL output and is not regenerated by any script.

## Previewing pages

`.claude/launch.json` defines a static server named `explainer` on port 8765 serving the repo root.

## Conventions

- Plain language in anything user-facing; the audience for the final visual is clinicians, pharmacists and public
  health officials, not data people.
- Do not commit or push unless the user asks.
- The dataset licence is CC BY-NC 4.0; keep attribution and do not put the raw data in git.
