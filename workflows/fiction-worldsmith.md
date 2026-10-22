# Workflow: Fiction Worldbuilding and Novel Authoring

This runbook guides an AI agent through the Worldsmith methodology: documentation-first worldbuilding, canonical authority tracking, scene drafting, and prose craft auditing.

---

## Prerequisites and Setup
1. **Detect or Initialize Project**:
   - Run `python3 scripts/anvil detect`.
   - Initialize project structure with `project.yaml` using `assets/templates/worldsmith-project-template.yaml`.
2. **Review Domain Reference**:
   - Consult [fiction-worldbuilding.md](../references/fiction-worldbuilding.md) for detailed craft rules.

---

## Phase 1: Canonical World Initialization

1. **Establish Canonical Authority Documents**:
   - `world/timeline.md`: Chronological backbone of eras, events, character birthdates.
   - `world/lore.md`: Cosmological rules, cultural factions, magic/technology constraints.
   - `world/characters.md`: Psychologies, vocal registers, agency goals, and relational tensions.
   - `world/systems.md`: Explicit magic/tech rules, material costs, and failure modes.
   - `world/conventions.md`: Typography, naming conventions, and viewpoint discipline.
2. **Review Canon Invariants**:
   - Verify timeline has no paradoxes.
   - Ensure character goals create immediate friction with established faction lore.

---

## Phase 2: Scene Design and Drafting

1. **Define Scene Beat**:
   - Identify viewpoint character, location, opening physical state, and scene objective.
2. **Drafting Execution**:
   - **Sensory Anchoring**: Ground the viewpoint character in tactile, olfactory, and auditory physical reality before dialogue starts.
   - **Active Character Agency**: Every decision must arise from the character's internal priorities, not arbitrary plot convenience.
   - **Dialogue Craft**: Use bare dialogue tags (`said`, `asked`) or action beats. Eliminate adverb dialogue tags (`said angrily`) and fancy tags (`sneered`, `mused`).
3. **Provisional Choices**:
   - If a creative choice alters world facts, mark it `[PROVISIONAL YYYY-MM-DD id=<id>]` and update the relevant canon doc first.

---

## Phase 3: Prose Craft and Cliche Auditing

1. **Run Automated Pattern Audits**:
   - Execute the pattern checker against drafted scenes:
     ```bash
     python3 scripts/anvil check-prose "chapters/*.md"
     ```
2. **Evaluate Specific Categories**:
   - **Crutch Words**: Remove `just`, `really`, `very`, `actually`, `basically`, `simply`.
   - **Filter Words**: Convert distanced perceptions (`could hear the bell toll`) to immediate sensory events (`the bell tolled`).
   - **Weak Inceptive Verbs**: Replace `started to run` with `ran`.
   - **Stock Melodrama**: Replace `heart raced`, `eyes widened`, `breath caught` with nuanced somatic behavior.

---

## Phase 4: Canon Propagation and Editorial Polish

1. **Verify Downward Propagation**:
   - Ensure changes made to character knowledge or world state are reflected in `world/timeline.md` and `world/characters.md`.
2. **Update Editorial Backlog**:
   - Record minor continuity questions in `world/editorial-backlog.md`.
3. **Decision Handoff**:
   - Present unresolved creative forks to the author with structured options and recommendations.
