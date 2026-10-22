# Fiction Worldbuilding and Prose Craft Reference

This document provides complete domain knowledge for documentation-first fiction worldbuilding, scene authoring, canon consistency, and prose craft auditing using the Anvil skill (embodying the Worldsmith methodology).

---

## 1. The "Silmarillion Approach"

Worldsmith rejects ad-hoc worldbuilding where facts are improvised while drafting prose and forgotten three chapters later. It enforces the **Silmarillion approach**:
1. **The World Precedes the Story**: Establish the rules, chronology, geographies, cultures, and physical constraints before scenes unfold.
2. **Role-Based Canonical Authority**: Every fact has a single canonical source of truth in a role document.
3. **Strict Propagation Discipline**: When a creative choice alters world facts, update the canonical authority document *before* modifying manuscript prose. Never allow chapter prose to drift ahead of canon.

```
┌────────────────────────────────────────────────────────┐
│ Canonical World Documents (The Source of Truth)        │
│ Timeline • Lore • Characters • Systems • Conventions   │
└───────────────────────────┬────────────────────────────┘
                            │ Propagate changes downward
                            ▼
┌────────────────────────────────────────────────────────┐
│ Manuscript Prose (Chapters, Scenes, Fragments)         │
│ Chapter 01 • Chapter 02 • Chapter 03 ...               │
└───────────────────────────┬────────────────────────────┘
                            │ Craft & consistency audit
                            ▼
┌────────────────────────────────────────────────────────┐
│ Editorial Backlog & Cliche Checks                      │
│ Pattern counts, dialogue tags, timeline continuity     │
└────────────────────────────────────────────────────────┘
```

---

## 2. Canonical Document Roles

Worldsmith projects maintain role documents (typically inside `world/` or `.worldsmith/`):

| Role Document | Authority Scope | Critical Invariants |
|---------------|-----------------|---------------------|
| **Timeline** (`timeline.md`) | Chronological events, eras, ages, dates | No temporal paradoxes, character ages match event dates |
| **Lore** (`lore.md`) | Mythos, cultures, factions, geographies | Faction motivations must remain historically grounded |
| **Characters** (`characters.md`) | Biographies, psychology, voices, arcs | Distinct speech registers, concrete agency, clear flaws |
| **Systems** (`systems.md`) | Magic, technology, economies, laws | Explicit costs, hard constraints, clear failure modes |
| **Conventions** (`conventions.md`)| Style choices, formatting, capitalization | Consistent honorifics, spelling of fantasy terms |
| **Themes** (`themes.md`) | Core dilemmas, recurring motifs, symbolism | Drives character choice conflicts across arcs |
| **Backlog** (`editorial-backlog.md`)| Inconsistencies, plot holes, revisions | Priority queue for editorial polish passes |

---

## 3. Scene Drafting Discipline

Every scene must be drafted with intentional structural discipline:
1. **Sensory Anchors**: Ground the viewpoint character immediately in physical space (smell, texture, temperature, lighting) before dialogue or interiority begins.
2. **Scene Goal & Opposition**: The viewpoint character must enter with a concrete objective. Opposition must create immediate friction.
3. **Emotional Arc**: The viewpoint character's emotional state at the end of the scene must differ from their state at the beginning.
4. **Beats & Action Units**: Break scenes into micro-beats: Action -> Reaction -> Dilemma -> Decision.

---

## 4. Prose Craft Standards and Pattern Auditing

Anvil enforces rigorous prose craft standards designed to eliminate AI writing habits and commercial fiction cliches:

### A. Crutch Words
Words that pad sentences without adding meaning. To be pruned ruthlessly:
- `just`, `really`, `very`, `actually`, `basically`, `simply`, `quite`, `merely`, `something`

### B. Filter Words (Sensory Distancing)
Phrases that place an unnecessary narrator lens between reader and character experience:
- *Distanced*: "She could hear the iron gate screech shut."
- *Direct*: "The iron gate screeched shut."
- *Audit targets*: `could see`, `could feel`, `could hear`, `could sense`, `could notice`, `seemed to`, `appeared to`

### C. Weak / Inceptive Verbs
Verbs that delay the actual action:
- *Weak*: "He started to draw his blade."
- *Active*: "He drew his blade."
- *Audit targets*: `started to`, `began to`, `tried to`, `managed to`, `continued to`

### D. Dialogue Tag Craft
- **Golden Rule**: Use bare `said` or `asked`, or preferably use an **action beat**.
- **Adverb Dialogue Tags**: Strictly banned (`"..." said angrily`, `"..." asked suspiciously`).
- **Fancy Dialogue Tags**: Banned in narration (`"..." mused / declared / sneered / hissed / roared`).
- Matcher restriction: Dialogue tag audits only evaluate lines containing quotation marks.

### E. Stock Body Reactions (Melodrama)
Clichéd physiological shortcuts that substitute for nuanced emotional response:
- `heart raced`, `heart pounded`, `heart skipped a beat`, `eyes widened`, `eyes went wide`, `breath caught`, `blood ran cold`, `hair stood on end`
- *Remediation*: Show the specific behavioral choice or tactile reaction unique to that character.

### F. Dead Metaphors & Emotional Labeling
- Dead metaphors: `knot in stomach`, `weight of the world`, `sent a chill down`, `stone-cold`
- Emotional labeling: "She was terrified." -> *Show the somatic reality, thought sequence, and defensive impulse.*

---

## 5. Decision Handoff Protocol

When drafting or auditing generates creative decisions (e.g., character fate, magic cost, plot branch):
1. The assistant must never guess or make irreversible canon decisions arbitrarily.
2. Draft the recommended option marked with a provisional finding tag:
   ```markdown
   [PROVISIONAL YYYY-MM-DD id=canon-branch-01]
   Text containing the proposed choice...
   ```
3. Present the author with a structured `Decisions Needed` prompt:
   - Question
   - Concrete alternatives (2-4 choices with trade-offs)
   - Assistant's recommended option with rationale
