# 0008. Two independent layout engines

Status: accepted

## Context
The start page needs a free layout (move, resize, hide, with a separate phone layout). The cockpit needs a strict hierarchy, Tab › Row › Tile, that keeps its order on a phone. Merging both into one engine would make each of them worse.

## Decision
Two JSON document formats, two tables, and two modules in both the back end and the interface, with no dependency between them. The start page uses an in-house column grid with collision handling, kept inside the width of the search bar. The cockpit uses nested sortable lists.

## Consequences
- Each engine stays small and fits its purpose. The in-house grid is about 10 KB and handles keyboard and touch.
- Two editors to maintain. They share only the design system and the base widgets.
