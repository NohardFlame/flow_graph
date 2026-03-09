# System Architecture Overview

## Product goal

Build an MVP that converts a small set of business or system documents into normalized action-centric records with strong evidence links and low token spend.

## Main runtime path

1. Client uploads one or more documents.
2. API stores file metadata in PostgreSQL and raw bytes in object storage.
3. API enqueues a document processing job.
4. Worker downloads the source file and parses it into a structured `ParsedDocument`.
5. Chunk assembler builds extraction windows from document structure.
6. Deterministic prefilter scores each chunk.
7. Only high-confidence and selected gray-zone chunks are sent to the LLM extractor.
8. LLM returns action-centric JSON.
9. Validator parses the JSON into domain models.
10. Normalizer computes canonical keys.
11. Results are persisted in PostgreSQL.
12. Optional indexing pushes selected chunks/actions into Qdrant.
13. API exposes run status and results.

## Bounded contexts

### API context
Owns request validation, upload coordination, read endpoints, and human-facing status.

### Ingestion context
Owns object storage writes, document metadata, and retrieval of source artifacts.

### Parsing context
Owns document conversion, structure preservation, chunk assembly, and chunk metadata.

### Prefilter context
Owns deterministic relevance scoring and chunk selection policy.

### Extraction context
Owns prompt construction, LLM invocation, retries, repair handling, and output validation.

### Normalization context
Owns canonical key derivation, alias collapse, and collision policy.

### Persistence context
Owns repositories, transactions, idempotency, and run bookkeeping.

### Worker orchestration context
Owns queue jobs, step transitions, retry policy, and resumability.

## Domain objects

### Document
A source file and its metadata.

### ProcessingRun
A single attempt or pipeline execution over one document version.

### ParsedDocument
Structured parse result derived from the source file.

### ExtractionChunk
A chunk assembled for extraction, with heading path, source spans, and prefilter score.

### ActionRecord
The main extracted entity. Contains:
- action label and canonical key,
- actors,
- objects,
- input/output states,
- conditions,
- permissions,
- restrictions,
- evidence references.

### EvidenceRef
A grounded pointer to exact source text and location metadata.

## Architectural rules

1. Domain models do not import infrastructure adapters.
2. Repositories expose domain-oriented methods, not raw SQL in service code.
3. External calls go through adapters:
   - object storage adapter,
   - doc parser adapter,
   - llm adapter,
   - vector index adapter.
4. Job handlers are thin orchestration layers.
5. Deterministic normalization must be reproducible from stored raw data.
6. Every persisted record must be attributable to a `run_id` and `document_id`.
7. Any expensive step must be restart-safe.

## MVP non-goals

- full graph database,
- cross-document ontology learning,
- agentic multi-step critique loops,
- fully automatic semantic dedup across all documents,
- complex user management.
