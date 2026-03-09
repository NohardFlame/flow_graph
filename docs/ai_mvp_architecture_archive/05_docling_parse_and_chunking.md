# Module: Docling Parse and Chunking

## Goal

Convert source documents into a structured internal representation and build extraction-oriented chunks that preserve business semantics.

## Recommended technologies

- Docling `DocumentConverter`
- Docling document export facilities
- custom chunk assembly layer on top of Docling structure
- optional use of `HybridChunker` only as a helper, not the final chunk policy

## Core architectural position

Do **not** treat Docling's default chunks as your production extraction chunks.

Use Docling for:
- format conversion,
- document structure,
- tables,
- headings,
- provenance metadata.

Then build your own extraction windows.

## Internal representations

Define:

### `ParsedDocument`
Fields:
- `document_id`
- `run_id`
- `source_format`
- `title`
- `sections`
- `tables`
- `lists`
- `raw_docling_export_ref`

### `SectionUnit`
Fields:
- `section_path`
- `block_type` (`paragraph`, `list`, `table`, `note`, `heading`)
- `text`
- `source_spans`
- `page_refs`

### `ExtractionChunk`
Fields:
- `chunk_id`
- `section_path`
- `chunk_text`
- `source_spans`
- `page_refs`
- `estimated_tokens`
- `structural_features`

## Chunk assembly algorithm

### Step 1: structural extraction
From Docling output, materialize ordered `SectionUnit` objects.

### Step 2: semantic grouping
Keep together:
- heading + following explanatory paragraphs,
- table + caption + nearby interpretation text,
- list of statuses + definitions,
- role/permission sections,
- "if/then" rule groups.

### Step 3: token cap enforcement
Apply soft upper bound:
- split first by subheading,
- then by block group,
- only last by approximate token count.

### Step 4: controlled overlap
Overlap by semantic context, not raw fixed windows:
- section path,
- previous subheading,
- short carry-over context snippet if needed.

## Chunk size target

For MVP extraction windows:
- preferred: 1.5k to 4k tokens
- smaller only when structure is naturally small
- avoid microscopic fragments that lose actor/object/state context

## Serialization rules for LLM input

Chunk text must be serialized consistently:
- include document title if available,
- include section path,
- preserve list formatting,
- serialize tables into stable readable text,
- avoid noisy page furniture.

## Parse failure handling

If a file cannot be parsed:
- mark parse step failed,
- store error metadata,
- do not attempt downstream extraction.

If a file partially parses:
- persist partial parse artifact,
- allow run to continue only if enough text exists to build chunks.

## Debug artifacts to persist

Store:
- structured parse export,
- chunk list export with chunk ids and source spans.

This is critical for debugging extraction misses.

## Acceptance criteria

- same source document yields stable chunk boundaries under same config,
- chunks preserve section context,
- tables and lists are not blindly shredded,
- chunk ids are deterministic for a given parse result and chunking config,
- parse/chunk outputs can be inspected without rerunning Docling.

## Common pitfalls

- coupling later logic directly to raw Docling internals everywhere,
- losing provenance when flattening text,
- using character-count chunking alone,
- ignoring tables and lists,
- embedding page furniture into extraction prompts.
