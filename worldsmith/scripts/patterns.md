# Prose Patterns

Default pattern list for worldsmith prose audits and the cliche hook. To
customize per project, copy this file to `.worldsmith/patterns.md` in your
project root and edit it.

To add a pattern: add it to the comma-separated list under the right category.
To add a category: add a `## Category Name` heading with patterns below it.
To use a regex: `<!-- regex: your_pattern_here -->` on its own line.

Literal patterns match case-insensitively on word boundaries ("mused" does not
match "amused"). Regexes are case-insensitive too; use `(?-i:...)` to make a
part case-sensitive.

Category directives, each an HTML comment on its own line:

- `<!-- hook: block -->` makes the category hook-enforced: the PostToolUse
  cliche hook flags any match in a manuscript Write/Edit. Other categories are
  only counted by `count_patterns.py` audits.
- `<!-- hint: ... -->` is the advice printed next to each hook violation.
- `<!-- scope: dialogue-lines -->` restricts matching to lines that contain a
  double quote (for dialogue tags; "The king declared war" is fine narration).

If a project override declares no hook-enforced category, the hook falls back
to the hook-enforced categories in the bundled default file, so an older
override never silently disables the hook. To disable the hook for a project,
keep a hook-enforced category with no patterns.

## Crutch Words

something, just, really, very, actually, basically, simply, quite, merely

## Filter Words

could see, could feel, could hear, could sense, could notice, seemed to, appeared to, happened to

## Weak Verbs

started to, began to, tried to, managed to, continued to

## Adverb Dialogue Tags

<!-- regex: \b(said|asked|replied|whispered|shouted)\s+(?-i:[a-z])\w*ly\b -->

## Stock Body Reactions

<!-- hook: block -->
<!-- hint: show it, don't name the sensation -->
heart raced, heart pounded, heart skipped, eyes widened, eyes went wide, breath caught, blood ran cold

## Dead Metaphors

<!-- hook: block -->
<!-- hint: show it, don't name the sensation -->
sent a chill down, a chill ran down, weight of the world, knot in her stomach, knot in his stomach

## Emotional Labeling

<!-- hook: block -->
<!-- hint: show it, don't name the sensation -->
couldn't help but think, couldn't help but feel, couldn't help but notice, a mixture of excitement, filled with a sense of, let out a breath, didn't realize they had been holding

## Redundant Adverbs

<!-- hook: block -->
<!-- hint: the adverb duplicates the verb; cut it or choose a more precise verb -->
whispered quietly, shouted loudly, sprinted quickly, crept slowly, muttered softly, screamed loudly, tiptoed quietly, rushed hurriedly

## Fancy Dialogue Tags

<!-- hook: block -->
<!-- hint: use "said" or a physical beat instead -->
<!-- scope: dialogue-lines -->
exclaimed, opined, mused, interjected, proclaimed, declared, retorted, quipped, remarked
