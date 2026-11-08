# Checks

`check` (also run after `apply`) reports:
- overlap — same entity attr has two values in overlapping intervals.
- absent_actor — a dead/gone character appears in a later event.
- two_places — one character in two places at the same t.
- cause_after_effect — a cause event is later than its effect.
- retired_in_published — a published chapter (ep <= now_ep) uses a retired id.
- problems — bad JSON fields, unknown ids, bad intervals.

Not detected: rule breaks with no named id (e.g. a power used against its rule), tone drift, facts only in prose. Compare those by reading the related entity with `get`.

Findings do not block `apply`; problems do.
