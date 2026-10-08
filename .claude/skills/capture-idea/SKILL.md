---
name: capture-idea
description: Record, organize, update, or combine ideas in this project's isolated Idea Lab. Use when the user has an inspiration, speculative solution, failed attempt, blocker, restart condition, or asks to preserve, revisit, relate, merge, or develop an Idea without turning it into a knowledge page.
---

# Capture Idea

Work only inside `ideas/`. Do not run or modify the main knowledge base index, taxonomy, graph, pages, or ingestion workflow.

## Capture quickly

When the user wants to preserve a new thought:

1. Read `ideas/README.md` and `ideas/_index.md`.
2. Search `ideas/pages/` for the same problem, mechanism, blocker, and synonyms.
3. Preserve the user's original wording verbatim.
4. If it is genuinely new, run:

   ```bash
   python3 ideas/scripts/new_idea.py "原始想法" --title "简洁标题" --problem "想解决的问题" --domains "领域1,领域2"
   ```

5. If an existing Idea is the same thought, append an evolution note or attempt instead of creating a duplicate.

Do not require a source, confidence rating, polished explanation, or complete plan. If the user only gives one sentence, save it without delaying capture for optional fields.

## Preserve reasoning history

- Never replace the `## 原始想法` text with a polished rewrite.
- Separate observed facts, assumptions, and personal judgment.
- Append attempts chronologically; do not silently rewrite an earlier result.
- For an unsuccessful attempt, record the adopted approach, observed result, failure or limitation, reusable portion, and restart condition.
- Use `blocked` only when at least one concrete blocker is recorded.
- Use `abandoned` only when the page records an explicit reason for abandoning it.

## Find combination opportunities

Compare a new or updated Idea against old Ideas using:

- the same or similar problem;
- a new capability matching an old `blockers` item;
- a new condition matching an old `restart_when` item;
- shared domains, external references, or complementary mechanisms.

Report candidate IDs, titles, and the concrete matching reason. Do not merge automatically and do not present the match score as proof of feasibility.

When the user confirms a combination:

1. Create a new Idea page rather than overwriting either source.
2. Add all source IDs to the new page's `derived_from`.
3. Add the new ID to every source page's `combined_into`.
4. Explain what each source contributes, which blocker is addressed, new risks, and the smallest validation step.
5. Treat all related page writes as one logical operation; do not leave one-way relations.

## Finish

Run only the isolated generators and health check:

```bash
python3 ideas/scripts/build_idea_index.py
python3 ideas/scripts/render_idea_graph.py
python3 ideas/scripts/check_idea_health.py
```

Require `ERROR 0` before completion. Review the diff and stage only the Idea pages and Idea Lab generated files changed by this operation. Do not include unrelated worktree files.
