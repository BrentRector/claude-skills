## 1. Decompose the standard into a rule catalog

One row per **normative rule**, not per section. Syntax rules, general (semantic) rules, constraints in
definitions, table cells that carry requirements, and MUST/SHALL sentences in prose each count. Give each row:

- a stable id (`<clause>/<rule-kind><n>`, for example `8.4.2/GR3` or `RFC9110-8.6/MUST2`);
- the verbatim rule text, extracted from the standard's own text (Markdown or plain text in the repo);
- the requirement level (MUST / SHOULD / MAY, or the standard's equivalent) and the editions or profiles it
  applies to;
- the definitions it depends on. The meaning of a term usually lives in a different clause.

Generate the catalog mechanically from the standard's text, and re-derive it when the text changes. A
hand-maintained catalog loses rules that are written as plain prose. Where a table or diagram carries the rule,
render the page (see `spec-oracle` §2): extracted figures skew toward falsely restrictive syntax.

For a very large standard, audit a named scope and say which clauses were NOT covered. Never imply that a
partial audit covered the whole standard. *(Validated 2026-09-28.)*
