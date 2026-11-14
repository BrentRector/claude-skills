## 7. Cluster findings by mechanism into tracked work

Do not file one ticket per rule. Group the open rows by **root cause**: the same dispatch, the same table, the
same rule written down in two places. File one work item per mechanism, listing every inventory row it claims.
When the fix lands, the item records which rows it CLOSED (or why it closed none), and GAP moves in the same
change. A finding that exists only in an audit report or a log paragraph is invisible to every work list and
will rot there.

Rank the work by what the defect DOES to a user's program or data: a wrong answer, a crash, or rejecting legal
input. Do not rank by the label a finding happened to get. Give each implementer one mechanism, or a
group of related ones that share files (see `agent-fleet`), and sweep its siblings (paired functions, other arms
of the same dispatch) before calling the cluster done.
