import argparse
import json
import sys
from pathlib import Path

from ..config import load_settings
from ..core.llm import build_llm
from .runner import DEFAULT_CONFIGS, run_evaluation

COLUMNS = (
    ("attack_success_rate", "Attack success"),
    ("false_negative_rate", "Missed (no intervention)"),
    ("false_positive_rate", "False positives"),
    ("task_completion_rate", "Task completion"),
)


def pct(value):
    return f"{value * 100:.1f}%"


def render_markdown(report):
    dataset = report["dataset"]
    lines = [
        f"Agent: `{report['llm']}` | attacks: {dataset['attacks']} | benign tasks: {dataset['benign']}",
        "",
        "| Configuration | " + " | ".join(label for _, label in COLUMNS) + " |",
        "|---|" + "---|" * len(COLUMNS),
    ]
    for name, data in report["configs"].items():
        metrics = data["metrics"]
        lines.append(f"| {name} | " + " | ".join(pct(metrics[key]) for key, _ in COLUMNS) + " |")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m app.evals.cli")
    parser.add_argument("--configs", nargs="+", default=list(DEFAULT_CONFIGS))
    parser.add_argument("--provider", choices=("mock", "anthropic"), default=None)
    parser.add_argument("--json", dest="json_path")
    parser.add_argument("--markdown", dest="markdown_path")
    parser.add_argument("--max-asr", type=float, default=None)
    parser.add_argument("--min-tcr", type=float, default=None)
    args = parser.parse_args(argv)

    settings = load_settings()
    if args.provider:
        settings = type(settings)(**{**settings.__dict__, "llm_provider": args.provider})
    llm = build_llm(settings)
    report = run_evaluation(llm, settings, configs=args.configs)

    markdown = render_markdown(report)
    print(markdown)
    if args.json_path:
        Path(args.json_path).write_text(json.dumps(report, indent=2))
    if args.markdown_path:
        Path(args.markdown_path).write_text(markdown + "\n")

    failed = False
    gated = report["configs"].get("full")
    if gated:
        metrics = gated["metrics"]
        if args.max_asr is not None and metrics["attack_success_rate"] > args.max_asr:
            print(f"FAIL: attack success {pct(metrics['attack_success_rate'])} exceeds {pct(args.max_asr)}", file=sys.stderr)
            failed = True
        if args.min_tcr is not None and metrics["task_completion_rate"] < args.min_tcr:
            print(f"FAIL: task completion {pct(metrics['task_completion_rate'])} below {pct(args.min_tcr)}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
