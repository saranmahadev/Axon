# AGENTS.md - Sprint-Based Development Process

**Purpose:** This document defines the systematic, agent-driven process for building the Memory SDK through structured sprints with planning, implementation, verification, and confirmation cycles.

---

## Process Overview

```
Phase → Sprint Planning → Confirmation → Implementation → Verification → Testing → Next Sprint
```

Each phase is broken into **sprints** (1-3 days of work). Each sprint follows a strict workflow:

1. **Sprint Planning** - Define scope, tasks, deliverables, and success criteria
2. **Confirmation** - Present plan to stakeholder and get approval
3. **Implementation** - Execute the planned tasks
4. **Verification** - Review code quality, completeness, and adherence to spec
5. **Testing** - Run automated tests and manual validation
6. **Sprint Review** - Document outcomes and prepare for next sprint

---

## Agent Roles

### 1. Planning Agent
**Responsibility:** Break down phases into actionable sprints

**Tasks:**
- Analyze phase requirements from the main todo list
- Create sprint backlogs with specific deliverables
- Define success criteria and acceptance tests
- Estimate complexity and dependencies
- Identify risks and blockers
- Create sprint plan document

**Output:** Sprint plan with tasks, deliverables, acceptance criteria, and file structure

---

### 2. Implementation Agent
**Responsibility:** Execute the sprint plan and write code

**Tasks:**
- Create directory structure and files
- Implement features according to specification
- Follow coding standards and best practices
- Add inline documentation and type hints
- Handle edge cases and error conditions
- Commit code with meaningful messages

**Output:** Working code files with proper structure and documentation

---

### 3. Verification Agent
**Responsibility:** Review and validate implementation quality

**Tasks:**
- Check code against sprint plan requirements
- Verify adherence to technical specification
- Review error handling and edge cases
- Validate type safety and contracts
- Check documentation completeness
- Identify gaps or issues

**Output:** Verification report with pass/fail status and issues list

---

### 4. Testing Agent
**Responsibility:** Validate functionality through automated and manual tests

**Tasks:**
- Write unit tests for new components
- Write integration tests where applicable
- Run all tests and report results
- Perform manual validation of key scenarios
- Check code coverage
- Document test cases

**Output:** Test suite and test report with coverage metrics

---

### 5. Review Agent
**Responsibility:** Synthesize sprint outcomes and prepare next steps

**Tasks:**
- Summarize what was completed
- Update the Sprint Document Properly
- Document any deviations from plan
- Identify technical debt or follow-ups
- Update project status
- Recommend next sprint scope
- Archive sprint artifacts

**Output:** Sprint retrospective and recommendations

---

## Sprint Workflow Template

### Phase: [Phase Name]
### Sprint: [Sprint Number] - [Sprint Name]

---

#### STEP 1: SPRINT PLANNING

**Planning Agent Output:**

```markdown
## Sprint Goal
[Clear, concise goal statement]

## Scope
- [ ] Task 1: [Description]
- [ ] Task 2: [Description]
- [ ] Task 3: [Description]

## Deliverables
1. [File/Component name] - [Purpose]
2. [File/Component name] - [Purpose]

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## File Structure
```
path/to/file.py
path/to/test_file.py
```

## Dependencies
- Depends on: [Previous sprint/component]
- Required packages: [List]

## Estimated Complexity: [Low/Medium/High]

## Risks
- [Risk 1]: [Mitigation]
- [Risk 2]: [Mitigation]
```

**🔄 CONFIRMATION CHECKPOINT:**
> Present sprint plan to user and await approval before proceeding

---

#### STEP 2: IMPLEMENTATION

**Implementation Agent Output:**

```markdown
## Implementation Log

### Files Created:
- [x] `path/to/file1.py` - [Purpose]
- [x] `path/to/file2.py` - [Purpose]

### Key Components:
- **Component1**: [Description of what was built]
- **Component2**: [Description of what was built]

### Design Decisions:
- [Decision 1]: [Rationale]
- [Decision 2]: [Rationale]

### Dependencies Added:
- package1==version
- package2==version

### Notes:
- [Any important implementation notes]
```

---

#### STEP 3: VERIFICATION

**Verification Agent Output:**

```markdown
## Verification Report

### Requirements Check:
- [x] Task 1 completed as specified
- [x] Task 2 completed as specified
- [ ] Task 3 has minor deviation: [Explanation]

### Code Quality:
- [x] Type hints present
- [x] Docstrings complete
- [x] Error handling implemented
- [x] Edge cases covered

### Specification Adherence:
- [x] Matches technical spec for [Component]
- [x] API contracts honored
- [x] Data models match schema

### Issues Found:
1. [Issue description] - [Severity: Low/Medium/High]
2. [Issue description] - [Severity: Low/Medium/High]

### Status: ✅ PASS / ⚠️ PASS WITH ISSUES / ❌ FAIL

### Recommendations:
- [Recommendation 1]
- [Recommendation 2]
```

---

#### STEP 4: TESTING

**Testing Agent Output:**

```markdown
## Test Report

### Test Coverage:
- Unit tests: [X]% coverage
- Integration tests: [X] scenarios

### Test Results:
```
test_component1.py::test_basic_functionality PASSED
test_component1.py::test_edge_case PASSED
test_component1.py::test_error_handling PASSED
test_component2.py::test_integration PASSED

Total: X passed, Y failed, Z skipped
```

### Manual Validation:
- [x] Scenario 1: [Result]
- [x] Scenario 2: [Result]
- [x] Scenario 3: [Result]

### Performance:
- [Metric 1]: [Result]
- [Metric 2]: [Result]

### Issues:
- [Issue if any]

### Status: ✅ ALL TESTS PASS / ❌ TESTS FAILING
```

---

#### STEP 5: SPRINT REVIEW

**Review Agent Output:**

```markdown
## Sprint Retrospective

### Completed:
- ✅ [Deliverable 1]
- ✅ [Deliverable 2]
- ⚠️ [Deliverable 3 - partial]

### Sprint Goal: ✅ ACHIEVED / ⚠️ PARTIALLY ACHIEVED / ❌ NOT ACHIEVED

### Technical Debt:
- [Item 1]: [Explanation and when to address]

### Lessons Learned:
- [Lesson 1]
- [Lesson 2]

### Blockers Resolved:
- [Blocker 1]: [How resolved]

### Next Sprint Preparation:
- Recommended scope: [Description]
- Required before next sprint: [Prerequisites]

### Artifacts:
- Code: [Commit/PR reference]
- Tests: [Test file locations]
- Documentation: [Doc updates]
```

**🔄 CONFIRMATION CHECKPOINT:**
> Present sprint review to user and get approval to proceed to next sprint

---

## Phase Breakdown with Sprints

### **PHASE 1: Foundation (MVP 0.1 - Core Infrastructure)**

#### Sprint 1.1: Project Scaffolding & Data Models
- Setup: pyproject.toml, directory structure, dev environment
- Core models: MemoryEntry, Filter, base types
- Duration: 1 day
- Deliverables: Project structure + core Pydantic models

#### Sprint 1.2: Storage Adapter Interface & InMemory
- StorageAdapter ABC
- InMemoryAdapter implementation
- Basic tests
- Duration: 1 day
- Deliverables: Adapter interface + working InMemory implementation

#### Sprint 1.3: Embedder Interface & OpenAI Integration
- Embedder ABC
- OpenAIEmbedder implementation
- Embedding cache foundation
- Duration: 1-2 days
- Deliverables: Working embedder with caching

---

### **PHASE 2: Core Storage & Routing (MVP 0.1 continued)**

#### Sprint 2.1: ChromaDB Vector Adapter
- ChromaAdapter implementation
- Vector indexing and search
- Metadata filtering
- Duration: 2 days
- Deliverables: Working ChromaAdapter with tests

#### Sprint 2.2: Redis Adapter & Cache Layer
- RedisAdapter implementation
- TTL support
- Cache key generation
- Duration: 2 days
- Deliverables: Working RedisAdapter with caching

#### Sprint 2.3: Policy DSL & Configuration
- Policy, EphemeralPolicy, SessionPolicy, PersistentPolicy
- Config validation
- Serialization
- Duration: 1-2 days
- Deliverables: Complete policy configuration system

#### Sprint 2.4: Router & Policy Engine
- Routing logic
- Tier selection
- Policy evaluation
- Duration: 2-3 days
- Deliverables: Working router with tier management

---

### **PHASE 3: Core API & Operations (MVP 0.1 completion)**

#### Sprint 3.1: MemorySystem Core API - Part 1
- store() method
- recall() method
- Basic validation and tracing
- Duration: 2 days
- Deliverables: Working store/recall operations

#### Sprint 3.2: MemorySystem Core API - Part 2
- forget() method
- export() method
- sync() method
- Duration: 1-2 days
- Deliverables: Complete CRUD operations

#### Sprint 3.3: Basic Summarization
- Simple LLM-based summarizer
- Count-based compaction
- compact() method
- Duration: 2 days
- Deliverables: Working summarization pipeline

---

### **PHASE 4: Advanced Features (v1.0)**

#### Sprint 4.1: Audit & Trace System
- Event logging
- trace() method
- TraceReport generation
- Provenance tracking
- Duration: 2 days

#### Sprint 4.2: Privacy & Encryption
- PII detection
- Redaction hooks
- Encryption adapters
- Duration: 2-3 days

#### Sprint 4.3: Observability & Metrics
- Prometheus metrics
- Structured logging
- observe() callbacks
- Duration: 1-2 days

#### Sprint 4.4: Advanced Compaction Strategies
- Semantic redundancy
- Importance-based
- Time-based triggers
- Duration: 2 days

---

### **PHASE 5: Production Adapters (v1.0 continued)**

#### Sprint 5.1: Qdrant Adapter
- QdrantAdapter implementation
- Connection pooling
- Error handling
- Duration: 2 days

#### Sprint 5.2: Pinecone Adapter
- PineconeAdapter implementation
- Retry logic
- Performance optimization
- Duration: 2 days

#### Sprint 5.3: SQL Adapter
- SQLAdapter for PostgreSQL/SQLite
- Schema management
- Query optimization
- Duration: 2-3 days

#### Sprint 5.4: S3 Archive Adapter
- S3Adapter implementation
- Reindexing support
- Batch operations
- Duration: 2 days

---

### **PHASE 6: Integration & Ecosystem (v1.0 completion)**

#### Sprint 6.1: Testing Infrastructure
- Comprehensive unit tests
- Integration test framework
- Mock data generators
- Duration: 2-3 days

#### Sprint 6.2: Demo Application
- FastAPI backend
- Simple web UI
- Example scenarios
- Duration: 2-3 days

#### Sprint 6.3: LangChain/LlamaIndex Integration
- Adapter plugins
- Integration examples
- Documentation
- Duration: 2 days

#### Sprint 6.4: CLI Tools
- Backup/export commands
- Reindex operations
- Configuration management
- Duration: 2 days

---

### **PHASE 7: Polish & Documentation (v1.0 final)**

#### Sprint 7.1: Documentation
- API docs
- User guide
- Example notebooks
- Duration: 2-3 days

#### Sprint 7.2: Performance Optimization
- Benchmarking suite
- Profiling
- Optimization
- Duration: 2-3 days

#### Sprint 7.3: Final QA & Release Prep
- End-to-end testing
- Bug fixes
- Release notes
- Duration: 2 days

---

## Agent Execution Rules

### 1. **Never Skip Confirmation**
- Planning Agent MUST wait for user approval before Implementation Agent proceeds
- Review Agent MUST wait for user approval before next sprint begins

### 2. **Sequential Execution**
- Agents execute in strict order: Plan → Confirm → Implement → Verify → Test → Review → Confirm
- No agent proceeds until previous agent completes

### 3. **Transparency**
- Each agent must clearly state what it's doing
- All decisions and deviations must be documented
- Issues must be raised immediately, not hidden

### 4. **Quality Gates**
- If Verification fails, return to Implementation
- If Testing fails, return to Implementation or Verification
- No sprint is "done" until all gates pass

### 5. **Artifact Management**
- All code committed to git
- All tests stored in tests/ directory
- All documentation updated in docs/
- Sprint logs archived in .sprints/ directory

---

## Sprint Tracking Template

Create `.sprints/sprint-[phase].[number].md` for each sprint:

```markdown
# Sprint [Phase].[Number]: [Name]

**Start Date:** YYYY-MM-DD
**End Date:** YYYY-MM-DD
**Status:** Planning / In Progress / In Review / Complete / Blocked

## Plan
[Planning Agent output]

## Implementation
[Implementation Agent output]

## Verification
[Verification Agent output]

## Testing
[Testing Agent output]

## Review
[Review Agent output]

## Approval
- [ ] Plan approved by: [User] on [Date]
- [ ] Sprint completed and approved by: [User] on [Date]
```

---

## Usage Instructions

### For AI Assistant (GitHub Copilot):

When user says "Start next sprint" or "Begin implementation":

1. **Activate Planning Agent**
   - Read current phase and sprint from todo list
   - Generate detailed sprint plan
   - Present plan clearly with file structure and success criteria
   - **WAIT for user confirmation with "APPROVED" or similar**

2. **Activate Implementation Agent** (only after approval)
   - Create all planned files
   - Implement features according to spec
   - Document decisions
   - **Report completion**

3. **Activate Verification Agent**
   - Check implementation against plan
   - Verify quality and completeness
   - **Report status (PASS/FAIL/ISSUES)**

4. **Activate Testing Agent**
   - Write and run tests
   - Report coverage and results
   - **Report status (PASS/FAIL)**

5. **Activate Review Agent**
   - Summarize sprint outcomes
   - Recommend next steps
   - **WAIT for user confirmation to proceed to next sprint**

### For User:

- Review each plan before approving
- Provide feedback on deviations
- Approve or reject sprint completions
- Request clarifications at any checkpoint

---

## Success Metrics

- **Sprint Completion Rate:** % of sprints completed on first attempt
- **Test Coverage:** Minimum 80% for core modules
- **Documentation Coverage:** 100% of public APIs documented
- **Defect Rate:** < 5 bugs per sprint discovered post-completion

---

## Version History

- **v1.0** (2025-11-04): Initial process definition
- Continuously updated as process evolves

---

**This document is the SINGLE SOURCE OF TRUTH for how we build the Memory SDK.**

Every sprint must follow this process. No exceptions.
