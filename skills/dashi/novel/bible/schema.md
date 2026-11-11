# Schema

entity (`entities/<id>.json`, file name = id):
```json
{"id": "c_minseo", "kind": "character", "name": "Minseo", "aliases": ["Min"],
 "summary": "one line",
 "facts": [{"attr": "age", "value": "17", "from_t": 0, "to_t": 365, "since_ep": 1}]}
```
- kind: character, place, faction, system, term, item.
- attr is free text. Common: look, speech, want, need, lie, wound, role, status (`dead`/`gone` hides the entity from `at`), `relation:<id>`, `rule:<name>` for systems.

event (`events/<id>.json`):
```json
{"id": "e0042", "t": 130, "label": "spring, year 3", "ep": 6,
 "place": "p_station", "who": ["c_minseo"], "what": "one line", "causes": ["e0031"]}
```
- place, who, causes must be existing ids.

episode (`episodes/006.json`):
```json
{"no": 6, "summary": "", "ending": "", "events": ["e0042"], "threads_opened": [], "threads_closed": []}
```

thread (item of `threads.json`):
```json
{"id": "t3", "what": "", "planted_ep": 2, "planted_event": "e0010", "payoff_plan": "", "status": "open"}
```
- status: open, closed, dropped.

overview / synopsis / style: free objects.

See: changes.

now.json: {ep, story_time, place, situation, characters: {id: state}, constants: [fixed premises], prev_ending: last ~1500 chars of the previous episode, verbatim}

plot.json: {status: review|approved, beats: [{id, what, state: next|done|later, ep}]}

style.json rules: [{id, rule, source, since_ep, active}]
