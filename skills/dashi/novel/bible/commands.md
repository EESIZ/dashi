# Commands

All print one JSON object. Failure: `{"ok": false, "error": "...", "fix": "..."}`; follow `fix`.

| command | does | output keys |
|---|---|---|
| `init DIR --title T [--time-unit day]` | create empty bible | dir |
| `index DIR` | rebuild index.json, validate | entries, problems |
| `at DIR T` | entities alive at T (id, name, summary), last 8 events, open threads | entities, recent_events, open_threads |
| `at DIR T --ids a,b` | full state of those entities at T | items[].attrs |
| `at DIR T --events N` | change how many recent events | |
| `get DIR ID` | one entity/event/thread; `ID` may be an episode number or overview/synopsis/style | item |
| `find DIR TEXT` | search names, aliases, summaries, event text | hits |
| `apply DIR ops.json [--dry-run]` | apply ops atomically; nothing is written on error | applied, written, findings |
| `check DIR` | validation + contradictions | problems, findings |
| `pack DIR [--out FILE]` | whole bible as one JSON for dashi compose `settings` | pack / out |
| `manual [TOPIC]` | this manual | text |

Common errors: `unknown_id` (fix lists similar ids), `duplicate_id`, `invalid_json`, `invalid_bible` (lists problems; nothing written), `op_missing_field`.

See: changes, checks.
