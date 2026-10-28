import hashlib
from pathlib import Path
import pandas as pd
from workforce_scheduler.generator import generate_dataset
from workforce_scheduler.validator import validate_dataset

def test_seed_reproducibility(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    generate_dataset(a, seed=42, employees_n=40, teams_n=4, days=3, leave_n=20)
    generate_dataset(b, seed=42, employees_n=40, teams_n=4, days=3, leave_n=20)
    for name in sorted(p.name for p in a.glob("*.csv")):
        assert hashlib.sha256((a/name).read_bytes()).hexdigest() == hashlib.sha256((b/name).read_bytes()).hexdigest()

def test_required_tables_and_ids(tmp_path):
    out = tmp_path / "data"
    generate_dataset(out, seed=7, employees_n=40, teams_n=4, days=3, leave_n=20)
    employees = pd.read_csv(out / "employees.csv")
    leaves = pd.read_csv(out / "leave_requests.csv")
    assert len(employees) == 40
    assert employees.employee_id.is_unique
    assert len(leaves) == 21  # 20 baseline + one injected approved-leave case
    assert leaves.leave_request_id.is_unique

def test_validator_emits_exception_paths(tmp_path):
    out, reports = tmp_path / "data", tmp_path / "reports"
    generate_dataset(out, seed=8, employees_n=80, teams_n=4, days=5, leave_n=30)
    summary = validate_dataset(out, reports)
    assert summary["issues_total"] > 0
    assert (reports / "coverage_report.csv").exists()
    assert (reports / "validation_issues.csv").exists()
