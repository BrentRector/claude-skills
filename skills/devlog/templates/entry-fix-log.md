<!-- The DEFECT/FIX LOG form: one entry per defect fixed in shipped code, for reviewers and source-license
     customers. Refactors, features and doc-only changes do not belong here. Newest section first; add the entry in
     the same commit as the fix. The header block below goes once at the top of the file. -->

# Fix log

**Audience:** anyone reviewing a behaviour-changing fix: the author of the next change in the same area, a reviewer
deciding whether a release is safe, a source-license customer asking why the code looks the way it does.

**What belongs here.** One entry per defect fixed in shipping code, written so the change can be reviewed without
reading the diff first: what a user saw, what caused it, what changed, why that shape and not an easier one, and how
the guard was proven able to fail. Pure refactors, new features and documentation-only changes do not belong here.

**What does not belong here.** This is an internal document. It names files and internal mechanisms that do not
belong in customer-facing material (package descriptions, the website, the public changelog).

**Maintaining it.** Newest section first. Each entry carries its commit, the files it touched and the guard that
holds it, so a reviewer can go straight to the test and try to break it.

---

<!-- Optional: a table of every change that alters the product's output, and what it reaches, so a release knows
     what to re-validate. -->

# YYYY-MM-DD — <theme of the day's fixes>

## NN. <What the user saw, in one line>

**Commit:** <sha> · **Files:** `<path>`, `<path>` · **Guard:** `<TestClass.TestName>`

**Symptom.** What a user saw, in their terms: the input, the output, the message.

**Cause.** The mechanism, not the symptom restated. Name the place where the wrong assumption lived.

**Fix, and why this shape.** What changed, and why not the easier fix (a check at the throw site, a special case,
a retry). Name every path that reaches the same mechanism and say how each one is covered.

**Proof the guard can fail.** The test fails on the parent commit (or with the fix reverted), with this message:
`...`. A guard that has never failed has not been shown to guard anything.
