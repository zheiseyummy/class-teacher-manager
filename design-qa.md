# Design QA

## Reference and viewport

- Selected reference: `C:\Users\zhengheisey\.codex\generated_images\019f6135-56b0-7be0-aaea-61b57946bbc7\exec-537675ad-54a4-4997-a61e-dc3944055abf.png`
- Reference viewport: `1487 x 1058`
- Prototype screenshot: `docs/visual-qa-workbench.png`
- Independent timetable screenshot: `docs/visual-qa-teaching-schedule.png`
- Calendar screenshot: `docs/visual-qa-planner.png`
- Backup center screenshot: `docs/visual-qa-backup.png`
- Side-by-side comparison: `docs/visual-qa-comparison.png` (reference on the left, application on the right)

## Checked

- Default landing state is the daily class workbench; the student-center toolbar is hidden until its own navigation item is selected.
- The left navigation, pale gray work area, white data surfaces, thin separators, jade primary action, and restrained class-color accents follow the selected office-workbench direction.
- Workbench controls navigate to the timetable, open the calendar-entry dialog, and open the existing attendance and moral-evaluation modules.
- Class colors are persisted in SQLite and appear in timetable cells, class badges, calendar markings, and event rows.
- Courses, class events, global events, daily course lists, and daily statistics render with seeded local data.
- The independent timetable renders five teacher-defined periods, start/end times, seven weekdays, three differently colored teaching groups, and the all-groups summary state without requiring a student class for the evening-study group.
- The backup center keeps destructive restore secondary to clear manual and scheduled backup actions, with a configurable local destination and readable backup history in the same desktop-workbench style.
- The workbench and calendar both retain draggable splitters and user-resizable table columns.

## Notes

- The offscreen Qt renderer used for automated screenshots does not load the local Chinese UI font, so Chinese glyphs appear as boxes in the generated QA images. The application stylesheet explicitly requests `Microsoft YaHei UI`, which is available on the target Windows desktop environment.
- The reference shows a product concept with attendance and parent-contact queues. The implemented workbench keeps the same daily-work structure while presenting the modules and local records that currently exist in this application.

## Final result

Passed. The visible startup-state mismatch found during the first capture was fixed, then the workbench and calendar were captured again at the reference viewport for final comparison.
