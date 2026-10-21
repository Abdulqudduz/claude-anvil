# JOSS Exemplar (Current Format)

One R package paper, checked against its source `paper/paper.md`, that was published under the current JOSS paper format: Summary, Statement of need, State of the field, Software design, Research impact statement, and AI usage disclosure are all present. Papers published before that format (most JOSS papers before 2026) lack those sections. Do not model a new paper on them.

Verified 2026-10-21 against https://github.com/sysbiolab/RGraphSpace/blob/HEAD/paper/paper.md.

## RGraphSpace: Rendering graphs as coherent spatial objects in ggplot2

- **DOI**: 10.21105/joss.11209 (JOSS 11(126), 11209)
- **Submitted / published**: 1 August 2026 / 15 October 2026
- **Repository**: https://github.com/sysbiolab/RGraphSpace (paper in `paper/`, with `paper.bib` and three figures)
- **Length**: about 1,600 words of body text including figure captions, near the top of the 750-1750 range
- **Section order**: Summary, Statement of need, State of the field, Research impact statement, Software design, Availability and documentation, AI usage disclosure, Acknowledgements, References

### Frontmatter patterns

- `date: "16 July 2026"`: the `%e %B %Y` format, no leading zero.
- Five tags, starting with `R`.
- Every author has a quoted ORCID; `equal-contrib: true` on three authors and `corresponding: true` on one.
- The affiliation carries a `ror:` identifier.
- Extra keys (`output:` for R Markdown rendering) are tolerated.

### How each required section is written

- **Summary**: one paragraph. It opens with the general concept (what a graph is), names the two packages the work bridges with citations (`igraph`, `ggplot2`), states the specific technical limitation ("each plot layer consumes a single rectangular table and is resolved independently"), then introduces the package as the fix.
- **Statement of need**: names the existing stack (`igraph`, `ggplot2`, `ggraph`, `tidygraph`) and pinpoints the gap concretely: "edges have no access to the rendered sizes of the nodes". A captioned figure (`\autoref{fig:figure1}`) shows the failure mode it fixes.
- **State of the field**: positions the package within the Grammar of Graphics lineage, credits the competitors (`ggraph`, `ggnetwork`, `GGally`, `sf` as an analogous extension) as real strengths, then states the one thing they do not do: "They do not, however, synchronize node and edge geometry during rendering." It ends with the build-vs-contribute answer: the package integrates with `tidygraph` and contributes only "the rendering step".
- **Research impact statement**: two sentences of concrete evidence: a downstream package that depends on it (`PathwaySpace`) and two published analyses that used it, all cited. No aspirational claims.
- **Software design**: the core S4 class and its slots, a memory trade-off (features in a sparse-matrix slot rather than the node table), the coordinate normalization rules, and how it hooks the `ggplot2` build pipeline. A second figure diagrams the architecture.
- **AI usage disclosure**: two sentences naming the tools and vendors (ChatGPT, Claude), the scope ("improve text readability and assist with code audit and review"), and the authors' review and responsibility.

### Takeaways for drafting

1. Name the precise technical gap in one sentence and reuse it across Summary, Statement of need, and State of the field.
2. In State of the field, praise competitors accurately, then state the single missing capability.
3. Keep the Research impact statement short and fully cited; downstream packages and published uses are the strongest evidence.
4. Spend the word budget on Software design, where reviewers learn the architecture and trade-offs.
5. Figures earn their place when they show the failure mode or the architecture.
