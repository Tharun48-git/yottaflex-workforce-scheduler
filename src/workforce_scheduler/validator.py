from __future__ import annotations
from pathlib import Path
import json
import pandas as pd

def load_tables(data_dir: str | Path) -> dict[str, pd.DataFrame]:
    d = Path(data_dir)
    names = ["teams", "skills", "employees", "employee_skills", "shift_templates",
             "holiday_calendar", "coverage_requirements", "shift_assignments",
             "leave_requests", "attendance_events", "swap_requests"]
    return {name: pd.read_csv(d / f"{name}.csv", keep_default_na=False) for name in names}

def validate_dataset(data_dir: str | Path, report_dir: str | Path | None = None) -> dict:
    t = load_tables(data_dir)
    issues = []
    def issue(kind, record_id, detail):
        issues.append({"issue_type": kind, "record_id": str(record_id), "detail": detail})

    # Primary keys and foreign keys.
    pk = {"teams": "team_id", "skills": "skill_id", "employees": "employee_id",
          "shift_templates": "template_id", "holiday_calendar": "holiday_id",
          "coverage_requirements": "requirement_id", "shift_assignments": "assignment_id",
          "leave_requests": "leave_request_id", "attendance_events": "attendance_id",
          "swap_requests": "swap_request_id"}
    for table, key in pk.items():
        df = t[table]
        if df[key].duplicated().any():
            for value in df.loc[df[key].duplicated(keep=False), key].unique():
                issue("DUPLICATE_PRIMARY_KEY", value, f"{table}.{key} is not unique")
        if (df[key].astype(str).str.len() == 0).any():
            issue("EMPTY_PRIMARY_KEY", table, f"{table}.{key} contains empty IDs")

    def fk(child, col, parent, parent_col, optional=False):
        valid = set(t[parent][parent_col].astype(str))
        for _, row in t[child].iterrows():
            value = str(row[col])
            if optional and value in ("", "None", "nan"):
                continue
            if value not in valid:
                issue("FOREIGN_KEY_VIOLATION", row.get(pk.get(child, col), row.get(col)),
                      f"{child}.{col}={value} missing from {parent}.{parent_col}")
    fk("employees", "team_id", "teams", "team_id")
    fk("employee_skills", "employee_id", "employees", "employee_id")
    fk("employee_skills", "skill_id", "skills", "skill_id")
    fk("coverage_requirements", "team_id", "teams", "team_id")
    fk("coverage_requirements", "skill_id", "skills", "skill_id")
    fk("shift_assignments", "employee_id", "employees", "employee_id")
    fk("shift_assignments", "team_id", "teams", "team_id")
    fk("shift_assignments", "template_id", "shift_templates", "template_id")
    fk("leave_requests", "employee_id", "employees", "employee_id")
    fk("attendance_events", "employee_id", "employees", "employee_id")
    fk("attendance_events", "assignment_id", "shift_assignments", "assignment_id")
    fk("swap_requests", "from_assignment_id", "shift_assignments", "assignment_id")
    fk("swap_requests", "requested_by_employee_id", "employees", "employee_id")
    fk("swap_requests", "target_employee_id", "employees", "employee_id", optional=True)

    assignments = t["shift_assignments"]
    employees = t["employees"].set_index("employee_id", drop=False)
    skill_pairs = set(zip(t["employee_skills"]["employee_id"], t["employee_skills"]["skill_id"]))
    approved_leaves = t["leave_requests"][t["leave_requests"]["status"] == "APPROVED"]
    for _, a in assignments.iterrows():
        if a["employee_id"] not in employees.index:
            continue
        # Skill requirement: each assignment must satisfy any matching requirement for its team/shift.
        reqs = t["coverage_requirements"][
            (t["coverage_requirements"]["team_id"] == a["team_id"]) &
            (t["coverage_requirements"]["shift_id"] == a["shift_id"])
        ]
        for _, req in reqs.iterrows():
            if (a["employee_id"], req["skill_id"]) not in skill_pairs:
                issue("REQUIRED_SKILL_ABSENT", a["assignment_id"],
                      f"Employee lacks {req['skill_id']} required for {a['shift_id']}")
        for _, leave in approved_leaves[approved_leaves["employee_id"] == a["employee_id"]].iterrows():
            if leave["start_date"] <= a["shift_date"] <= leave["end_date"]:
                issue("APPROVED_LEAVE_OVERLAP", a["assignment_id"],
                      f"Approved leave {leave['leave_request_id']} overlaps shift date {a['shift_date']}")

    # Double-booked employee: same employee and shift start/date in multiple active rows.
    if not assignments.empty:
        dupes = assignments[assignments.duplicated(["employee_id", "shift_id"], keep=False)]
        for _, row in dupes.iterrows():
            issue("EMPLOYEE_DOUBLE_BOOKED", row["assignment_id"],
                  f"Employee {row['employee_id']} has multiple assignments for {row['shift_id']}")

    # Coverage: compare qualified active assignments to each requirement.
    coverage_rows = []
    for _, req in t["coverage_requirements"].iterrows():
        eligible = assignments[
            (assignments["shift_id"] == req["shift_id"]) &
            (assignments["team_id"] == req["team_id"]) &
            (assignments["status"] == "ASSIGNED")
        ]
        qualified = [eid for eid in eligible["employee_id"] if (eid, req["skill_id"]) in skill_pairs]
        actual = len(set(qualified))
        gap = max(0, int(req["minimum_staff"]) - actual)
        coverage_rows.append({"requirement_id": req["requirement_id"], "shift_id": req["shift_id"],
                              "team_id": req["team_id"], "skill_id": req["skill_id"],
                              "minimum_staff": int(req["minimum_staff"]), "qualified_staff": actual,
                              "coverage_gap": gap, "coverage_met": gap == 0})
        if gap:
            issue("COVERAGE_GAP", req["requirement_id"],
                  f"Required {req['minimum_staff']} qualified staff; found {actual}; gap={gap}")

    # Overtime: scheduled hours by employee/week. This is a conservative scheduled-hours proxy.
    overtime_rows = []
    if not assignments.empty:
        a = assignments.copy()
        a["shift_date_parsed"] = pd.to_datetime(a["shift_date"], errors="coerce")
        a["week_start"] = (a["shift_date_parsed"] - pd.to_timedelta(a["shift_date_parsed"].dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
        weekly = a.groupby(["employee_id", "week_start"], dropna=False)["planned_hours"].sum().reset_index()
        caps = t["employees"].set_index("employee_id")
        for _, row in weekly.iterrows():
            if row["employee_id"] not in caps.index:
                continue
            cap = int(caps.loc[row["employee_id"], "weekly_hour_cap"]) + int(caps.loc[row["employee_id"], "overtime_cap_hours"])
            overtime = max(0, int(row["planned_hours"]) - int(caps.loc[row["employee_id"], "weekly_hour_cap"]))
            exceeded = int(row["planned_hours"]) > cap
            overtime_rows.append({"employee_id": row["employee_id"], "week_start": row["week_start"],
                                  "scheduled_hours": int(row["planned_hours"]),
                                  "weekly_hour_cap": int(caps.loc[row["employee_id"], "weekly_hour_cap"]),
                                  "overtime_hours": overtime, "maximum_with_overtime": cap,
                                  "overtime_cap_exceeded": exceeded})
            if exceeded:
                issue("OVERTIME_CAP_EXCEEDED", row["employee_id"],
                      f"{row['week_start']}: {row['planned_hours']}h exceeds cap {cap}h")

    # Swap application must have approved status and manager approval.
    for _, s in t["swap_requests"].iterrows():
        applied = str(s["applied"]).lower() in ("true", "1", "yes")
        if applied and (s["status"] != "APPROVED" or not s["manager_approved_by"]):
            issue("SWAP_APPLIED_WITHOUT_APPROVAL", s["swap_request_id"],
                  "Applied swap lacks approved status or manager approver")

    # Attendance must point to a real assignment belonging to the same employee.
    assignment_owner = dict(zip(assignments["assignment_id"], assignments["employee_id"]))
    for _, att in t["attendance_events"].iterrows():
        if att["assignment_id"] in assignment_owner and assignment_owner[att["assignment_id"]] != att["employee_id"]:
            issue("ATTENDANCE_EMPLOYEE_MISMATCH", att["attendance_id"],
                  "Attendance employee does not match assignment employee")

    issue_df = pd.DataFrame(issues, columns=["issue_type", "record_id", "detail"])
    coverage_df = pd.DataFrame(coverage_rows)
    overtime_df = pd.DataFrame(overtime_rows)
    summary = {
        "employees": int(len(t["employees"])), "teams": int(len(t["teams"])),
        "shift_assignments": int(len(assignments)), "leave_requests": int(len(t["leave_requests"])),
        "attendance_events": int(len(t["attendance_events"])),
        "coverage_requirements": int(len(t["coverage_requirements"])),
        "coverage_met_rate": round(float(coverage_df["coverage_met"].mean()), 4) if len(coverage_df) else 1.0,
        "coverage_gap_requirements": int((coverage_df["coverage_gap"] > 0).sum()) if len(coverage_df) else 0,
        "issues_total": int(len(issue_df)),
        "issue_counts": issue_df["issue_type"].value_counts().to_dict() if len(issue_df) else {},
        "ground_truth_labels": int(len(pd.read_csv(Path(data_dir) / "ground_truth.csv"))) if (Path(data_dir) / "ground_truth.csv").exists() else 0,
        "note": "Synthetic demo. Weekly scheduled-hours calculation is a proxy; production scheduling should enforce rest periods and rolling windows."
    }
    if report_dir:
        rd = Path(report_dir)
        rd.mkdir(parents=True, exist_ok=True)
        issue_df.to_csv(rd / "validation_issues.csv", index=False)
        coverage_df.to_csv(rd / "coverage_report.csv", index=False)
        overtime_df.to_csv(rd / "overtime_report.csv", index=False)
        (rd / "validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
