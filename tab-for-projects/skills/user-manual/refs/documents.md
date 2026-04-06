# Document Reference

## Document Types

Each type serves a distinct purpose. Pick the type that matches what you're capturing.

| Type | When to use | Typical tags |
|------|-------------|-------------|
| **ADR** | A single decision with rationale, alternatives, and consequences | `decision`, `architecture` |
| **Design doc** | A significant change needing evaluation — context, goals, design, tradeoffs | `architecture`, `decision` |
| **Architecture overview** | System structure, components, boundaries, how they connect | `architecture`, `reference` |
| **Requirements doc** | What a feature or system must do — functional and non-functional constraints | `reference`, + domain tag |
| **Feature doc** | Why a feature exists, how it works, how to use it | `guide`, + domain tag |
| **Pattern record** | An established codebase pattern with file references and rationale | `conventions`, + domain tag |
| **Convention doc** | Naming, structure, integration, or style conventions | `conventions`, + domain tag |
| **Reference doc** | API contracts, config shapes, lookup tables, enum definitions | `reference`, + domain tag |
| **Troubleshooting guide** | Symptoms, causes, fixes for known problems | `troubleshooting`, + domain tag |

**ADRs vs. design docs:** An ADR captures one decision. A design doc evaluates a broader change that may involve multiple decisions. If the scope is "we chose X over Y," write an ADR. If the scope is "here's how we're restructuring the auth system," write a design doc.

---

## Create-vs-Update Discipline

The KB should grow in depth, not breadth. Before writing, search for what already exists.

### Before Every Write

1. Call `list_documents({ search: "[topic]" })` to find existing documents on the same topic.
2. Scan titles and summaries. If a document covers this topic, call `get_document` to read it.
3. Decide: update or create.

### When to Update

- A document already covers this topic — add sections, correct stale information, refresh content.
- New information extends or refines what's already documented.
- The existing document is partially wrong — fix the inaccuracies rather than creating a parallel version.

### When to Create

- The topic is genuinely new — no existing document covers it.
- The scope is fundamentally different from any existing document, even if the domain overlaps.

### When Superseding

- Create the new document first.
- Add a note at the top of the new document: "Supersedes: [old doc title] ([old doc ID])."
- Update the old document's summary to note it has been superseded and by what.
- Both documents persist — the old one provides historical context.

### The Bias

**Default to updating.** Creating is the exception. Ten well-maintained documents beat fifty stale ones.

---

## Tagging Conventions

Tags use a **closed enum**. Only these values are valid:

| Category | Tags |
|----------|------|
| **Domain** | `ui`, `data`, `integration`, `infra`, `domain` |
| **Content type** | `architecture`, `conventions`, `guide`, `reference`, `decision`, `troubleshooting` |
| **Concern** | `security`, `performance`, `testing`, `accessibility` |

### Rules

- **1-3 tags per document.** Pick the most relevant, not all that could apply.
- **Always include one content-type tag.** This is the primary classifier — it tells readers what kind of document this is.
- **Add a domain tag when the document is domain-specific.** An architecture doc about the data layer gets `architecture` + `data`. A general conventions doc gets `conventions` alone.
- **Add a concern tag only when the concern is the focus.** A security ADR gets `decision` + `security`. A feature doc that mentions security in passing does not get `security`.

### Common Combinations

| Document | Tags |
|----------|------|
| ADR about API auth approach | `decision`, `security` |
| Architecture overview of data pipeline | `architecture`, `data` |
| Naming conventions for UI components | `conventions`, `ui` |
| Troubleshooting MCP connection issues | `troubleshooting`, `integration` |
| General coding conventions | `conventions` |
| Performance tuning guide | `guide`, `performance` |

---

## Document Ownership

The **tech lead is the single owner of all KB document output.** No other agent calls `create_document` or `update_document`. This centralized ownership ensures consistency, prevents duplication, and enables KB health management.

### Tech Lead — Single Document Owner

The tech lead writes all document types:

| Source | Document types | Examples |
|--------|---------------|----------|
| **From code investigation** | Pattern records, convention docs, drift corrections, codebase references | "Pattern: MCP tool handler structure", "Conventions: File naming in skills/" |
| **From analysis and decisions** | Design docs, ADRs, architecture overviews, feature docs | "Design: Auth system restructure", "ADR: Event-driven sync over polling" |

The tech lead's bias is toward **updating** over creating. Its primary job is keeping existing documentation accurate and the KB lean (soft cap: 10 documents per project).

### Tech Lead — Owns All Document Types

The tech lead both analyzes systems for design decisions and investigates code for codebase truth. It writes all document types directly:

| Situation | Tech lead does |
|-----------|----------------|
| New design decision needed | Researches, evaluates alternatives, writes the ADR or design doc |
| Architecture overview needed | Analyzes system structure, creates the architecture overview document |
| Codebase drifted from design | Detects drift, updates the document to match reality |
| New convention emerged | Discovers the convention in code, creates convention doc |
| Existing doc is stale | Updates or supersedes the document |

---

## Passing References

Documents are the interface between advisory agents. The protocol for sharing:

### Write First, Share Second

1. Write or update the document using `create_document` or `update_document`.
2. Attach it to the project using `update_project({ items: [{ id: "[project-id]", attach_documents: ["[doc-id]"] }] })`.
3. Share the document ID with teammates.

### Reference Format

When passing a reference to another agent, include three things:

- **Document ID** — the lookup key.
- **2-3 sentence summary** — what the document contains and why it matters.
- **Implication for the recipient** — what it means for their work.

Example:

> Architecture decision documented in `01ABC123`. Key points: chose event-driven sync over polling for lower latency and simpler error handling. Planner — this affects task decomposition because the sync service needs an event bus dependency. Tech lead — verify the current codebase doesn't already have a polling implementation that needs migration.

### What NOT to Do

- **Never paste document content into messages.** IDs are the interface. The recipient fetches what they need.
- **Never reference a document without its ID.** Titles change; IDs don't.
- **Never share a document ID without context.** A bare ID forces the recipient to fetch and read before knowing if it's relevant.
