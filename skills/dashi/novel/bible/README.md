# Story bible

A folder of small JSON files plus `bible.py`. Read only what you need.

Start:
1. `bible.py index DIR` — rebuild `index.json`.
2. `bible.py at DIR T` — what is true at story time T. Use this before writing.
3. `bible.py get DIR ID` — one item in full.
4. `bible.py apply DIR ops.json` — the only way to change the bible.
5. `bible.py check DIR` — contradictions.

Never invent a fact the bible may hold: `find` or `get` it first.

Topics (`bible.py manual TOPIC`):
- structure — folders, files, the two time axes
- schema — fields of each file
- commands — every command, output, errors
- changes — ops for apply (add, set, end, retire, threads)
- checks — what check finds and misses
- workflow — writing a chapter, retconning, flashbacks
