#!/usr/bin/env python3
"""Story bible indexer. Every command prints one JSON object. Run `bible.py manual` first."""
import difflib
import json
import os
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

DOCS = Path(__file__).resolve().parent / "bible"
KINDS = {"character", "place", "faction", "system", "term", "item"}
PROSE = ("overview", "synopsis", "style")
THREAD_STATUS = {"open", "closed", "dropped"}
# 2026-11-11 user decision: the bible keeps where the story is now, a rough plot flow
# (facts only, reviewed by the user before writing) and managed style rules.
NOW_KEYS = ("ep", "story_time", "place", "situation", "characters", "constants", "prev_ending")
PLOT_STATUS = {"review", "approved"}
BEAT_STATE = {"next", "done", "later"}


SNAPSHOTS = ".snapshots"


def episode_of(ops):
    """The episode an ops list writes: add_episode's no, else the last meta now_ep."""
    if not isinstance(ops, list):
        return None
    for op in ops:
        if isinstance(op, dict) and op.get("op") == "add_episode" and isinstance(op.get("episode"), dict) \
                and isinstance(op["episode"].get("no"), int):
            return op["episode"]["no"]
    eps = [op["now_ep"] for op in ops if isinstance(op, dict) and op.get("op") == "meta" and isinstance(op.get("now_ep"), int)]
    return eps[-1] if eps else None


def snapshot(root, snap):
    """Copy the bible as it is before an episode is applied (once per episode)."""
    if snap.exists():
        shutil.rmtree(snap)
    shutil.copytree(root, snap, ignore=shutil.ignore_patterns(SNAPSHOTS, ".tmp-*"))


def restore(snap, root):
    """Put the bible back to the snapshot, keeping the snapshots themselves."""
    for p in root.iterdir():
        if p.name == SNAPSHOTS:
            continue
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    for p in snap.iterdir():
        (shutil.copytree if p.is_dir() else shutil.copy2)(p, root / p.name)


class Fail(Exception):
    def __init__(self, error, fix="", **extra):
        super().__init__(error)
        self.body = {"ok": False, "error": error, "fix": fix, **extra}


def out(body):
    sys.stdout.write(json.dumps(body, ensure_ascii=False) + "\n")


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise Fail("missing_file", "run init, or check the folder", file=str(path))
    except ValueError as exc:
        raise Fail("invalid_json", "fix the JSON syntax", file=str(path), detail=str(exc)[:200])


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=1)
        stream.write("\n")
    os.replace(tmp, path)


class Bible:
    """Whole bible in memory; save() writes only after validation."""

    def __init__(self, root):
        self.root = Path(root)
        if not (self.root / "bible.json").is_file():
            raise Fail("not_a_bible", "run: bible.py init DIR --title T --time-unit day", dir=str(self.root))
        self.meta = read_json(self.root / "bible.json")
        self.prose = {k: read_json(self.root / (k + ".json")) for k in PROSE if (self.root / (k + ".json")).is_file()}
        self.entities = self._folder("entities")
        self.events = self._folder("events")
        self.episodes = {}
        for p in sorted((self.root / "episodes").glob("*.json")):
            e = read_json(p)
            self.episodes[e.get("no")] = e
        tp = self.root / "threads.json"
        self.threads = read_json(tp) if tp.is_file() else []
        np_ = self.root / "now.json"
        self.now = read_json(np_) if np_.is_file() else {}
        pp = self.root / "plot.json"
        self.plot = read_json(pp) if pp.is_file() else {"status": "review", "beats": []}
        self.changes = []
        self.retired = set()
        log = self.root / "changes.jsonl"
        if log.is_file():
            for line in log.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("op") == "retire" and "attr" not in row:
                    self.retired.add(row.get("id"))

    def _folder(self, name):
        items = {}
        for p in sorted((self.root / name).glob("*.json")):
            item = read_json(p)
            iid = item.get("id")
            if not isinstance(iid, str) or not iid:
                raise Fail("missing_id", "give every item an id", file=str(p))
            if iid in items:
                raise Fail("duplicate_id", "ids must be unique", id=iid, file=str(p))
            if iid + ".json" != p.name:
                raise Fail("id_file_mismatch", "file name must be <id>.json", id=iid, file=str(p))
            items[iid] = item
        return items

    # ---- views
    def ids(self):
        return set(self.entities) | set(self.events) | {t.get("id") for t in self.threads}

    def index(self):
        rows = [{"id": e["id"], "kind": e.get("kind"), "name": e.get("name"), "aliases": e.get("aliases", []),
                 "summary": e.get("summary", ""), "file": "entities/" + e["id"] + ".json"} for e in self.entities.values()]
        rows += [{"id": t["id"], "kind": "thread", "name": t.get("what", ""), "aliases": [],
                  "summary": t.get("status", ""), "file": "threads.json"} for t in self.threads]
        return {"meta": self.meta, "entries": rows,
                "events": len(self.events), "episodes": sorted(k for k in self.episodes if isinstance(k, int))}

    def state(self, eid, t):
        e = self.entities[eid]
        attrs = {}
        for f in e.get("facts", []):
            if f["from_t"] <= t and (f.get("to_t") is None or t < f["to_t"]):
                attrs[f["attr"]] = f["value"]
        return {"id": eid, "kind": e.get("kind"), "name": e.get("name"), "summary": e.get("summary", ""), "attrs": attrs}

    def alive_at(self, eid, t):
        e = self.entities.get(eid)
        if e is None:
            return True
        for f in e.get("facts", []):
            if f["attr"] == "status" and f["value"] in ("dead", "gone") and f["from_t"] <= t and (f.get("to_t") is None or t < f["to_t"]):
                return False
        return True

    # ---- validation
    def validate(self):
        problems = []
        known = self.ids()
        for e in self.entities.values():
            if e.get("kind") not in KINDS:
                problems.append({"id": e["id"], "error": "bad_kind", "fix": "kind is one of " + ",".join(sorted(KINDS))})
            for f in e.get("facts", []):
                if not {"attr", "value", "from_t"} <= set(f):
                    problems.append({"id": e["id"], "error": "bad_fact", "fix": "fact needs attr, value, from_t", "fact": f})
                elif f.get("to_t") is not None and f["to_t"] <= f["from_t"]:
                    problems.append({"id": e["id"], "error": "bad_interval", "fix": "to_t must be greater than from_t", "fact": f})
        for v in self.events.values():
            if not isinstance(v.get("t"), (int, float)):
                problems.append({"id": v["id"], "error": "bad_event_time", "fix": "event needs numeric t"})
            for ref in list(v.get("who", [])) + ([v["place"]] if v.get("place") else []) + list(v.get("causes", [])):
                if ref not in known and ref not in self.retired:  # retired refs are reported by check
                    problems.append({"id": v["id"], "error": "unknown_ref", "ref": ref, "fix": self.suggest(ref)})
        for no, ep in self.episodes.items():
            for ref in ep.get("events", []):
                if ref not in self.events:
                    problems.append({"id": "episode:" + str(no), "error": "unknown_ref", "ref": ref, "fix": self.suggest(ref)})
        for th in self.threads:
            if th.get("status") not in THREAD_STATUS:
                problems.append({"id": th.get("id"), "error": "bad_thread_status", "fix": "status is open, closed or dropped"})
        if not isinstance(self.now, dict) or set(self.now) - set(NOW_KEYS):
            problems.append({"id": "now", "error": "bad_now", "fix": "now keys are " + ", ".join(NOW_KEYS)})
        plot = self.plot
        if not isinstance(plot, dict) or plot.get("status") not in PLOT_STATUS or not isinstance(plot.get("beats"), list):
            problems.append({"id": "plot", "error": "bad_plot", "fix": "plot is {status: review|approved, beats: [...]}"})
        else:
            seen = set()
            for b in plot["beats"]:
                if not isinstance(b, dict) or not isinstance(b.get("id"), str) or not isinstance(b.get("what"), str) \
                        or not b["what"].strip() or b.get("state") not in BEAT_STATE or b["id"] in seen:
                    problems.append({"id": "plot", "error": "bad_beat", "beat": b,
                                     "fix": "beat is {id (unique), what, state: next|done|later}"})
                else:
                    seen.add(b["id"])
        rules = self.prose.get("style", {}).get("rules", [])
        if not isinstance(rules, list) or len({r.get("id") for r in rules if isinstance(r, dict)}) != len(rules) or \
                any(not isinstance(r, dict) or not isinstance(r.get("rule"), str) or not r["rule"].strip() for r in rules):
            problems.append({"id": "style", "error": "bad_style_rules", "fix": "style.rules is [{id (unique), rule, source, active}]"})
        return problems

    def suggest(self, ref):
        ids = [i for i in self.ids() if i]
        near = difflib.get_close_matches(ref, ids, n=5, cutoff=0.5)
        near += [i for i in ids if i not in near and (ref in i or i in ref)]
        named = [e["id"] for e in self.entities.values() if ref in (e.get("name"), *e.get("aliases", []))]
        near = list(dict.fromkeys(named + near))[:5]
        return ("similar ids: " + ", ".join(near)) if near else "add the item first, or fix the id"

    def check(self):
        findings = []
        for e in self.entities.values():
            facts = e.get("facts", [])
            for i, a in enumerate(facts):
                for b in facts[i + 1:]:
                    if a.get("attr") != b.get("attr") or a.get("value") == b.get("value"):
                        continue
                    a_end = a.get("to_t") if a.get("to_t") is not None else float("inf")
                    b_end = b.get("to_t") if b.get("to_t") is not None else float("inf")
                    if a["from_t"] < b_end and b["from_t"] < a_end:
                        findings.append({"type": "overlap", "id": e["id"], "attr": a["attr"],
                                         "values": [a["value"], b["value"]], "fix": "end the older fact (op end) or retire one"})
        seen = {}
        for v in sorted(self.events.values(), key=lambda x: (x.get("t", 0), x["id"])):
            for who in v.get("who", []):
                if not self.alive_at(who, v["t"]):
                    findings.append({"type": "absent_actor", "event": v["id"], "who": who, "t": v["t"],
                                     "fix": "the character is dead/gone at this time"})
                key = (who, v["t"])
                if v.get("place") and key in seen and seen[key][1] != v["place"]:
                    findings.append({"type": "two_places", "who": who, "t": v["t"], "events": [seen[key][0], v["id"]],
                                     "fix": "change one event time or place"})
                seen.setdefault(key, (v["id"], v.get("place")))
            for c in v.get("causes", []):
                cause = self.events.get(c)
                if cause and cause.get("t", 0) > v["t"]:
                    findings.append({"type": "cause_after_effect", "event": v["id"], "cause": c,
                                     "fix": "a cause must not happen after its effect"})
        retired = self.retired
        now_ep = self.meta.get("now_ep", 0) or 0
        for v in self.events.values():
            used = (set(v.get("who", [])) | {v.get("place")}) & retired
            if used and v.get("ep") is not None and v["ep"] <= now_ep:
                findings.append({"type": "retired_in_published", "event": v["id"], "ids": sorted(used),
                                 "fix": "a published chapter uses a retired setting; retcon or restore"})
        return findings

    # ---- changes
    def apply(self, ops):
        if not isinstance(ops, list):
            raise Fail("bad_ops", "ops file is a JSON list of {op:...}")
        for n, op in enumerate(ops):
            try:
                self._apply(op)
            except Fail as exc:
                exc.body["op_index"] = n
                raise
            self.changes.append({"date": date.today().isoformat(), **op})

    def _need(self, op, *keys):
        missing = [k for k in keys if k not in op]
        if missing:
            raise Fail("op_missing_field", "add: " + ", ".join(missing), op=op.get("op"))

    def _entity(self, eid):
        if eid not in self.entities:
            raise Fail("unknown_id", self.suggest(eid), id=eid)
        return self.entities[eid]

    def _apply(self, op):
        kind = op.get("op")
        if kind == "add_entity":
            self._need(op, "entity")
            e = op["entity"]
            if not isinstance(e, dict) or "id" not in e:
                raise Fail("bad_entity", "entity needs id, kind, name")
            if e["id"] in self.ids():
                raise Fail("duplicate_id", "use another id or op set", id=e["id"])
            e.setdefault("aliases", []); e.setdefault("facts", []); e.setdefault("summary", "")
            self.entities[e["id"]] = e
        elif kind == "update_entity":
            self._need(op, "id")
            e = self._entity(op["id"])
            for k in ("name", "aliases", "summary", "kind"):
                if k in op:
                    e[k] = op[k]
        elif kind == "set":
            self._need(op, "id", "attr", "value", "from_t")
            e = self._entity(op["id"])
            for f in e.setdefault("facts", []):
                if f["attr"] == op["attr"] and f.get("to_t") is None and f["from_t"] < op["from_t"]:
                    f["to_t"] = op["from_t"]
            e["facts"].append({"attr": op["attr"], "value": op["value"], "from_t": op["from_t"],
                               "to_t": op.get("to_t"), "since_ep": op.get("ep", self.meta.get("now_ep"))})
        elif kind == "end":
            self._need(op, "id", "attr", "to_t")
            e = self._entity(op["id"])
            open_facts = [f for f in e.get("facts", []) if f["attr"] == op["attr"] and f.get("to_t") is None]
            if not open_facts:
                raise Fail("no_open_fact", "nothing to end for this attr", id=op["id"], attr=op["attr"])
            for f in open_facts:
                f["to_t"] = op["to_t"]
        elif kind == "add_event":
            self._need(op, "event")
            v = op["event"]
            if not isinstance(v, dict) or "id" not in v:
                raise Fail("bad_event", "event needs id, t, what")
            if v["id"] in self.ids():
                raise Fail("duplicate_id", "use another event id", id=v["id"])
            v.setdefault("ep", self.meta.get("now_ep")); v.setdefault("who", []); v.setdefault("causes", [])
            self.events[v["id"]] = v
        elif kind == "add_episode":
            self._need(op, "episode")
            ep = op["episode"]
            if not isinstance(ep, dict) or not isinstance(ep.get("no"), int):
                raise Fail("bad_episode", "episode needs integer no")
            self.episodes[ep["no"]] = ep
        elif kind == "thread_open":
            self._need(op, "thread")
            th = op["thread"]
            if th.get("id") in self.ids():
                raise Fail("duplicate_id", "use another thread id", id=th.get("id"))
            th.setdefault("status", "open"); th.setdefault("planted_ep", self.meta.get("now_ep"))
            self.threads.append(th)
        elif kind in ("thread_close", "thread_drop"):
            self._need(op, "id")
            th = next((t for t in self.threads if t.get("id") == op["id"]), None)
            if th is None:
                raise Fail("unknown_id", self.suggest(op["id"]), id=op["id"])
            th["status"] = "closed" if kind == "thread_close" else "dropped"
            th["closed_ep"] = op.get("ep", self.meta.get("now_ep"))
        elif kind == "retire":
            self._need(op, "id")
            if "attr" in op:
                e = self._entity(op["id"])
                before = [f for f in e.get("facts", []) if f["attr"] == op["attr"]]
                if not before:
                    raise Fail("no_such_attr", "check attr name with get", id=op["id"], attr=op["attr"])
                e["facts"] = [f for f in e["facts"] if f["attr"] != op["attr"]]
                op["before"] = before
            elif op["id"] in self.entities:
                op["before"] = self.entities.pop(op["id"])
                self.retired.add(op["id"])
            elif op["id"] in self.events:
                op["before"] = self.events.pop(op["id"])
                self.retired.add(op["id"])
            else:
                raise Fail("unknown_id", self.suggest(op["id"]), id=op["id"])
        elif kind == "meta":
            for k in ("now_ep", "now_t", "title", "time_unit"):
                if k in op:
                    self.meta[k] = op[k]
        elif kind == "now":
            data = {k: v for k, v in op.items() if k != "op"}
            if not data or set(data) - set(NOW_KEYS):
                raise Fail("bad_now", "now takes any of: " + ", ".join(NOW_KEYS))
            self.now.update(data)
        elif kind == "plot_add":
            self._need(op, "beat")
            b = op["beat"]
            if not isinstance(b, dict) or not isinstance(b.get("what"), str) or not b["what"].strip():
                raise Fail("bad_beat", "beat needs what (one line of fact)")
            beats = self.plot.setdefault("beats", [])
            b = {"id": b.get("id") or "b%03d" % (len(beats) + 1), "what": b["what"], "state": b.get("state", "next")}
            if b["id"] in {x.get("id") for x in beats}:
                raise Fail("duplicate_id", "use another beat id", id=b["id"])
            beats.append(b)
            if self.plot.get("status") == "approved" and op.get("by") != "user":
                self.plot["status"] = "review"
        elif kind == "plot_set":
            self._need(op, "id", "state")
            if op["state"] not in BEAT_STATE:
                raise Fail("bad_beat_state", "state is next, done or later")
            b = next((x for x in self.plot.get("beats", []) if x.get("id") == op["id"]), None)
            if b is None:
                raise Fail("unknown_id", "no such beat", id=op["id"])
            b["state"] = op["state"]
            if op["state"] == "done":
                b["ep"] = op.get("ep", self.meta.get("now_ep"))
            else:
                b.pop("ep", None)
        elif kind == "plot_status":
            self._need(op, "status")
            if op["status"] not in PLOT_STATUS:
                raise Fail("bad_plot_status", "status is review or approved")
            self.plot["status"] = op["status"]
        elif kind == "style_rule_add":
            self._need(op, "rule")
            style = self.prose.setdefault("style", {})
            rules = style.setdefault("rules", [])
            rid = op.get("id") or "r%02d" % (len(rules) + 1)
            if rid in {r.get("id") for r in rules}:
                raise Fail("duplicate_id", "use another rule id", id=rid)
            rules.append({"id": rid, "rule": op["rule"], "source": op.get("source", ""),
                          "since_ep": op.get("ep", self.meta.get("now_ep")), "active": True})
        elif kind == "style_rule_retire":
            self._need(op, "id")
            r = next((x for x in self.prose.get("style", {}).get("rules", []) if x.get("id") == op["id"]), None)
            if r is None:
                raise Fail("unknown_id", "no such style rule", id=op["id"])
            r["active"] = False
        elif kind == "prose":
            self._need(op, "file", "data")
            if op["file"] not in PROSE or not isinstance(op["data"], dict):
                raise Fail("bad_prose", "file is overview, synopsis or style; data is an object")
            self.prose.setdefault(op["file"], {}).update(op["data"])
        else:
            raise Fail("unknown_op", "see: bible.py manual changes", op=kind)

    def save(self):
        problems = self.validate()
        if problems:
            raise Fail("invalid_bible", "nothing was written; fix the listed problems", problems=problems[:20])
        write_json(self.root / "bible.json", self.meta)
        for k, v in self.prose.items():
            write_json(self.root / (k + ".json"), v)
        for folder, items in (("entities", self.entities), ("events", self.events)):
            keep = {i + ".json" for i in items}
            for p in (self.root / folder).glob("*.json"):
                if p.name not in keep:
                    p.unlink()
            for i, item in items.items():
                write_json(self.root / folder / (i + ".json"), item)
        for no, ep in self.episodes.items():
            write_json(self.root / "episodes" / ("%03d.json" % no), ep)
        write_json(self.root / "threads.json", self.threads)
        write_json(self.root / "now.json", self.now)
        write_json(self.root / "plot.json", self.plot)
        if self.changes:
            with (self.root / "changes.jsonl").open("a", encoding="utf-8") as log:
                for row in self.changes:
                    log.write(json.dumps(row, ensure_ascii=False) + "\n")
        write_json(self.root / "index.json", self.index())


def cmd(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        return {"ok": True, "commands": ["init DIR --title T [--time-unit U]", "index DIR", "at DIR T [--ids a,b] [--events N]",
                                         "get DIR ID", "find DIR TEXT", "apply DIR OPS.json [--dry-run]", "check DIR",
                                         "pack DIR [--out FILE]",
                                         "manual [topic]"], "start": "bible.py manual"}
    name, args = argv[0], argv[1:]

    def opt(flag, default=None):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                raise Fail("missing_value", "give a value after " + flag)
            value = args[i + 1]
            del args[i:i + 2]
            return value
        return default

    if name == "manual":
        topic = args[0] if args else "README"
        path = DOCS / (topic + ".md")
        if not path.is_file():
            raise Fail("unknown_topic", "topics: " + ", ".join(sorted(p.stem for p in DOCS.glob("*.md"))))
        return {"ok": True, "topic": topic, "text": path.read_text(encoding="utf-8")}
    if name == "init":
        title, unit = opt("--title", ""), opt("--time-unit", "day")
        if not args:
            raise Fail("missing_dir", "bible.py init DIR --title T")
        root = Path(args[0])
        if (root / "bible.json").exists():
            raise Fail("already_exists", "use apply to change an existing bible", dir=str(root))
        write_json(root / "bible.json", {"title": title, "time_unit": unit, "now_ep": 0, "now_t": 0})
        for k in PROSE:
            write_json(root / (k + ".json"), {})
        for folder in ("entities", "events", "episodes"):
            (root / folder).mkdir(parents=True, exist_ok=True)
        write_json(root / "threads.json", [])
        write_json(root / "now.json", {})
        write_json(root / "plot.json", {"status": "review", "beats": []})
        b = Bible(root)
        write_json(root / "index.json", b.index())
        return {"ok": True, "dir": str(root)}
    if not args:
        raise Fail("missing_dir", "first argument after the command is the bible folder")
    b = Bible(args[0])
    rest = args[1:]
    if name == "index":
        problems = b.validate()
        write_json(b.root / "index.json", b.index())
        return {"ok": not problems, "entries": len(b.entities) + len(b.threads), "problems": problems[:20]}
    if name == "at":
        if not rest:
            raise Fail("missing_time", "bible.py at DIR T")
        t = float(rest[0])
        ids = opt("--ids", None)
        n = int(opt("--events", "8"))
        if ids:
            wanted = [i for i in ids.split(",") if i]
            unknown = [i for i in wanted if i not in b.entities]
            if unknown:
                raise Fail("unknown_id", b.suggest(unknown[0]), ids=unknown)
            return {"ok": True, "t": t, "items": [b.state(i, t) for i in wanted]}
        events = sorted((v for v in b.events.values() if v.get("t", 0) <= t), key=lambda v: v["t"])[-n:]
        return {"ok": True, "t": t, "meta": b.meta,
                "entities": [{"id": i, "kind": e.get("kind"), "name": e.get("name"), "summary": e.get("summary", "")}
                             for i, e in b.entities.items() if b.alive_at(i, t)],
                "recent_events": [{"id": v["id"], "t": v["t"], "what": v.get("what", "")} for v in events],
                "open_threads": [{"id": th["id"], "what": th.get("what", "")} for th in b.threads if th.get("status") == "open"]}
    if name == "get":
        if not rest:
            raise Fail("missing_id", "bible.py get DIR ID")
        i = rest[0]
        for pool in (b.entities, b.events):
            if i in pool:
                return {"ok": True, "item": pool[i]}
        th = next((t for t in b.threads if t.get("id") == i), None)
        if th:
            return {"ok": True, "item": th}
        if i.isdigit() and int(i) in b.episodes:
            return {"ok": True, "item": b.episodes[int(i)]}
        if i in b.prose:
            return {"ok": True, "item": b.prose[i]}
        if i in ("now", "plot"):
            return {"ok": True, "item": getattr(b, i)}
        raise Fail("unknown_id", b.suggest(i), id=i)
    if name == "find":
        q = " ".join(rest).strip()
        if not q:
            raise Fail("missing_text", "bible.py find DIR TEXT")
        hits = [r for r in b.index()["entries"]
                if q in (r["name"] or "") or q in r["summary"] or any(q in a for a in r["aliases"]) or q == r["id"]]
        hits += [{"id": v["id"], "kind": "event", "name": v.get("what", ""), "t": v.get("t")}
                 for v in b.events.values() if q in v.get("what", "")]
        return {"ok": True, "hits": hits[:50]}
    if name == "apply":
        dry = "--dry-run" in rest
        rest = [r for r in rest if r != "--dry-run"]
        if not rest:
            raise Fail("missing_ops", "bible.py apply DIR OPS.json")
        ops = read_json(Path(rest[0]))
        # Applying one episode again (a rewrite) first undoes that episode's previous apply.
        ep = episode_of(ops)
        snap = b.root / SNAPSHOTS / ("ep-%03d" % ep) if ep is not None else None
        replaced = False
        if snap is not None and snap.is_dir():
            now = b.meta.get("now_ep") or 0
            if now > ep:
                raise Fail("episode_not_latest", "episode %d was applied before the later episode %d; "
                           "undo the later episodes first or ask the user" % (ep, now), episode=ep, now_ep=now)
            if now == ep:
                b = Bible(snap)
                replaced = True
        b.apply(ops)
        problems = b.validate()
        if problems:
            raise Fail("invalid_bible", "nothing was written; fix the listed problems", problems=problems[:20])
        if not dry:
            root = Path(args[0])
            if replaced:
                restore(snap, root)
                b.root = root
            elif snap is not None:
                snapshot(root, snap)
            b.save()
        return {"ok": True, "applied": len(b.changes), "written": not dry, "episode": ep,
                "replaced_previous_apply": replaced, "findings": b.check()}
    if name == "pack":
        target = opt("--out", None)
        packed = {"format": "dashi-story-bible", "meta": b.meta, "prose": b.prose, "entities": b.entities,
                  "events": b.events, "episodes": {str(k): v for k, v in b.episodes.items()}, "threads": b.threads,
                  "now": b.now, "plot": b.plot}
        text = json.dumps(packed, ensure_ascii=False)
        if target:
            Path(target).write_text(text, encoding="utf-8")
            return {"ok": True, "out": target, "bytes": len(text.encode("utf-8"))}
        return {"ok": True, "pack": packed}
    if name == "check":
        problems = b.validate()
        findings = b.check()
        return {"ok": not problems and not findings, "problems": problems[:20], "findings": findings[:50]}
    raise Fail("unknown_command", "see: bible.py --help", command=name)


def main():
    try:
        body = cmd(sys.argv[1:])
        out(body)
        return 0 if body.get("ok") else 1
    except Fail as exc:
        out(exc.body)
        return 1
    except (ValueError, TypeError, KeyError) as exc:
        out({"ok": False, "error": "bad_input", "fix": "check the command arguments and file fields", "detail": str(exc)[:200]})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
