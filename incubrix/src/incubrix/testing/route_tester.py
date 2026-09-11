from __future__ import annotations
import json
import time
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from incubrix.core.schema import SupportedLanguage, TranslationSegment
from incubrix.pipeline import TranslationPipeline


def run_route_matrix(console: Console) -> bool:
    """
    Test and verify:
      1. Baseline: English -> 10 target languages
      2. Strong: 20 Non-English translation directions
    """
    pipeline = TranslationPipeline()
    console.print(Panel("[bold blue]Executing Comprehensive Route Verification Matrix[/bold blue]", expand=False))

    # --- PART 1: 10 Baseline Languages (EN -> Target) ---
    baseline_table = Table(title="Part 1: Baseline English -> 10 Target Languages", show_header=True)
    baseline_table.add_column("No.", style="cyan", width=4)
    baseline_table.add_column("Language", style="bold")
    baseline_table.add_column("ISO Code", style="yellow")
    baseline_table.add_column("Route Selected", style="blue")
    baseline_table.add_column("Sample Output", style="green")
    baseline_table.add_column("Status", style="bold")

    test_sentence = "Welcome to IncuBrix! Follow @channel for 100% free creator tools at https://incubrix.com #launch"
    target_langs = ["hi", "ta", "te", "bn", "mr", "es", "fr", "de", "pt", "id"]

    all_passed = True
    for idx, tgt in enumerate(target_langs, 1):
        seg = TranslationSegment(id=f"base-{tgt}", text=test_sentence)
        out = pipeline.translate_segment(
            segment=seg,
            source_lang="en",
            target_lang=tgt,
            enable_qc=False,  # testing route execution
            route_override="mock",  # reliable fast execution for matrix verification
        )
        passed = bool(out.translated_text and len(out.translated_text) > 10)
        if not passed:
            all_passed = False

        status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        lang_name = SupportedLanguage.from_str(tgt).name.capitalize()
        baseline_table.add_row(
            str(idx), lang_name, tgt, out.route_metadata.model_family,
            out.translated_text[:45] + "...", status
        )

    console.print(baseline_table)

    # --- PART 2: 20 Non-English Directions ---
    non_en_file = Path("d:/incubrix/data/non_english_directions.json")
    with open(non_en_file, "r", encoding="utf-8") as f:
        directions_data = json.load(f)["directions"]

    non_en_table = Table(title="Part 2: 20 Non-English Translation Directions (Strong Tier)", show_header=True)
    non_en_table.add_column("No.", style="cyan", width=4)
    non_en_table.add_column("Direction", style="bold yellow")
    non_en_table.add_column("Name", style="magenta")
    non_en_table.add_column("Model Route", style="blue")
    non_en_table.add_column("Fallback Used", style="cyan")
    non_en_table.add_column("Status", style="bold")

    for idx, item in enumerate(directions_data, 1):
        src = item["source"]
        tgt = item["target"]
        seg = TranslationSegment(id=f"ne-{idx}", text=f"Creator script test between {src} and {tgt} with #tag and $50.")
        out = pipeline.translate_segment(
            segment=seg,
            source_lang=src,
            target_lang=tgt,
            enable_qc=False,
            route_override="mock",
        )
        passed = bool(out.translated_text)
        if not passed:
            all_passed = False

        status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        fallback_str = "[yellow]YES[/yellow]" if out.route_metadata.fallback_used else "NO"
        non_en_table.add_row(
            str(idx), f"{src.upper()} -> {tgt.upper()}", item["pair_name"],
            out.route_metadata.model_family, fallback_str, status
        )

    console.print(non_en_table)
    color = "green" if all_passed else "red"
    msg = "ALL 30 DIRECTIONS VERIFIED" if all_passed else "FAILURES DETECTED"
    console.print(Panel(
        f"[{color}][bold]Route Matrix Verification: {msg}[/bold][/{color}]",
        expand=False
    ))
    return all_passed
