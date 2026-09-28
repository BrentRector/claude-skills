---
# The PUBLISHED NARRATIVE form: one post per milestone or finding, readable by outsiders, on a site whose content
# collection holds these files (for example src/content/devlogs/<series>-<slug>-YYYY-MM-DD.mdx). A post is written
# from the working history's entries, never instead of them. Reversals are published too, as their own post.
title: "<The finding, stated as a claim: 'The timeout was never the network; it was the lock order'>"
date: YYYY-MM-DD
project: "<series-slug>"
tags:
  - <series-slug>
  - <topic>
status: active          # active | archived
tldr: "<Two sentences: what is now known, and what it changes.>"
outcome: success        # success | partial | failure | overturned
---

<!-- When this post overturns an earlier one, open with a one-line banner that links it, and leave the earlier post
     up with a link forward. Readers who arrive at the old post must be able to find the correction. -->
*Overturns [<earlier post title>](/devlogs/<earlier-slug>/). <Which parts still stand, and which do not.>*

<The finding, first paragraph: what was observed, under what conditions, with the numbers.>

<How it was established: the method, the experiment, the measurement. Enough that a skeptical reader could repeat it.>

<What was wrong before, if anything, and why it looked right at the time.>

**Status:** <what is demonstrated, what is still open, and what the next post will test.>
