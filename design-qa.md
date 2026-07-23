# Design QA

## Reference and viewports

- Selected visual direction: `ui-prototype/artifacts/prototype-dashboard-final.png`
- Wide desktop viewport: `1487 x 1058`
- Minimum supported viewport: `1120 x 700`
- Workbench: `docs/visual-qa-workbench.png`
- Compact workbench: `docs/visual-qa-workbench-compact.png`
- Student center: `docs/visual-qa-students.png`
- Compact student center: `docs/visual-qa-students-compact.png`
- Timetable: `docs/visual-qa-teaching-schedule.png`
- Calendar: `docs/visual-qa-planner.png`
- Backup center: `docs/visual-qa-backup.png`

## Checked

- The formal PySide6 application now uses the approved solid-blue navigation, white application header, pale gray workspace, and restrained blue primary actions.
- Brand, page title, page subtitle, current date, navigation state, and page-local actions have clear visual hierarchy.
- Navigation and frequent actions use a consistent native icon treatment with tooltips where the label is hidden.
- The student toolbar appears only on the student page and remains usable at the minimum window width.
- Workbench class/date controls move into the common header without changing their data behavior.
- Five metric cards use real SQLite counts for students, courses, attendance, events, and moral records.
- Course and event lists preserve real schedule details and avoid inventing unsupported task-completion state.
- Recent class activity combines real attendance and moral records, while QtCharts renders the latest seven days.
- Existing business pages render inside the new shell without clipping or overlapping.
- Workbench columns and rows remain draggable; existing resizable table columns and class semantic colors remain intact.
- Wide and compact screenshots show stable panel dimensions and no incoherent overlap.

## Notes

- The offscreen Qt renderer does not load the local Chinese UI font, so Chinese glyphs appear as boxes in automated screenshots. The application requests `Microsoft YaHei UI`, which is available on the target Windows environment.
- The event model has no completion field, so the dashboard presents calendar items as real schedules instead of simulated checkable tasks.
- Arbitrary card drag, reorder, and resize remain intentionally deferred; the stable splitter layout is retained.

## Final result

Passed. The common PySide6 shell and formal workbench are ready for the score-analysis redesign.
