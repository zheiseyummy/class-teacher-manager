# Design QA

## Reference and viewports

- Selected visual direction: `DESIGN.md` 中定义的克制型校园 SaaS 工作台
- Wide desktop viewport: `1440 x 900`
- Compact viewport: `390 x 844`
- Workbench: `docs/visual-qa-workbench.png`
- Compact workbench: `docs/visual-qa-workbench-compact.png`
- Student center: `docs/visual-qa-students.png`
- Compact student center: `docs/visual-qa-students-compact.png`
- Timetable: `docs/visual-qa-teaching-schedule.png`
- Calendar: `docs/visual-qa-planner.png`
- Backup center: `docs/visual-qa-backup.png`
- Teacher profile: `docs/visual-qa-teacher-profile.png`
- Compact teacher profile: `docs/visual-qa-teacher-profile-compact.png`
- Teacher greeting and sidebar footer: `docs/visual-qa-teacher-footer.png`

## Checked

- The formal PySide6 application now uses a light neutral navigation shell, white application header, pale gray workspace, and restrained blue primary actions.
- Brand, page title, page subtitle, current date, navigation state, and page-local actions have clear visual hierarchy.
- Navigation and frequent actions use bundled Lucide SVG icons, so their shape no longer depends on the active Windows or Qt theme.
- The student toolbar appears only on the student page and remains usable at the minimum window width.
- The workbench class selector remains interactive, while the current date is now a read-only display and cannot open a calendar or accept edits.
- Five metric cards use real SQLite counts for students, courses, attendance, events, and moral records.
- Course and event lists preserve real schedule details and avoid inventing unsupported task-completion state.
- Recent class activity combines real attendance and moral records.
- The lower-right panel compares the latest two same-semester exams for the selected class and shows student totals, class-rank changes, and the two largest common-subject changes.
- When two exams contain different subjects, the total row explicitly says that the subjects differ instead of presenting the raw total difference as directly comparable.
- Existing business pages render inside the new shell without clipping or overlapping.
- Workbench columns and rows remain draggable; existing resizable table columns and class semantic colors remain intact.
- Dashboard list rows now recalculate their width after window resizing, preserving course states, event categories, and score-change badges.
- Wide and compact screenshots show stable panel dimensions, normal icons, complete labels, and no incoherent overlap.
- The teacher profile dialog remains complete at both regular and minimum sizes; subjects, classes, semester, personal mark preview, privacy hint, and actions do not overlap.
- The workbench greeting uses the stored teacher name, while the sidebar footer keeps `v1.0.0` and the personal mark visible without reducing navigation space.

## Notes

- Final screenshots were captured with the native Windows Qt renderer; Chinese text and bundled SVG icons both render normally.
- The event model has no completion field, so the dashboard presents calendar items as real schedules instead of simulated checkable tasks.
- Arbitrary card drag, reorder, and resize remain intentionally deferred; the stable splitter layout is retained.

## Final result

Passed. The product-level UI, responsive compact layout and `v1.0.0` release presentation are complete. Detailed current evidence is recorded in `.design/UI_QA_REPORT.md` and `VISUAL_SCORECARD.md`.
