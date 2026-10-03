# Docs and honesty (engineering-standards section 6)

## 6. Docs and honesty

- **Keep docs current in the same change set.** Design docs, README, API docs and the project instructions
  describe the code as it is NOW. History (what changed, what was tried) belongs in the commit message and the
  changelog or dev log, never in the design doc.
  *Why: a stale design doc tells the next implementer to build the rejected approach.* *(Practice — not yet validated: no measured effect, and a live-state document still accumulated history.)*
- **Implement from the design doc; a design correction updates the doc in the same change.**
- **Sweep docs on discovery.** When a doc is wrong, fix it and every other doc that repeats the stale fact, now.
- **Comments carry the WHY.** Document every public type and member; comment non-obvious logic; never narrate
  "this used to do X". A comment that lies is worse than none.
- **Cite the authority in the code.** A rule implemented from a spec names its clause at the implementation site.
- **Forensic commit messages.** A subject, then what changed, why, what was considered and rejected.
- **Report honestly and calibrated to the evidence.** Never write "verified", "complete" or "no regressions"
  without the evidence in hand. Say which gates ran, what they covered, and what is still pending.
  *Why: the closing summary line is where overreach creeps in, and it is the line others act on.*
- **Say it immediately when you were wrong.** Record the misstep, its cause and the fix, clinically. Never
  minimize, and never present a guess, a recollection or training data as measured fact. *(Practice — not yet validated: no measured effect.)*
