# Axon Roadmap: from v1.0.0b2 to a solid v1.0.0

**Positioning:** Axon is the *governed memory layer* for LLM applications: tiered storage,
policy-driven lifecycle, cost control, and compliance building blocks (audit, PII, `forget`)
on top of any vector backend.

**Principle:** every claim in the README must link to a test or a benchmark.

Estimates assume roughly 10-15 hours per week. Do not start a phase until the previous
phase's exit criteria are met (Phases 4 and 5 may overlap).

| Phase | Focus | Effort | Status |
|---|---|---|---|
| 0 | Audit and baseline | 3-5 days | In progress |
| 1 | Correctness and stability | 2-3 weeks | In progress |
| 2 | Packaging and hygiene | 1 week | Planned |
| 3 | CI/CD and release engineering | 3-5 days | Planned |
| 4 | Adoption features | 3-4 weeks | Planned |
| 5 | Proof (benchmarks, compliance, security) | 2-3 weeks | Planned |
| 6 | Documentation and launch | 1-2 weeks | Planned |
| 7 | Post-launch | Continuous | Planned |

---

## Phase 0: Audit and baseline (3-5 days)

**Goal:** find out what is true before changing anything.

- [ ] Install in a clean venv; run `pytest`, `ruff check`, `black --check`, `mypy`; record results
- [ ] Verify each blocker from the previous roadmap against current code (some may be fixed)
- [ ] Test the README quick start on a clean machine and every install extra
- [ ] Check docs and examples still run
- [ ] Check dependency drift (Chroma, Qdrant, Pinecone, OpenAI, LangChain, LlamaIndex)
- [ ] Run secret scan and `pip-audit`
- [ ] File findings as GitHub issues (`blocker`, `bug`, `docs`, `enhancement`) under a 1.0 milestone

**Exit criteria:** a written list of real blockers and a GitHub milestone.

---

## Phase 1: Correctness and stability (2-3 weeks)

**Also fixed so far:** audit auto-export deadlock and overwrite; `store()` crash with audit logging + string `privacy_level`.
**Found, still open:** capacity enforcement scans the tier on each store while it is over capacity (needs a cheaper approach at scale); `MemorySystem.recall` needs an embedder on vector-store tiers (text queries only work on in-memory/Redis); `test_audit_flow` performance test is timing-flaky; `export()` fallback calls sync `list_ids()` (not on Redis/Pinecone); several adapter/embedder tests need optional deps (`python-dotenv` is undeclared); compaction integration tests need `dotenv`/OpenAI.

**Goal:** the core behaves as documented.

- [ ] **Known bugs**
  - [x] Tier capacity tracking so overflow fires (`policy_engine.py`); *overflow demotes/purges but never hard-evicts live entries; `eviction_strategy` is not implemented*
  - [x] Replace silent `except: pass` blocks with logged, propagated errors (`memory_system.py`, Qdrant/Pinecone counts)
  - [x] `forget()` works by ID and by filter across every tier (was broken and missing on `MemorySystem`; now tested end to end)
- [ ] **End-to-end behavior tests** for:
  - [x] promotion/demotion (found and fixed: promotion duplicated entries, demotion never ran,
        access counts were lost on non-memory backends)
  - [x] TTL expiry (found and fixed: `ttl_seconds` was never enforced)
  - [x] capacity enforcement on store
  - [ ] compaction with provenance
  - [ ] transaction rollback on partial failure
  - [ ] audit events on success and failure
  - [ ] PII detection (including odd input)
- [ ] **Concurrency:** Router is single-event-loop only; document it and add a clear guard
      rather than silent corruption
- [x] **Adapter contract tests:** one shared suite (`tests/contract/`, ~190 cases) run against memory,
      Chroma, Qdrant and Redis (real server); Pinecone runs when `PINECONE_API_KEY` is set.
      *Follow-up: run Redis/Qdrant as CI service containers (Phase 3).*
- [x] **Error model:** `axon.errors` hierarchy rooted at `AxonError`; each class also subclasses the
      builtin it replaces so existing `except` clauses keep working
- [ ] **Data safety:** add `schema_version` to stored entries and define a migration path

**Exit criteria:** contract suite passes on all adapters, no known data-loss bugs,
coverage on `core/` at or above 85-90%.

---

## Phase 2: Packaging and hygiene (1 week)

**Goal:** installing and importing Axon is trustworthy.

- [ ] One package name everywhere (`axon-sdk` vs `axon-memory`); confirm PyPI ownership
- [ ] Single source of truth for the version
- [ ] Make `openai` optional; core deps are pydantic, numpy, typing-extensions only;
      missing extras raise a helpful `ImportError` naming the extra to install
- [ ] Consistent `requires-python` across `pyproject.toml`, README, CI, classifiers
- [ ] Keep `import axon` fast (lazy imports) and enforce it with a test
- [ ] mypy in CI; keep shipping `py.typed`
- [ ] Repo cleanup; add `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue/PR templates, `CODEOWNERS`

**Exit criteria:** `pip install` works in a fresh venv and `import axon` works with no
optional dependencies installed.

---

## Phase 3: CI/CD and release engineering (3-5 days)

**Goal:** every change is checked and releases are repeatable.

- [ ] GitHub Actions matrix: Python 3.10-3.13 on Linux; smaller matrix on macOS/Windows
- [ ] Jobs: lint, format, mypy, unit tests, integration tests with service containers
      (Redis, Qdrant, Chroma); Pinecone optional/nightly
- [ ] Coverage reporting with a floor
- [ ] Release workflow: tag, build, publish to PyPI via trusted publishing, GitHub Release
- [ ] Dependabot or Renovate; pre-commit hooks (black, ruff)
- [ ] CHANGELOG in Keep-a-Changelog format; SemVer; document what is public API
- [ ] Publish `1.0.0rc1` to TestPyPI first

**Exit criteria:** green CI badge and an rc installable from TestPyPI.

---

## Phase 4: Adoption features (3-4 weeks)

**Goal:** make Axon easy to try and easy to plug in.

- [ ] **SQLite adapter** (zero-infrastructure default for local use and demos)
- [ ] **MCP server** exposing `store`, `recall`, `forget`, `export`, `compact`
- [ ] Refresh LangChain and LlamaIndex integrations with version-pinned tests
- [ ] **CLI** for tier stats, audit export, `forget --user`
- [ ] Optional OpenTelemetry hooks
- [ ] File-based configuration (YAML/TOML) alongside the Python API

**Exit criteria:** `pip install` to a working recall in under five minutes, with no
external services and no API key.

---

## Phase 5: Proof (2-3 weeks, may overlap Phase 4)

**Goal:** replace claims with evidence.

- [ ] Reproducible `benchmarks/` harness (one command)
- [ ] Cost and latency: same workload with tiers off vs on (backend calls, p50/p95, tokens);
      publish a "% saved" figure only if the data supports it
- [ ] Retrieval quality on LoCoMo or LongMemEval, reported honestly against baselines
- [ ] Compliance evidence: `forget(user)` removes data from all tiers and is audited;
      document guarantees and non-guarantees (Axon provides building blocks; it does not
      certify GDPR/HIPAA compliance)
- [ ] Load and soak tests for capacity limits and memory growth
- [ ] Security review: filter injection, secrets/PII in logs, `bandit`

**Exit criteria:** published results with methodology; every README claim links to evidence.

---

## Phase 6: Documentation and launch (1-2 weeks)

**Goal:** people find Axon and understand it quickly.

- [ ] README rewrite: one-sentence pitch, 20-line quick start, fair comparison with
      Mem0/Zep/Letta
- [ ] Docs site: getting started, concepts, adapter guide, compliance guide, MCP guide,
      migration notes, generated API reference, troubleshooting
- [ ] Trim examples to about 10, all tested in CI
- [ ] One flagship demo (e.g. compliance-aware support agent)
- [ ] Publish `1.0.0`; announce (Show HN, r/LocalLLaMA, r/MachineLearning, LangChain and
      MCP communities) with the benchmark as the hook
- [ ] GitHub Discussions, `good first issue` labels, working contributor guide

**Exit criteria:** 1.0.0 on PyPI, docs live, launch posts out.

---

## Phase 7: Post-launch (continuous)

- Triage issues weekly; patch releases for bugs; a minor release every 4-8 weeks
- Let usage drive the roadmap. Candidates: temporal validity (`valid_from`/`valid_to`),
  LLM-based compaction and dedup, agent-scoped memory
- Track downloads, stars, issues from strangers, contributor PRs; if nothing moves after
  2-3 months of visible effort, revisit the positioning
