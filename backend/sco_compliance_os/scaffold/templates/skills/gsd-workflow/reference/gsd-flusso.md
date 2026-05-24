# GSD - flusso canonico (sintesi)

Ciclo: new-project (domande -> research agents -> requisiti -> roadmap, approvazione) ->
discuss-phase (decisioni implementative -> CONTEXT.md) ->
plan-phase (research paralleli + planner + plan-checker -> task atomici) ->
execute-phase -> verify-work -> ship -> audit/complete-milestone -> milestone-summary -> extract-learnings.

Artefatti GSD (.planning/): PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md,
phases/NN-nome/{CONTEXT.md, RESEARCH.md, NN-NN-PLAN.md}, MILESTONES.md.

Comandi principali (forma /gsd-...): new-project, discuss-phase, plan-phase, execute-phase,
verify-work, ship, audit-milestone, complete-milestone, milestone-summary, new-milestone,
progress, resume-work, pause-work, manager, quick, autonomous, explore, spike, sketch,
extract-learnings, forensics, code-review.

Namespace router: /gsd-workflow (discuss/plan/execute/verify/phase/progress),
/gsd-project (milestones/audit/summary), /gsd-quality (review/debug/audit/security/eval/ui),
/gsd-context (map/graphify/docs/learnings), /gsd-manage (config/workspace/thread/update/ship),
/gsd-ideate (explore/sketch/spike/spec/capture).

Principi: piano verificato contro l'obiettivo prima di eseguire; gate di verifica reale prima
di "fatto"; context machine-greppabile a predicati; retrospettiva con cattura dei learnings.
