import argparse, json
from pathlib import Path
from .generator import generate_dataset, SEED_DEFAULT
from .validator import validate_dataset

def main():
    parser = argparse.ArgumentParser(description="Generate and validate synthetic workforce schedules.")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="Generate deterministic CSV files")
    gen.add_argument("--out", default="data/generated")
    gen.add_argument("--seed", type=int, default=SEED_DEFAULT)
    gen.add_argument("--employees", type=int, default=2000)
    gen.add_argument("--teams", type=int, default=100)
    gen.add_argument("--days", type=int, default=90)
    gen.add_argument("--leaves", type=int, default=5000)
    gen.add_argument("--no-anomalies", action="store_true")
    val = sub.add_parser("validate", help="Validate dataset and write reports")
    val.add_argument("--data", default="data/generated")
    val.add_argument("--reports", default="reports")
    args = parser.parse_args()
    if args.command == "generate":
        result = generate_dataset(args.out, args.seed, args.employees, args.teams, args.days,
                                  args.leaves, not args.no_anomalies)
        print(json.dumps(result, indent=2))
    else:
        result = validate_dataset(args.data, args.reports)
        print(json.dumps(result, indent=2))
        print(f"Reports written to {Path(args.reports).resolve()}")

if __name__ == "__main__":
    main()
