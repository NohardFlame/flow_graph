# Action-Centric Extraction: Intent and Target Shape

## Why the project is built around actions

The system is not trying to extract "all entities mentioned in the document" as an end in itself.
The primary goal is to extract **action-centric business facts** that can later be turned into a process model.

In this design, an action is the main unit of meaning.
Actors, objects, and states are important **only insofar as they participate in a meaningful business action**.

This is intentional:
- a role with no actions is not useful for the future diagram;
- an object with no lifecycle or operations is not useful for the future diagram;
- a state matters mainly when some action leads into it, requires it, or forbids action in it.

So the extraction target is not a generic knowledge graph.
It is a **future process/logic graph** built around actions.

---

## What we want to build later

The long-term goal is to construct a flow/process diagram from extracted action records.

Conceptually, each extracted action can later become one or more edges in a graph such as:

- **actor -> action -> object**
- **object state A -> action -> object state B**
- **role -> may / may not perform -> action**
- **system -> automatically performs -> action on object**

That means the extraction output should already contain enough local semantics to support:
- who acts;
- on what object;
- from which state;
- to which state;
- whether it is allowed, forbidden, automatic, or conditional.

We do **not** want shallow summaries like "request processing" or "user management".
Those are too broad to become graph edges.

---

## What counts as a good extracted result

A good result is an **atomic business action**.
It should be small enough to be represented as a concrete operation in a future diagram.

Good examples:
- "user submits request"
- "manager approves request"
- "system changes request status to approved"
- "operator cannot edit closed order"
- "system sends notification after approval"

Bad examples:
- "request handling"
- "working with orders"
- "approval process"
- "status management"

Good output should be:
- specific;
- grounded in the chunk text;
- useful for downstream normalization;
- useful for future graph construction.

---

## How to think about action records

Each action record should describe one independent, graph-worthy business fact.

In practice, a good record usually answers most of these questions:
- Who performs the action?
- What is the action?
- What object is affected?
- Is there an input state?
- Is there an output state?
- Is this allowed, forbidden, automatic, or conditional?

If the text does not provide some field clearly, it is better to leave it empty/null than invent it.

---

## Why normalization matters

Later stages will merge results across chunks and documents.
So extraction should preserve:
- the original wording from the source text;
- a conservative suggested canonical form for downstream merging.

Example:
- source wording: "Менеджер подтверждает заявку"
- extracted action label: "manager approves request"
- canonical suggestions: `manager`, `request`, `approve`

The extraction stage should help normalization, but not aggressively over-merge distinct concepts.
Conservative normalization is better than clever but wrong normalization.

---

## How the agent should evaluate output quality

When reviewing extraction results, the agent should ask:

1. Is this a concrete action or just a topic name?
2. Can this result later become a node/edge in a process diagram?
3. Does it clearly connect actor, object, and/or states?
4. Is it faithful to the source chunk?
5. Is it normalized enough for downstream merging, but not over-normalized?

If the answer to the first two questions is "no", the extraction is probably too vague.

---

## Practical rule of thumb

The extraction should produce records that are already close to future diagram edges.

In other words:
- **Do not extract for documentation only.**
- **Extract for future process graph construction.**

That is the core design intent of this system.
