# Workforce Scheduling & Validation Demo

A Python project that creates deterministic synthetic workforce data and validates schedules against leave, skills, staffing, overtime, attendance, and shift-swap rules. All records are synthetic; no employee personal data is used.

## Web app (interactive demo)

`docs/index.html` is a single-file web app. It re-implements the generator and validator in JavaScript so you can explore the data without installing Python.

- Generates teams, employees, skills, shifts, leave, attendance and swaps from a seed, then validates them against the rules below.
- Schedules assign each shift to the qualified person with the fewest hours so far, respecting approved leave, weekly caps and a one-shift-per-day limit.
- Swaps need a manager other than the requester. Leave decisions and swap steps are stored as events, not overwritten.
- A **Live** tab lets you request leave or swaps, decide them, and watch coverage and issues update. Shared real-time updates only work when the page is opened inside claude.ai; anywhere else (including GitHub Pages) it runs in single-tab mode.
- A "Regenerate twice and compare" button on the Data tab checks reproducibility.

Run it locally by opening `docs/index.html` in a browser. To host it, enable GitHub Pages (Settings, Pages, branch `main`, folder `/docs`).

Note: the browser version uses its own seeded random generator, so a given seed gives repeatable results there but not the same rows as the Python CLI.

## Features

- Master data first: teams, skills, employees, employee-skill bridge, shift templates.
- Transaction/event data: coverage requirements, shift assignments, leave requests, attendance events, swaps, holidays.
- Deterministic, zero-padded IDs and fixed-seed generation.
- Labelled edge cases in a separate `ground_truth.csv`.
- Validation reports for foreign keys, duplicate IDs, skill eligibility, leave conflicts, coverage gaps, overtime, attendance consistency, and unapproved swaps.
- Reproducibility manifest with row counts and SHA-256 checksums.
- CLI and automated tests.

## Requirements

- Python 3.10+
- pip

## Quick start (Windows PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
python -m workforce_scheduler.cli generate --out data/generated --seed 20261022
python -m workforce_scheduler.cli validate --data data/generated --reports reports
pytest
```

If PowerShell blocks activation, run the commands without activation using `.venv\Scripts\python.exe -m pip install -e ".[dev]"`, then replace `python` with `.venv\Scripts\python.exe`.

## Smaller run while developing

```powershell
python -m workforce_scheduler.cli generate --out data/starter --seed 20261022 --employees 100 --teams 10 --days 7 --leaves 100
python -m workforce_scheduler.cli validate --data data/starter --reports reports/starter
```

## Full data volume

The default generator creates 2,000 employees, 100 teams, 90 days of shifts, and 5,000 baseline leave requests. It writes CSV files and `manifest.json`. Use the smaller run first to verify the environment, then run the default command.

## Data files

| File | Purpose |
|---|---|
| `teams.csv` | Team master and effective dates |
| `skills.csv` | Skill catalogue |
| `employees.csv` | Employee master, team, weekly cap and overtime cap |
| `employee_skills.csv` | Many-to-many employee/skill bridge |
| `shift_templates.csv` | Shift codes, times and durations |
| `holiday_calendar.csv` | Clearly marked illustrative holiday rows |
| `coverage_requirements.csv` | Minimum qualified staffing by team/shift/skill |
| `shift_assignments.csv` | Employee-to-shift assignments |
| `leave_requests.csv` | Leave lifecycle and approval outcome |
| `attendance_events.csv` | Attendance linked to an assignment |
| `swap_requests.csv` | Swap request, manager approval and application state |
| `ground_truth.csv` | Expected labels for deliberately injected anomalies; never merge into model/input features |

## Data model and relationships

- Team 1:N Employee; each employee belongs to one team at a time.
- Employee N:M Skill through `employee_skills`.
- ShiftTemplate 1:N ShiftAssignment.
- Employee 1:N ShiftAssignment, LeaveRequest, and AttendanceEvent.
- ShiftAssignment 1:N AttendanceEvent (for clock events).
- ShiftAssignment 1:N SwapRequest as the source assignment.
- Team/Shift/Skill 1:N CoverageRequirement over effective dates.
- HolidayCalendar is independent calendar reference data.

Every table has a primary key except the bridge table, whose composite key is `(employee_id, skill_id)`. Foreign keys are validated by the validation command. IDs are stable within a generated dataset; regenerating with the same parameters and seed produces the same CSV checksums.

## Business rules

1. An assignment must reference existing employee, team and shift template IDs.
2. An employee must possess the skill required by a matching coverage requirement.
3. Approved leave cannot overlap a scheduled shift date.
4. Qualified unique employees are counted against minimum staffing; shortfalls are coverage gaps.
5. Applied swaps require `APPROVED` status and a manager approver.
6. Weekly scheduled hours above the employee's weekly cap are overtime; hours above weekly cap plus overtime cap are violations.
7. Attendance events must refer to an existing assignment for the same employee.
8. Deliberate negative cases are tagged in `ground_truth.csv`, separately from input tables.

## Outputs

The validation command writes:

- `validation_issues.csv` — issue type, record ID, and explanation.
- `coverage_report.csv` — required staff, qualified staff, coverage gap and pass/fail.
- `overtime_report.csv` — weekly scheduled hours, cap, overtime and cap exception.
- `validation_summary.json` — measurable summary metrics.

## Validation and reproducibility

Run generation twice with the same seed and parameters into two different folders and compare `manifest.json` checksums or CSV SHA-256 values. The test suite includes reproducibility, ID checks, and exception-path checks.

## Limitations / production considerations

This is a synthetic assessment demo, not a production rostering engine. The generator seeds baseline assignments and the validator exposes conflicts; it is not a constraint-optimization solver. The weekly hours calculation is a scheduled-hours proxy. A production system should add hard scheduling constraints, minimum rest periods, rolling work-hour windows, timezone/DST handling, jurisdiction-specific holiday calendars, robust swap target validation, audit-event append-only storage, and a database-backed transaction layer. Public-holiday rows are illustrative and must not be treated as an authoritative legal calendar.

## Lawful provenance

All records are synthetically generated by this repository. No external employee data is used. The sample holiday names are illustrative labels only.
