"""Cognee scenarios C1, C2, C3, C5 and C6 (target blueprint section 5). C4 is in ladder.py.

Support levels come from Cognee's own words at v1.6.8 (target blueprint section 1.2):

- "Open-source cognee scales vertically, in one process ... More workers or replicas
  against the same data are not coordinated" (.agents/skills/cognee-performance/SKILL.md
  L118-L125): every multi-process scenario is **boundary**;
- several datasets processed at once in one process is a described, capped feature
  (same file L104-L116): in-process concurrency across datasets is **supported**;
- nothing documents what a delete must leave behind beyond its receipt: C6 is **none**.
"""

from __future__ import annotations

from witnessmark.checkers import Check, check_present, check_unique_keys
from witnessmark.history import OK
from witnessmark.memory import Case, CaseSuite, RaceScenario, VisibilityScenario

from .fixtures import Corpus, build, key

AT = "https://github.com/topoteretes/cognee/blob/v1.6.8"
ONE_PROCESS = f"{AT}/.agents/skills/cognee-performance/SKILL.md#L118-L125"
SEVERAL_DATASETS = f"{AT}/.agents/skills/cognee-performance/SKILL.md#L104-L116"
DELETE_RECEIPT = f"{AT}/cognee/api/v1/datasets/datasets.py#L464-L506"
ISSUE_5254 = "https://github.com/topoteretes/cognee/issues/5254"
ISSUE_6559 = "https://github.com/topoteretes/cognee/issues/6559"
WRITERS = "Too many concurrent writers"
UPSERT = f"{AT}/cognee/infrastructure/databases/vector/lancedb/LanceDBAdapter.py#L572-L656"
# Cognee runs the data items of one cognify call concurrently (data_per_batch, default 20), and C0 shows
# that this alone stores duplicate vector rows. The cross-process scenarios cognify one item at a time,
# so what they measure is the concurrency they create, not C0's.
ONE_ITEM = {"data_per_batch": 1}
ERROR_CLASSES = (("ladybug file lock", "Could not set lock on file"), ("lance writer conflict", WRITERS),
                 ("sqlite locked", "database is locked"), ("file not found", "FileNotFoundError"),
                 ("unique constraint", "UNIQUE constraint"), ("integrity error", "IntegrityError"))


def error_class(message: str) -> str:
    for label, needle in ERROR_CLASSES:
        if needle in (message or ""):
            return label
    head = (message or "").split(":", 1)[0].strip()
    return head[:60] or "unknown"


def error_check(ops) -> Check:
    """Not an invariant: what the operations that did not succeed raised, by class (kept in the evidence)."""
    failed = [op for op in ops if op.outcome != OK]
    classes: dict[str, int] = {}
    for op in failed:
        label = error_class((op.error or {}).get("message", ""))
        classes[label] = classes.get(label, 0) + 1
    return Check("ERR", not failed, len(failed), "operations that raised",
                 "; ".join(f"{k} x{v}" for k, v in sorted(classes.items())) or "none",
                 [op.op_id for op in failed])


# --- reading a dump --------------------------------------------------------------------------------------------


def _nodes(state: dict, kind: str) -> dict[str, int]:
    return dict((state.get("graph") or {}).get("nodes", {}).get(kind, {}))


def _tag_counts(state: dict, kind: str) -> dict[str, int]:
    """Chunk, document and summary nodes per tag (a chunk key may list several tags)."""
    counts: dict[str, int] = {}
    for label, count in _nodes(state, kind).items():
        for tag in label.split(","):
            counts[tag] = counts.get(tag, 0) + count
    return counts


def _relations(state: dict) -> dict[str, int]:
    found = {}
    for label, count in (state.get("graph") or {}).get("edges", {}).items():
        source, relation, target = label.split("|", 2)
        if source.startswith("Entity:") and target.startswith("Entity:"):
            found[f"{source[7:]}|{relation}|{target[7:]}"] = count
    return found


def _rows(state: dict) -> dict[str, list[dict]]:
    rows: dict[str, list[dict]] = {}
    for row in state.get("relational", []):
        for tag in row["tags"] or ["?"]:
            rows.setdefault(tag, []).append(row)
    return rows


def _vector_duplicates(state: dict) -> dict[str, int]:
    return {name: value["max_rows_per_id"] for name, value in (state.get("vector") or {}).items()
            if isinstance(value, dict) and "max_rows_per_id" in value}


def _dangling(state: dict) -> tuple[int, int, int]:
    vector = state.get("vector") or {}
    without_node = sum(v.get("without_graph_node", 0) for v in vector.values() if isinstance(v, dict))
    without_vector = sum((vector.get("graph_nodes_without_vector") or {}).values())
    return (state.get("graph") or {}).get("orphan_edges", 0), without_node, without_vector


def store_checks(corpus: Corpus, tags: list[str], state: dict, where: str) -> list[Check]:
    """I1 Form B, I2 and I4 across stores for the documents ``tags`` (target blueprint section 6)."""
    entities = _nodes(state, "Entity")
    vector_rows = _vector_duplicates(state)
    orphans, without_node, without_vector = _dangling(state)
    rows = _rows(state)
    files_missing = [t for t in tags for r in rows.get(t, []) if r["raw_exists"] is False or r["original_exists"] is False]
    checks = [
        check_unique_keys(entities, f"entities in {where}"),
        Check("I1B", all(v <= 1 for v in vector_rows.values()), max(vector_rows.values(), default=0),
              "rows per vector id",
              "; ".join(f"{n}: up to {v} rows per id" for n, v in sorted(vector_rows.items()) if v > 1)
              or f"one row per id in {len(vector_rows)} collections"),
        check_present(sorted(corpus.entity_keys(tags)), set(entities), f"entities in {where}"),
        check_present(sorted(corpus.relation_keys(tags)), set(_relations(state)), f"relations in {where}"),
        check_present(sorted(tags), set(_tag_counts(state, "DocumentChunk")), f"chunks in {where}"),
        check_present(sorted(tags), set(rows), f"data rows in {where}"),
        Check("I2", not files_missing, len(files_missing), "rows whose stored file is gone",
              f"rows pointing at missing files: {files_missing[:5]}" if files_missing
              else "every row's stored files exist", files_missing[:20]),
        Check("I4", not (orphans or without_node or without_vector), orphans + without_node + without_vector,
              "artefacts in one store only",
              f"{orphans} edges with a missing endpoint, {without_node} vectors without a graph node, "
              f"{without_vector} graph nodes without a vector"),
    ]
    return checks


def exact_graph(corpus: Corpus, tags: list[str], state: dict, absent: list[str] = ()) -> list[str]:
    """Differences from the fixture graph: the sequential control must show none."""
    problems = []
    entities = _nodes(state, "Entity")
    want = corpus.entity_keys(tags)
    if set(entities) != want or any(v != 1 for v in entities.values()):
        problems.append(f"entities {sorted(entities.items())[:8]} (want {len(want)}, one each)")
    relations = _relations(state)
    if set(relations) != corpus.relation_keys(tags) or any(v != 1 for v in relations.values()):
        problems.append(f"relations {len(relations)} (want {len(corpus.relation_keys(tags))}, one each)")
    types = set(_nodes(state, "EntityType"))
    want_types = {key(e.type) for t in tags for e in corpus.doc(t).entities}
    if types != want_types:
        problems.append(f"entity types {sorted(types)} (want {sorted(want_types)})")
    for kind in ("DocumentChunk", "TextDocument", "TextSummary"):
        counts = _tag_counts(state, kind)
        if set(counts) != set(tags) or any(v != 1 for v in counts.values()):
            problems.append(f"{kind}: {len(counts)} tags, {sum(counts.values())} nodes (want {len(tags)}, one each)")
    provenance = state.get("provenance") or {}
    wrong = [t for t in tags if sorted(provenance.get(t, [])) != sorted(key(e.name) for e in corpus.doc(t).entities)]
    if wrong:
        problems.append(f"chunk provenance differs for {wrong[:5]}")
    rows = _rows(state)
    if set(rows) != set(tags) or any(len(v) != 1 for v in rows.values()):
        problems.append(f"data rows for {sorted(rows)[:6]} (want {len(tags)}, one each)")
    if any(r["raw_exists"] is not True for v in rows.values() for r in v):
        problems.append("a row's stored file is missing")
    leftovers = [t for t in absent if t in _tag_counts(state, "DocumentChunk") or t in rows]
    if leftovers:
        problems.append(f"deleted documents still present: {leftovers}")
    if any(v > 1 for v in _vector_duplicates(state).values()):
        problems.append(f"duplicate vector ids {_vector_duplicates(state)}")
    if any(_dangling(state)):
        problems.append("orphan edges {} / vectors without nodes {} / nodes without vectors {}".format(*_dangling(state)))
    return problems


def _errors(ops) -> list[str]:
    return [(op.error or {}).get("message", "") for op in ops if op.outcome != OK]


# --- C1: several workers, one dataset --------------------------------------------------------------------------


class C1OneDataset(RaceScenario):
    """K worker processes add overlapping slices of one corpus to one dataset, then each cognifies it."""

    invariants = ("I1B", "I2", "I4")
    support = "boundary"
    basis = "documented"
    basis_ref = ONE_PROCESS
    GROUP = "wm_c1"
    OVERLAP = 2

    def __init__(self, workers: int):
        self.workers = workers
        self.id = f"c1.k{workers}"
        self.corpus = build("c1")

    def slices(self) -> list[list[str]]:
        tags = [doc.tag for doc in self.corpus.docs]
        size = len(tags) // self.workers
        out = []
        for i in range(self.workers):
            nxt = ((i + 1) % self.workers) * size
            out.append(tags[i * size:(i + 1) * size] + tags[nxt:nxt + self.OVERLAP])
        return out

    def params(self):
        return {"corpus": self.corpus.name, "documents": len(self.corpus.docs), "workers": self.workers,
                "overlap": self.OVERLAP, "slices": self.slices()}

    def clients(self):
        # Adds first, then cognifies: with K processes, client i and client K+i land in worker i, in order.
        return ([(self.GROUP, {"entry": "add", "tags": share}) for share in self.slices()]
                + [(self.GROUP, {"entry": "cognify", "worker": i, **ONE_ITEM}) for i in range(self.workers)])

    @staticmethod
    def acknowledged(ops) -> tuple[list[str], list[str]]:
        """(documents whose add was acknowledged, those of them a later acknowledged cognify covered)."""
        adds = [op for op in ops if op.outcome == OK and op.input.get("entry") == "add"]
        cognifies = [op for op in ops if op.outcome == OK and op.input.get("entry") == "cognify"]
        added = sorted({t for op in adds for t in op.input["tags"]})
        covered = sorted({t for op in adds for t in op.input["tags"]
                          if any(c.inv.mono_ns > op.ret.mono_ns for c in cognifies)})
        return added, covered

    def check(self, ops, states):
        added, covered = self.acknowledged(ops)
        state = states[self.GROUP]
        checks = store_checks(self.corpus, covered, state, self.GROUP)
        checks.append(check_present(added, set(_rows(state)), f"rows of acknowledged adds in {self.GROUP}"))
        checks.append(error_check(ops))
        return checks

    def sequential_expected(self, ops, states):
        tags = [doc.tag for doc in self.corpus.docs]
        problems = exact_graph(self.corpus, tags, states[self.GROUP]) + _errors(ops)
        return (not problems and all(op.outcome == OK for op in ops),
                f"the fixture graph exactly: {len(self.corpus.entity_keys(tags))} entities and "
                f"{len(self.corpus.relation_keys(tags))} relations once each; one chunk, document, summary and row "
                f"per document ({len(tags)}); no duplicates, orphans or one-store artefacts",
                "; ".join(problems) or "as expected")


class C1Disjoint(C1OneDataset):
    """Control: the same K workers, each on its own dataset with its own documents."""

    def __init__(self, workers: int):
        super().__init__(workers)
        self.id = f"c1.disjoint.k{workers}"

    def slices(self):
        tags = [doc.tag for doc in self.corpus.docs]
        size = len(tags) // self.workers
        return [tags[i * size:(i + 1) * size] for i in range(self.workers)]

    def groups(self):
        return [f"wm_c1d_{i}" for i in range(self.workers)]

    def clients(self):
        return ([(f"wm_c1d_{i}", {"entry": "add", "tags": share}) for i, share in enumerate(self.slices())]
                + [(f"wm_c1d_{i}", {"entry": "cognify", "worker": i, **ONE_ITEM}) for i in range(self.workers)])

    def check(self, ops, states):
        checks = []
        for group in self.groups():
            mine = [op for op in ops if op.input["group"] == group]
            _added, covered = self.acknowledged(mine)
            checks += store_checks(self.corpus, covered, states[group], group)
        checks.append(error_check(ops))
        return checks

    def sequential_expected(self, ops, states):
        problems = []
        for share, group in zip(self.slices(), self.groups()):
            problems += [f"{group}: {p}" for p in exact_graph(self.corpus, share, states[group])]
        problems += _errors(ops)
        return (not problems, "each dataset holds exactly its own slice's fixture graph",
                "; ".join(problems) or "as expected")


# --- C2: concurrent vector writers and a delete (#5254) --------------------------------------------------------


class C2Writers(RaceScenario):
    """Two processes cognify different datasets on one shared store while a third deletes a third dataset's data."""

    id = "c2.writers"
    invariants = ("I1B", "I2", "I4", "I5")
    support = "boundary"
    basis = "issue"
    basis_ref = ISSUE_5254
    A, B, C = "wm_c2_a", "wm_c2_b", "wm_c2_c"

    def __init__(self):
        self.corpus = build("c2")
        self.tags = {g: [d.tag for d in self.corpus.docs if d.tag.startswith(p)]
                     for g, p in ((self.A, "C2A"), (self.B, "C2B"), (self.C, "C2C"))}

    def params(self):
        return {"corpus": "c2", "datasets": self.tags, "store": "one store shared by every dataset "
                "(ENABLE_BACKEND_ACCESS_CONTROL=false)", "omitted": "memify (no model fixture for its prompts)"}

    def groups(self):
        return [self.A, self.B, self.C]

    async def setup(self, target, group):
        if group == self.C:
            await target.ingest({"entry": "add_cognify", "tags": self.tags[self.C], **ONE_ITEM}, self.C)

    def clients(self):
        return [(self.A, {"entry": "add_cognify", "tags": self.tags[self.A], **ONE_ITEM}),
                (self.B, {"entry": "add_cognify", "tags": self.tags[self.B], **ONE_ITEM}),
                (self.C, {"entry": "delete", "tags": self.tags[self.C]})]

    def check(self, ops, states):
        store = states[self.A]
        acknowledged = sorted({t for op in ops if op.outcome == OK and op.input.get("entry") == "add_cognify"
                               for t in op.input["tags"]})
        checks = store_checks(self.corpus, acknowledged, store, "the shared store")
        conflicts = [op.op_id for op in ops if WRITERS in ((op.error or {}).get("message") or "")]
        checks.append(Check("C2W", not conflicts, len(conflicts), "operations failed with writer conflicts",
                            f"{len(conflicts)} operation(s) failed with '{WRITERS}'" if conflicts
                            else "no writer conflicts", conflicts))
        chunks, rows = _tag_counts(store, "DocumentChunk"), _rows(states[self.A]) | _rows(states[self.B])
        attempted = self.tags[self.A] + self.tags[self.B]
        partial = [t for t in attempted if (t in rows) != (t in chunks)]
        checks.append(Check("C2P", not partial, len(partial), "partially indexed documents",
                            f"documents with a row but no chunk, or a chunk but no row: {partial[:6]}" if partial
                            else "every document is either fully indexed or absent", partial))
        checks.append(error_check(ops))
        delete_ok = any(op.outcome == OK and op.input.get("entry") == "delete" for op in ops)
        left = [t for t in self.tags[self.C] if t in chunks or t in _rows(states[self.C])] if delete_ok else []
        checks.append(Check("I5", not left, len(left), "deleted documents still present",
                            f"after an acknowledged delete, still present: {left[:6]}" if left
                            else "nothing of the deleted documents remains" if delete_ok else "the delete failed",
                            left))
        return checks

    def sequential_expected(self, ops, states):
        kept = self.tags[self.A] + self.tags[self.B]
        state = dict(states[self.A])
        state["relational"] = states[self.A]["relational"] + states[self.B]["relational"] + states[self.C]["relational"]
        problems = exact_graph(self.corpus, kept, state, absent=self.tags[self.C]) + _errors(ops)
        return (not problems, "the shared store holds exactly A's and B's fixture graph; nothing of C remains",
                "; ".join(problems) or "as expected")


# --- C3: add and delete on one stored file (#6559) -------------------------------------------------------------

OFFSETS_MS = list(range(-50, 130, 5))  # declared before any run: 36 start offsets of the add against the delete


def _c3_checks(state_a: dict, state_b: dict, delete_ok: bool, add_ok: bool, cognify_b: str | None) -> list[Check]:
    rows_b = _rows(state_b).get("C3X", [])
    missing = [r for r in rows_b if r["raw_exists"] is False or r["original_exists"] is False]
    checks = [
        Check("I2", not missing, len(missing), "B rows pointing at deleted files",
              "B's acknowledged row points at files that no longer exist (cause = delete)" if missing
              else (f"B's row and its files exist" if rows_b else "B has no row"), ["C3X"] if missing else []),
        Check("I2", cognify_b in (None, "ok"), 0 if cognify_b in (None, "ok") else 1, "failed cognify(B)",
              f"cognify(B): {cognify_b}"),
    ]
    if add_ok and not rows_b:
        checks.append(Check("I2", False, 1, "acknowledged adds without a row", "add(B) returned but B has no row"))
    if delete_ok:
        left = len(_rows(state_a).get("C3X", [])) + _tag_counts(state_a, "DocumentChunk").get("C3X", 0)
        checks.append(Check("I5", not left, left, "A artefacts left", "A's copy is gone" if not left
                            else "A still holds the deleted document"))
    return checks


class C3CrossProcess(RaceScenario):
    """Two processes, no pause: one deletes A's copy while the other adds the same bytes to B, then cognifies B."""

    id = "c3.cross_process"
    invariants = ("I2", "I5")
    support = "boundary"
    basis = "issue"
    basis_ref = ISSUE_6559
    spread_gate = False  # the offsets stagger the two clients on purpose
    A, B = "wm_c3_a", "wm_c3_b"

    def params(self):
        return {"declared_sweep": [{"offset_ms": d} for d in OFFSETS_MS],
                "offset": "positive: the add starts later; negative: the delete starts later; trial k uses "
                          "offset k-1 of the sweep",
                "credit": "#6559's reporter found the window and swept offsets without a pause"}

    def groups(self):
        return [self.A, self.B]

    async def setup(self, target, group):
        if group == self.A:
            await target.ingest({"entry": "add", "tags": ["C3X"]}, self.A)

    def clients(self):
        return [(self.A, {"entry": "delete", "tags": ["C3X"], "offsets": [max(0, -d) for d in OFFSETS_MS]}),
                (self.B, {"entry": "add_try_cognify", "tags": ["C3X"], "offsets": [max(0, d) for d in OFFSETS_MS],
                          **ONE_ITEM})]

    def check(self, ops, states):
        delete = next((op for op in ops if op.input["entry"] == "delete"), None)
        add = next((op for op in ops if op.input["entry"] == "add_try_cognify"), None)
        add_ok = add is not None and add.outcome == OK
        cognify = (add.result or {}).get("cognify") if add_ok else None
        return _c3_checks(states[self.A], states[self.B], delete is not None and delete.outcome == OK, add_ok,
                          cognify) + [error_check(ops)]

    def sequential_expected(self, ops, states):
        checks = self.check(ops, states)
        bad = [c.detail for c in checks if not c.held] + _errors(ops)
        return (not bad, "delete(A) then add(B) and cognify(B): B's row and files exist, cognify(B) succeeds, "
                         "A's copy is gone", "; ".join(bad) or "as expected")


class C3InProcess(CaseSuite):
    """One process: #6559's pause between B's stored file and its row commit, and the same without a pause."""

    id = "c3.in_process"
    invariants = ("I2", "I5")
    support = "supported"
    basis = "issue"
    basis_ref = f"{ISSUE_6559} (support: {SEVERAL_DATASETS})"
    A, B = "wm_c3_a", "wm_c3_b"

    def cases(self):
        setup = ({"entry": "add", "tags": ["C3X"]},)
        group = f"{self.A}+{self.B}"
        return [Case("paused", group, setup, {"entry": "c3_paused", "tags": ["C3X"], "dataset_a": self.A,
                                              "dataset_b": self.B, **ONE_ITEM}),
                Case("gather", group, setup, {"entry": "c3_gather", "tags": ["C3X"], "dataset_a": self.A,
                                              "dataset_b": self.B, **ONE_ITEM})]

    def check(self, case, ops, state):
        op = ops[-1]
        result = op.result or {}
        delete = result.get("delete")
        delete_ok = isinstance(delete, dict) and delete.get("deleted", 0) > 0
        datasets = state.get("datasets", {})
        return _c3_checks(datasets.get(self.A, {}), datasets.get(self.B, {}), delete_ok, op.outcome == OK,
                          result.get("cognify_b"))


# --- C5: read your writes --------------------------------------------------------------------------------------


class C5Visibility(VisibilityScenario):
    id = "c5.visibility"

    def __init__(self):
        self.corpus = build("c5")

    def group(self):
        return "wm_c5"

    def items(self):
        return [({"entry": "add_cognify", "tags": [d.tag], **ONE_ITEM}, d.sentence, d.tag)
                for d in self.corpus.docs]


# --- C6: deletion permanence -----------------------------------------------------------------------------------


class C6Deletion(CaseSuite):
    """Delete one document; everything derived only from it goes, shared entities stay."""

    id = "c6.deletion"
    invariants = ("I5", "I2")
    support = "none"
    basis = "documented"
    basis_ref = DELETE_RECEIPT
    D, E = "wm_c6", "wm_c6e"

    def __init__(self):
        self.corpus = build("c6")

    def cases(self):
        setup = ({"entry": "add_cognify", "tags": ["C6D1", "C6D2", "C6D3"], **ONE_ITEM},)
        return [
            Case("delete", self.D, setup, {"entry": "delete", "tags": ["C6D1"]}),
            Case("delete_during_cognify", f"{self.D}+{self.E}", setup,
                 {"entry": "delete_during_cognify", "tags": ["C6D1"], "other_group": self.E,
                  "other_tags": ["C6E1", "C6E2"], **ONE_ITEM}),
        ]

    def check(self, case, ops, state):
        d = state.get("datasets", {}).get(self.D, state)
        checks = []
        gone_tag = [kind for kind in ("DocumentChunk", "TextDocument", "TextSummary") if "C6D1" in _tag_counts(d, kind)]
        entities = _nodes(d, "Entity")
        relations = _relations(d)
        alice = [k for k in ("alice moreau",) if k in entities]
        alice_edges = [r for r in relations if r.startswith("alice moreau|")]
        row_left = "C6D1" in _rows(d)
        checks.append(Check("I5", not (gone_tag or alice or alice_edges or row_left),
                            len(gone_tag) + len(alice) + len(alice_edges) + int(row_left), "artefacts left",
                            f"left after the delete: nodes {gone_tag}, entities {alice}, edges {alice_edges}, "
                            f"row {row_left}" if (gone_tag or alice or alice_edges or row_left)
                            else "nothing derived only from C6D1 remains"))
        orphans, without_node, without_vector = _dangling(d)
        checks.append(Check("I5", not (orphans or without_node), orphans + without_node, "dangling artefacts",
                            f"{orphans} orphan edges, {without_node} vectors without a graph node, "
                            f"{without_vector} graph nodes without a vector"))
        kept = ["C6D2", "C6D3"]
        checks.append(check_present(sorted(self.corpus.entity_keys(kept)), set(entities), "shared and other entities"))
        checks.append(check_present(sorted(self.corpus.relation_keys(kept)), set(relations), "other documents' relations"))
        checks.append(check_present(kept, set(_tag_counts(d, "DocumentChunk")), "other documents' chunks"))
        if case.id == "delete_during_cognify":
            e = state.get("datasets", {}).get(self.E, {})
            checks += [c for c in store_checks(self.corpus, ["C6E1", "C6E2"], e, self.E) if c.invariant == "I2"]
        return checks


# --- C0: one cognify call, one process --------------------------------------------------------------------------


class C0SingleCall(CaseSuite):
    """One add and one cognify over eight documents that share entities: nothing concurrent on the caller's side.

    Cognee runs the call's data items concurrently (data_per_batch, default 20). The case with
    data_per_batch=1 is the control: the same documents, one item at a time.
    """

    id = "c0.single_call"
    invariants = ("I1B", "I2", "I4")
    support = "supported"
    basis = "documented"
    basis_ref = f"{UPSERT} (create_data_points upserts, and dedups ids within a batch)"
    GROUP = "wm_c0"

    def __init__(self):
        self.corpus = build("c1")
        self.tags = [d.tag for d in self.corpus.docs[:8]]

    def cases(self):
        one = Case("data_per_batch_1", self.GROUP, (), {"entry": "add_cognify", "tags": self.tags, "data_per_batch": 1})
        default = Case("default_20", self.GROUP, (), {"entry": "add_cognify", "tags": self.tags})
        return [one, default]

    def check(self, case, ops, state):
        return store_checks(self.corpus, self.tags if ops[-1].outcome == OK else [], state, self.GROUP)
