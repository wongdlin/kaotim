# kaotim-refactor: high tier only

Load only when the confirmed tier is high.

- Full gates every phase; smaller steps than medium.
- Every plan step touching a public interface, shared module, schema, or serialized format gets an explicit risk callout.
- Recommend splitting into sub-refactors; offer each in a fresh session with only the state note.
- Public surface change → stop; propose compat/migration plan (e.g. keep old entry point delegating to new; deprecate later); proceed only after explicit approval.
- No tests → characterization tests first (`techniques.md`), or explicit waiver plus fallback: smaller steps and a manual verification checklist.
- Data formats: pin current serialized output with characterization tests before any move/rename.
