# Credits

`wave-grill` is adapted from two skills of [mattpocock/skills](https://github.com/mattpocock/skills)
at commit `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`, © 2026 Matt Pocock, used under the MIT
License reproduced in [LICENSE](LICENSE):

| upstream | here | how much |
|---|---|---|
| `skills/productivity/grilling/SKILL.md` | `SKILL.md` § The design tree, in rounds | almost word for word |
| `skills/engineering/domain-modeling/SKILL.md` | `SKILL.md` § The domain model, as you go | condensed |
| `skills/engineering/domain-modeling/GLOSSARY-FORMAT.md` | `references/glossary-format.md` | verbatim |
| `skills/engineering/domain-modeling/ADR-FORMAT.md` | `references/adr-format.md` | verbatim |
| `skills/engineering/to-tickets/SKILL.md` (wide refactors) | `SKILL.md` § Round 1, expand–contract | condensed |
| `skills/engineering/wayfinder/SKILL.md` (destination, fog, out of scope) | the decisions file's sections | the idea, reworded |

Upstream ships the first two as separate skills that `grill-with-docs` composes. Here they are
one skill, because the wave skills are installed on their own and a hard dependency on a second
plugin would break that.

Added for the wave flow, and not upstream: round 1's precondition / done-state / gates check, the
gates branch, and the decisions file written after every round.
