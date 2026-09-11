from __future__ import annotations
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from incubrix.qc.engine import QCEngine


def run_qc_audit(console: Console) -> dict:
    """
    Run automated fault injection audit to calculate QC precision and recall.
    Evaluates:
      - Empty outputs
      - Repetitive loops
      - Wrong language outputs
      - Missing / corrupted entities
      - Clean outputs (control)
    """
    fault_file = Path("d:/incubrix/data/fault_injection_suite.json")
    with open(fault_file, "r", encoding="utf-8") as f:
        injections = json.load(f)["injections"]

    engine = QCEngine()

    tp = 0  # Injected fault correctly flagged
    tn = 0  # Clean output correctly approved
    fp = 0  # Clean output incorrectly flagged
    fn = 0  # Injected fault missed (wrongly approved)

    table = Table(title="IncuBrix Automated QC Fault Injection Audit", show_header=True)
    table.add_column("Test ID", style="cyan", width=18)
    table.add_column("Type", style="yellow", width=16)
    table.add_column("Expected", style="magenta", width=10)
    table.add_column("QC Result", style="bold", width=12)
    table.add_column("Confidence", style="blue", width=12)
    table.add_column("Flags Detected", style="green")

    results = []

    for item in injections:
        res = engine.evaluate(
            segment_id=item["id"],
            source_text=item["source_text"],
            translated_text=item["translated_text"],
            source_lang=item["source_lang"],
            target_lang=item["target_lang"],
            production_model_family="NLLB",
            expected_entities=item.get("expected_entities", []),
        )

        should_pass = item["should_pass"]
        actual_pass = res.passed

        if not should_pass and not actual_pass:
            tp += 1
            verdict = "[green]CORRECT (FLAGGED)[/green]"
        elif should_pass and actual_pass:
            tn += 1
            verdict = "[green]CORRECT (APPROVED)[/green]"
        elif should_pass and not actual_pass:
            fp += 1
            verdict = "[red]FALSE POSITIVE[/red]"
        else:
            fn += 1
            verdict = "[red]FALSE NEGATIVE (MISSED)[/red]"

        table.add_row(
            item["id"],
            item.get("expected_fault") or "CLEAN",
            "PASS" if should_pass else "FLAG",
            verdict,
            f"{res.overall_confidence * 100:.1f}%",
            ", ".join(res.flags) or "None",
        )

        results.append({
            "id": item["id"],
            "expected_fault": item.get("expected_fault"),
            "should_pass": should_pass,
            "actual_pass": actual_pass,
            "confidence": res.overall_confidence,
            "flags": res.flags,
        })

    console.print(table)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / len(injections) if len(injections) > 0 else 0.0

    metrics = {
        "total_evaluated": len(injections),
        "true_positives": tp,
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "accuracy": round(accuracy, 4),
    }

    metrics_table = Table(title="Independent QC Performance Metrics", show_header=True)
    metrics_table.add_column("Metric", style="cyan", width=25)
    metrics_table.add_column("Score", style="bold green", width=15)

    metrics_table.add_row("Fault Detection Precision", f"{precision * 100:.2f}%")
    metrics_table.add_row("Fault Detection Recall", f"{recall * 100:.2f}%")
    metrics_table.add_row("F1-Score", f"{f1 * 100:.2f}%")
    metrics_table.add_row("Overall Accuracy", f"{accuracy * 100:.2f}%")
    metrics_table.add_row("False Positive Rate", f"{(fp / max(1, fp + tn)) * 100:.2f}%")

    console.print(metrics_table)

    # Export audit evidence
    report_file = Path("d:/incubrix/data/qc_audit_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({"metrics": metrics, "details": results}, f, indent=2)

    console.print(Panel(
        f"[bold green]Audit Report successfully saved to: {report_file}[/bold green]",
        expand=False
    ))
    return metrics
