# UI QA Report

## Scope

- Product: 班主任综合管理系统（PySide6 / Windows 本地桌面端）
- QA date: 2026-08-30
- Main viewports: 1440 x 900、390 x 844
- Data policy: 全部截图使用临时 SQLite 数据库和确定性的演示姓名、学号；未读取或写入用户的真实学生数据库。

## Screenshot Matrix

| Scenario | Screenshot | Result |
|---|---|---|
| Desktop workbench | `.design/screenshots/after-desktop.png` | Pass |
| Compact workbench | `.design/screenshots/after-mobile.png` | Pass |
| Compact student center | `.design/screenshots/after-students-mobile.png` | Pass |
| Compact student form | `.design/screenshots/after-student-form-mobile.png` | Pass |
| Compact teacher profile | `.design/screenshots/after-profile-mobile.png` | Pass |
| Compact quality center | `.design/screenshots/after-quality-mobile.png` | Pass |
| Compact final quality review | `.design/screenshots/after-quality-review-mobile.png` | Pass |
| Compact scores | `.design/screenshots/after-scores-mobile.png` | Pass |
| Compact attendance | `.design/screenshots/after-attendance-mobile.png` | Pass |
| Compact schedule/calendar | `.design/screenshots/after-planner-mobile.png` | Pass |
| Compact backup center | `.design/screenshots/after-backup-mobile.png` | Pass |

## Checks

| Check | Observation | Result |
|---|---|---|
| Information hierarchy | Page title, context, primary action, data surface and detail surface are visually distinct. | Pass |
| Navigation | Light desktop sidebar has clear selected state; compact mode exposes every module through the top-left menu. | Pass |
| Text and controls | Chinese text renders correctly with native Windows Qt; controls remain readable at 390px logical width. | Pass |
| Tables | Low-priority columns are hidden where appropriate; complete data remains available through controlled horizontal scrolling. | Pass |
| Split panes | Desktop panes remain draggable; compact mode changes horizontal panes to vertical flow. | Pass |
| Forms and dialogs | Student form and teacher profile scroll; final review keeps filters, actions and the complete wide table usable. | Pass |
| States | Empty data, no filtered results, disabled actions, selection, hover and keyboard focus have explicit styling. | Pass |
| Risk actions | Delete, restore and final-result locking retain confirmation steps; disabled danger buttons no longer appear active. | Pass |
| Overflow | No incoherent overlap was found; wide tables use visible horizontal scroll instead of clipping values. | Pass |
| Privacy | No real names, phone numbers, addresses, grades or parent details appear in QA artifacts. | Pass |

## Iterations Applied After QA

1. Replaced the saturated blue sidebar with a light neutral shell and reduced decorative color area.
2. Added true compact navigation and reflowed module toolbars, metric cards and split panes at widths below 840px.
3. Added reusable empty states and separate actions for missing data versus no search results.
4. Hid low-priority columns in compact tables while retaining complete data and horizontal scrolling where necessary.
5. Added responsive dialog sizing and scroll containers for long forms.
6. Changed disabled primary and danger buttons to neutral styling to avoid suggesting that unavailable actions can be clicked.
7. Re-captured screenshots with native Windows Qt after confirming that offscreen Qt lacks the correct Chinese font fallback.

## Residual Notes

- The application is a Windows desktop program. The 390 x 844 result validates a narrow desktop window, not an Android or iOS build.
- High-dimensional score and final-review tables intentionally retain horizontal scrolling in compact mode so no source field is discarded.
- Native screenshot capture prints non-blocking PNG ICC profile warnings from existing image/icon assets; rendered output is correct.

## Verdict

Pass. The average visual score is 4.45/5, above the required 4.0 threshold. No additional visual iteration is required before delivery.
