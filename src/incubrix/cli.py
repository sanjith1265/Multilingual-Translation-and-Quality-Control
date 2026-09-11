from __future__ import annotations
import sys
import json
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from incubrix.core.schema import (
    TranslationSegment,
    BatchTranslationRequest,
    SupportedLanguage,
)
from incubrix.pipeline import TranslationPipeline
from incubrix.qc.review_queue import ReviewQueueManager

console = Console(safe_box=True)


@click.group()
def main():
    """IncuBrix Translation & Independent QC CLI (Track 04)"""
    pass


@main.command(name="translate")
@click.argument("text")
@click.option("--from", "-s", "source_lang", default="en", help="Source language (e.g. en, hi, es)")
@click.option("--to", "-t", "target_lang", required=True, help="Target language (e.g. hi, ta, es)")
@click.option("--route", "-r", default=None, help="Route override (nllb, marian, mock)")
@click.option("--dnt", multiple=True, help="Do-not-translate term (can specify multiple)")
@click.option("--glossary", "-g", default=None, help="JSON string of glossary mappings")
@click.option("--no-qc", is_flag=True, help="Disable independent QC checks")
def translate_cmd(text, source_lang, target_lang, route, dnt, glossary, no_qc):
    """Translate a single sentence or creator script segment."""
    pipeline = TranslationPipeline()
    gloss_dict = json.loads(glossary) if glossary else {}

    segment = TranslationSegment(id="cli-01", text=text)
    with console.status("[bold green]Executing translation and independent QC..."):
        out = pipeline.translate_segment(
            segment=segment,
            source_lang=source_lang,
            target_lang=target_lang,
            glossary=gloss_dict,
            do_not_translate=list(dnt),
            route_override=route,
            enable_qc=not no_qc,
        )

    # Render summary table
    table = Table(title=f"Translation: {source_lang.upper()} -> {target_lang.upper()}", show_header=True)
    table.add_column("Property", style="cyan", width=24)
    table.add_column("Value", style="magenta")

    table.add_row("Input Text", out.source_text)
    table.add_row("Translated Text", f"[bold green]{out.translated_text}[/bold green]")
    table.add_row("Route Used", f"{out.route_metadata.model_family} ({out.route_metadata.model_name})")
    table.add_row("Execution Device", out.route_metadata.device.upper())
    table.add_row("Latency", f"{out.runtime_ms} ms")
    status_style = "green" if out.review_status == "APPROVED" else "red"
    table.add_row("Review Status", f"[{status_style}][bold]{out.review_status}[/bold][/{status_style}]")
    table.add_row("Preserved Entities", ", ".join(out.preserved_entities) or "None")

    if out.qc_result:
        table.add_row("QC Overall Confidence", f"{out.qc_result.overall_confidence * 100:.1f}%")
        table.add_row("QC Pass Status", "[green]PASSED[/green]" if out.qc_result.passed else "[red]FLAGGED[/red]")
        table.add_row("QC Flags", ", ".join(out.qc_result.flags) or "None")

    console.print(table)


@main.command(name="batch")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--to", "-t", "target_lang", required=True, help="Target language")
@click.option("--from", "-s", "source_lang", default="en", help="Source language")
@click.option("--output", "-o", default=None, help="Output JSON path")
@click.option("--route", "-r", default=None, help="Route override (nllb, marian, mock)")
def batch_cmd(input_file, target_lang, source_lang, output, route):
    """Translate a batch JSON file with resume support."""
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_segments = data.get("segments", data.get("samples", data if isinstance(data, list) else []))
    segments = [
        TranslationSegment(
            id=str(s.get("id", idx)),
            text=s.get("text", s.get("source_text", str(s))),
        )
        for idx, s in enumerate(raw_segments)
    ]

    pipeline = TranslationPipeline()
    batch_req = BatchTranslationRequest(
        batch_id=f"batch-{Path(input_file).stem}",
        segments=segments,
        source_lang=source_lang,
        target_lang=target_lang,
        enable_qc=True,
        enable_cache=True,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Translating {len(segments)} segments to {target_lang}...", total=len(segments))
        resp = pipeline.translate_batch(batch_req)
        progress.update(task, completed=len(segments))

    out_path = output or f"d:/incubrix/data/batch_output_{target_lang}.json"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resp.model_dump(), f, indent=2, ensure_ascii=False)

    console.print(Panel(
        f"[bold green]Batch Completed![/bold green]\n"
        f"Total: {resp.total_segments} | Processed: {resp.completed_segments} | Failed: {resp.failed_segments}\n"
        f"Cache Hits: {resp.cached_hits} | Flagged for Review: {resp.review_queue_count}\n"
        f"Total Runtime: {resp.total_runtime_ms:.1f} ms\n"
        f"Output written to: [cyan]{out_path}[/cyan]",
        title="Batch Summary"
    ))


@main.command(name="test-routes")
def test_routes_cmd():
    """Verify all 10 baseline languages and 20 non-English directions."""
    from incubrix.testing.route_tester import run_route_matrix
    run_route_matrix(console)


@main.command(name="audit-qc")
def audit_qc_cmd():
    """Run fault-injection test suite and report QC precision/recall metrics."""
    from incubrix.testing.qc_auditor import run_qc_audit
    run_qc_audit(console)


@main.command(name="benchmark")
def benchmark_cmd():
    """Execute automated CPU performance & memory benchmark."""
    from incubrix.benchmarks.runner import execute_benchmark
    execute_benchmark(console)


@main.command(name="serve")
@click.option("--host", default="127.0.0.1", help="Host address")
@click.option("--port", default=8000, help="Port number")
def serve_cmd(host, port):
    """Launch local FastAPI microservice."""
    import uvicorn
    console.print(f"[bold green]Launching IncuBrix Translation Microservice on http://{host}:{port}...[/bold green]")
    uvicorn.run("incubrix.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
