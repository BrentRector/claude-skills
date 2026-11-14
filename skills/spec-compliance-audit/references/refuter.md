## 6. The adversarial refuter on every CLOSING verdict

The agent that produced a verdict is biased toward it. Send every verdict that would CLOSE a row
(`CONFORMS`, `DOCUMENTED-NON-SUPPORT`) and every divergence (`PARTIAL`, `DIVERGES`, `NOT-IMPLEMENTED`) to at
least one independent agent that did not produce it. Its instruction is to refute: re-read the rule, look for a
more specific rule that overrides it, walk the paths again, and check that the witness actually exercises the
governed branch. Drop or downgrade whatever it knocks down. If the refuter itself fails, the verdict is
**unverified**, not confirmed. Record it that way.

When the refuter agrees, check that it agrees with the REASONING, not just the label. A right verdict reached for
a wrong reason gets its reasoning corrected in the record.

The refuter also checks the premise. A finding can quote a real rule correctly and still describe input that the
grammar or format makes impossible. If you cannot write the witness's input legally, the finding is refuted.

**The readers get the refuters' categories before they submit.** Each verdict record answers, as yes/no fields,
the questions refuters overturn verdicts on, so the author checks them first:
- **Does the witness exercise THIS rule's branch**, and was it seen to fail under the recorded mutation (§5)?
- **Is the citation re-checked** for clause, rule kind and quote, by the checker, in this batch?
- **Does the citation's edition match** the edition the behavior is for (`spec-oracle`, "One edition's rule
  answering for another")?
- **Is the expected value derived from the rule**, not observed from the implementation or another one?
- **Is the premise expressible**: can the witness's input be written legally?

In one audit lane's 67 overturns, the causes were: the witness did not exercise the rule 27, citation 16, edition
11, expected value not spec-derived 9, other 3.

**Report the overturn rate per batch, by category, beside GAP.** It is the measure of first-pass quality. Across
five lanes over three months, refuters overturned 29-42 % of first-pass verdicts and the rate did not fall, while
the categories stayed with the refuters. A falling rate shows the pre-submit answers working; a flat one shows
they are being filled in without being checked.

**What the pre-submit answers cannot catch.** A careful reader who answers every field truthfully can still misread
the right rule. No instruction prevents that; the independent refuter, the differential and the next reader find
it. That is why the refuter runs on every closing verdict, whatever the record answers.
