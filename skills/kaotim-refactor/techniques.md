# kaotim-refactor reference

Language-neutral names; apply with the repo's local idioms. Load when planning or writing characterization tests.

## Techniques
- **Extract** (function/method/module/variable) — name a coherent chunk.
- **Inline** — remove an indirection that adds nothing.
- **Rename** — clarify intent; update all references found by search.
- **Move** — relocate to the module that owns the concept.
- **Introduce parameter object** — group parameters that travel together.
- **Replace conditional with polymorphism / table** — only with two concrete use cases.
- **Split phase** — separate parse/compute/output stages.
- **Remove duplication** — only when duplicates are truly the same concept.

## Smells (signals, not orders)
Long function · long parameter list · duplicated logic · feature envy · shotgun surgery · deep nesting · unclear names · mixed abstraction levels. Never act on a smell outside the confirmed scope — add to noticed-not-touched.

## Characterization tests
- Pin **current** behavior, even if it looks wrong; never "fix" it in the test.
- Cover the paths the plan touches: normal, edge, error, odd branches flagged in recon.
- Use the repo's existing test framework, layout, and naming.
- Assert observable outputs (return values, side effects, serialized output), not internals.
- Run them green before any source edit. User confirms them before writing.
