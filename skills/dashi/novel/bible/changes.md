# Changes (`apply`)

`ops.json` is a list, applied in order, all or nothing. Add `"reason"` to any op; it is logged.

```json
[
 {"op": "add_entity", "entity": {"id": "c_seojin", "kind": "character", "name": "Seojin", "summary": "..."}},
 {"op": "update_entity", "id": "c_seojin", "summary": "new one line", "aliases": ["Jin"]},
 {"op": "set", "id": "c_minseo", "attr": "age", "value": "18", "from_t": 365, "ep": 9},
 {"op": "end", "id": "c_minseo", "attr": "relation:c_seojin", "to_t": 400},
 {"op": "add_event", "event": {"id": "e0050", "t": 402, "ep": 9, "who": ["c_minseo"], "what": "..."}},
 {"op": "add_episode", "episode": {"no": 9, "summary": "...", "ending": "...", "events": ["e0050"]}},
 {"op": "thread_open", "thread": {"id": "t7", "what": "..."}},
 {"op": "thread_close", "id": "t3", "ep": 9},
 {"op": "thread_drop", "id": "t4"},
 {"op": "retire", "id": "c_old", "reason": "removed from story"},
 {"op": "retire", "id": "c_minseo", "attr": "lie"},
 {"op": "prose", "file": "synopsis", "data": {"whole": "..."}},
 {"op": "meta", "now_ep": 9, "now_t": 402}
]
```

- set = change in story (closes the open fact of the same attr, keeps history).
- retire = "never was" (deletes from files, logs once). Use set/end for in-story change.
- Use `--dry-run` to see findings first.

See: checks.
