# Workflow

With dashi: `pack DIR --out b.json`, pass the file text as compose `settings`; apply the returned `bible_ops` (save as ops.json, `apply --dry-run`, then `apply`). No bible yet: `init` first, then apply the returned ops.

Write a chapter by hand:
1. `at DIR T` (T = story time of the chapter; default now_t).
2. Pick needed ids; `at DIR T --ids ...` for full state. Unknown name → `find`; still missing → it is new.
3. Write.
4. Ops: add_event per happening, set/end for changes, thread_open/close, add_episode, meta (now_ep, now_t).
5. `apply --dry-run`, read findings, then `apply`.

Retcon: `retire` the old setting, `add_entity`/`set` the new one, run `check` for retired_in_published.

Flashback: events with small t and the current ep; do not move now_t back.
