from __future__ import annotations
import hashlib
import json
from pathlib import Path
import random
from datetime import date, datetime, time, timedelta
import pandas as pd

SEED_DEFAULT = 20261022
SKILLS = ["CUSTOMER_SUPPORT", "OPERATIONS", "IT_SUPPORT", "SAFETY", "INVENTORY", "SUPERVISION"]
SHIFT_CODES = ["A", "B", "C"]
SHIFT_HOURS = {"A": (6, 14), "B": (14, 22), "C": (22, 6)}
TABLES = [
    "teams", "skills", "employees", "employee_skills", "shift_templates",
    "holiday_calendar", "coverage_requirements", "shift_assignments",
    "leave_requests", "attendance_events", "swap_requests"
]

def _id(prefix: str, n: int, width: int = 6) -> str:
    return f"{prefix}-{n:0{width}d}"

def generate_dataset(out_dir: str | Path, seed: int = SEED_DEFAULT,
                     employees_n: int = 2000, teams_n: int = 100,
                     days: int = 90, leave_n: int = 5000,
                     inject_anomalies: bool = True) -> dict:
    """Generate a fully synthetic dataset. Same parameters + seed => same CSV bytes."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    start = date(2026, 1, 1)

    teams = [{"team_id": _id("TEAM", i), "team_name": f"Team {i:03d}",
              "manager_employee_id": None, "effective_from": start.isoformat(),
              "effective_to": None, "status": "ACTIVE"} for i in range(1, teams_n + 1)]
    skills = [{"skill_id": f"SKL-{s}", "skill_name": s.replace("_", " ").title(),
               "skill_code": s, "status": "ACTIVE"} for s in SKILLS]

    employees = []
    employee_skills = []
    for i in range(1, employees_n + 1):
        team_no = ((i - 1) % teams_n) + 1
        hire_date = start - timedelta(days=rng.randint(0, 900))
        employees.append({
            "employee_id": _id("EMP", i), "team_id": _id("TEAM", team_no),
            "display_name": f"Employee {i:04d}", "employment_type": rng.choices(
                ["FULL_TIME", "PART_TIME", "CONTRACT"], weights=[78, 14, 8])[0],
            "weekly_hour_cap": rng.choice([32, 36, 40]), "overtime_cap_hours": 8,
            "hire_date": hire_date.isoformat(), "effective_from": hire_date.isoformat(),
            "effective_to": None, "status": "ACTIVE"
        })
        # Every employee gets 1-3 skills; the team's core skill is included.
        chosen = set(rng.sample(SKILLS, rng.randint(1, 3)))
        chosen.add(SKILLS[(team_no - 1) % len(SKILLS)])
        for s in sorted(chosen):
            employee_skills.append({"employee_id": _id("EMP", i), "skill_id": f"SKL-{s}",
                                    "proficiency": rng.choice(["BASIC", "INTERMEDIATE", "ADVANCED"]),
                                    "valid_from": hire_date.isoformat(), "valid_to": None})

    templates = []
    for code, (sh, eh) in SHIFT_HOURS.items():
        templates.append({
            "template_id": f"TPL-{code}", "shift_code": code,
            "start_time": f"{sh:02d}:00", "end_time": f"{eh:02d}:00",
            "duration_hours": 8, "crosses_midnight": eh <= sh,
            "status": "ACTIVE"
        })

    holidays = []
    # Synthetic public-holiday calendar: explicitly marked illustrative, not authoritative.
    for d, name in [(date(2026, 1, 26), "Republic Day"),
                    (date(2026, 3, 4), "Regional Holiday"),
                    (date(2026, 8, 15), "Independence Day")]:
        if start <= d < start + timedelta(days=days):
            holidays.append({"holiday_id": f"HOL-{d.isoformat()}", "holiday_date": d.isoformat(),
                             "holiday_name": name, "region": "IN-DEMO", "is_public": True})

    coverage = []
    assignments = []
    attendance = []
    # Every team/shift/day requires two employees with one target skill.
    emp_by_team = {}
    emp_skill_map = {}
    for e in employees:
        emp_by_team.setdefault(e["team_id"], []).append(e)
    for es in employee_skills:
        emp_skill_map.setdefault(es["employee_id"], set()).add(es["skill_id"])

    assignment_counter = 0
    for day_idx in range(days):
        d = start + timedelta(days=day_idx)
        for team_idx in range(1, teams_n + 1):
            team_id = _id("TEAM", team_idx)
            target_skill = f"SKL-{SKILLS[(team_idx - 1) % len(SKILLS)]}"
            for code in SHIFT_CODES:
                shift_id = f"SHIFT-{d.isoformat()}-{code}"
                req_id = f"REQ-{d.isoformat()}-{team_idx:03d}-{code}"
                coverage.append({
                    "requirement_id": req_id, "shift_id": shift_id, "team_id": team_id,
                    "skill_id": target_skill, "minimum_staff": 2,
                    "effective_from": d.isoformat(), "effective_to": d.isoformat()
                })
                candidates = emp_by_team[team_id][:]
                # Prefer employees with the required skill; fallback is intentionally not used
                # in valid baseline assignments, so coverage gaps can be measured honestly.
                qualified = [e for e in candidates if target_skill in emp_skill_map[e["employee_id"]]]
                rng.shuffle(qualified)
                chosen = qualified[:2]
                for e in chosen:
                    assignment_counter += 1
                    assignments.append({
                        "assignment_id": _id("ASN", assignment_counter),
                        "shift_id": shift_id, "employee_id": e["employee_id"],
                        "team_id": team_id, "template_id": f"TPL-{code}",
                        "shift_date": d.isoformat(), "start_datetime": f"{d.isoformat()}T{SHIFT_HOURS[code][0]:02d}:00:00",
                        "end_datetime": f"{(d + timedelta(days=1 if code == 'C' else 0)).isoformat()}T{SHIFT_HOURS[code][1]:02d}:00:00",
                        "planned_hours": 8, "status": "ASSIGNED", "source": "GENERATOR"
                    })
                    # Keep attendance event rows linked to assignments.
                    status = rng.choices(["PRESENT", "LATE", "ABSENT"], [94, 4, 2])[0]
                    attendance.append({
                        "attendance_id": f"ATT-{e['employee_id']}-{d.isoformat()}T{SHIFT_HOURS[code][0]:02d}0000",
                        "employee_id": e["employee_id"], "assignment_id": _id("ASN", assignment_counter),
                        "event_timestamp": f"{d.isoformat()}T{SHIFT_HOURS[code][0]:02d}:00:00",
                        "event_type": status, "minutes_late": 10 if status == "LATE" else 0,
                        "source": "SYNTHETIC_CLOCK"
                    })

    leave_requests = []
    for i in range(1, leave_n + 1):
        emp = employees[rng.randrange(len(employees))]
        req_date = start + timedelta(days=rng.randrange(days))
        length = rng.choices([1, 2, 3, 5], [58, 24, 13, 5])[0]
        leave_requests.append({
            "leave_request_id": _id("LVE-2026", i), "employee_id": emp["employee_id"],
            "submitted_at": (datetime.combine(req_date, time(9)) - timedelta(days=rng.randint(1, 20))).isoformat(),
            "start_date": req_date.isoformat(), "end_date": (req_date + timedelta(days=length - 1)).isoformat(),
            "leave_type": rng.choice(["ANNUAL", "SICK", "PERSONAL"]),
            "status": rng.choices(["APPROVED", "PENDING", "REJECTED"], [58, 15, 27])[0],
            "decision_by": f"EMP-{rng.randint(1, employees_n):06d}" if rng.random() > .1 else None,
            "decision_at": None, "hours_requested": length * 8
        })
    # Set decision timestamps only for requests that were decided.
    for lr in leave_requests:
        if lr["status"] in ("APPROVED", "REJECTED"):
            lr["decision_at"] = (datetime.fromisoformat(lr["submitted_at"]) + timedelta(hours=rng.randint(1, 120))).isoformat()

    swaps = []
    for i in range(1, max(100, days * 2) + 1):
        if not assignments:
            break
        a = assignments[rng.randrange(len(assignments))]
        swaps.append({
            "swap_request_id": _id("SWP-2026", i), "from_assignment_id": a["assignment_id"],
            "requested_by_employee_id": a["employee_id"], "target_employee_id": None,
            "requested_at": f"{a['shift_date']}T09:00:00",
            "status": rng.choices(["APPROVED", "PENDING", "REJECTED"], [55, 20, 25])[0],
            "manager_approved_by": a["employee_id"] if rng.random() > .12 else None,
            "approved_at": None, "applied": False
        })
        if swaps[-1]["status"] == "APPROVED" and swaps[-1]["manager_approved_by"]:
            swaps[-1]["approved_at"] = f"{a['shift_date']}T10:00:00"

    # Explicit, labelled negative scenarios. Ground truth is never merged into input files.
    ground_truth = []
    if inject_anomalies and assignments:
        # Double booking: duplicate employee onto a different assignment at same shift start.
        a0 = assignments[0]
        dup = dict(a0)
        dup["assignment_id"] = _id("ASN", assignment_counter + 1)
        dup["shift_id"] = a0["shift_id"]
        dup["source"] = "INJECTED_ANOMALY"
        assignments.append(dup)
        ground_truth.append({"record_type": "shift_assignment", "record_id": dup["assignment_id"],
                             "issue_type": "EMPLOYEE_DOUBLE_BOOKED", "expected_detection": True,
                             "rule": "Employee cannot hold overlapping active assignments."})
        # Leave overlap with an assigned shift.
        a1 = assignments[min(2, len(assignments)-1)]
        leave_requests.append({
            "leave_request_id": _id("LVE-2026", leave_n + 1), "employee_id": a1["employee_id"],
            "submitted_at": f"{a1['shift_date']}T09:00:00", "start_date": a1["shift_date"],
            "end_date": a1["shift_date"], "leave_type": "SICK", "status": "APPROVED",
            "decision_by": "EMP-000001", "decision_at": f"{a1['shift_date']}T10:00:00", "hours_requested": 8
        })
        ground_truth.append({"record_type": "leave_request", "record_id": _id("LVE-2026", leave_n + 1),
                             "issue_type": "APPROVED_LEAVE_OVERLAP", "expected_detection": True,
                             "rule": "Approved leave cannot overlap an assigned shift."})
        # Missing skill: clone an assignment but assign it to an employee lacking the target skill.
        req = coverage[0]
        req_skill = req["skill_id"]
        unqualified = next((e for e in employees if req_skill not in emp_skill_map[e["employee_id"]]), None)
        if unqualified:
            bad = dict(assignments[1])
            bad["assignment_id"] = _id("ASN", assignment_counter + 2)
            bad["employee_id"] = unqualified["employee_id"]
            bad["team_id"] = req["team_id"]
            bad["shift_id"] = req["shift_id"]
            bad["shift_date"] = req["effective_from"]
            bad["source"] = "INJECTED_ANOMALY"
            assignments.append(bad)
            ground_truth.append({"record_type": "shift_assignment", "record_id": bad["assignment_id"],
                                 "issue_type": "REQUIRED_SKILL_ABSENT", "expected_detection": True,
                                 "rule": "Assignment employee must hold the required skill for the shift/team."})
        # Unapproved swap marked applied.
        sw = swaps[0]
        sw["status"] = "PENDING"
        sw["applied"] = True
        sw["manager_approved_by"] = None
        ground_truth.append({"record_type": "swap_request", "record_id": sw["swap_request_id"],
                             "issue_type": "SWAP_APPLIED_WITHOUT_APPROVAL", "expected_detection": True,
                             "rule": "A swap may be applied only after manager approval."})
        # Overtime cap: explicit overtime summary is derived in validator; this record flags a synthetic case.
        # Add multiple same-day assignment rows for one employee to trigger overtime / overlap checks.
        overtime_emp = assignments[0]["employee_id"]
        for j in range(6):
            src = assignments[j]
            bad = dict(src)
            bad["assignment_id"] = _id("ASN", assignment_counter + 3 + j)
            bad["employee_id"] = overtime_emp
            bad["shift_id"] = f"SHIFT-{src['shift_date']}-{'A' if src['template_id'] != 'TPL-A' else 'B'}"
            bad["source"] = "INJECTED_ANOMALY"
            assignments.append(bad)
        ground_truth.append({"record_type": "employee", "record_id": overtime_emp,
                             "issue_type": "OVERTIME_CAP_EXCEEDED", "expected_detection": True,
                             "rule": "Scheduled hours beyond weekly hour cap plus overtime cap are flagged."})

    frames = {
        "teams": pd.DataFrame(teams), "skills": pd.DataFrame(skills),
        "employees": pd.DataFrame(employees), "employee_skills": pd.DataFrame(employee_skills),
        "shift_templates": pd.DataFrame(templates), "holiday_calendar": pd.DataFrame(holidays, columns=["holiday_id", "holiday_date", "holiday_name", "region", "is_public"]),
        "coverage_requirements": pd.DataFrame(coverage), "shift_assignments": pd.DataFrame(assignments),
        "leave_requests": pd.DataFrame(leave_requests), "attendance_events": pd.DataFrame(attendance),
        "swap_requests": pd.DataFrame(swaps), "ground_truth": pd.DataFrame(ground_truth)
    }
    manifest = {"seed": seed, "start_date": start.isoformat(), "days": days,
                "requested_employees": employees_n, "teams": teams_n, "requested_leave_requests": leave_n,
                "synthetic_only": True, "anomalies_injected": inject_anomalies,
                "tables": {}}
    for name, df in frames.items():
        path = out / f"{name}.csv"
        df.to_csv(path, index=False, lineterminator="\n")
        manifest["tables"][name] = {"rows": int(len(df)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
