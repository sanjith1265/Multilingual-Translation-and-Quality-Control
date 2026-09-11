from __future__ import annotations
import os
import time
import json
import psutil
import platform
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from incubrix.core.schema import TranslationSegment
from incubrix.pipeline import TranslationPipeline


def execute_benchmark(console: Console, repetitions: int = 5) -> dict:
    """
    Execute automated CPU performance, memory, and latency benchmark.
    """
    console.print(Panel("[bold cyan]IncuBrix CPU Benchmark Suite (SASTRA 2027 Track 04)[/bold cyan]", expand=False))

    proc = psutil.Process(os.getpid())
    system_info = {
        "os": platform.system() + " " + platform.release(),
        "processor": platform.processor(),
        "cpu_cores_physical": psutil.cpu_count(logical=False),
        "cpu_cores_logical": psutil.cpu_count(logical=True),
        "total_ram_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "python_version": platform.python_version(),
    }

    pipeline = TranslationPipeline()

    bench_sentences = [
        ("Short caption", "Welcome to IncuBrix! Follow @channel for free creator tips #growth"),
        ("Medium script", "In this video, we review 5 essential tools that every digital creator needs in 2026. Make sure to visit https://incubrix.com/tools before October 15."),
        ("Entity-rich", "We crossed 1,500,000 subscribers and raised $25,000 for charity in 48 hrs with a 99.2% satisfaction rate!"),
    ]

    target_languages = ["hi", "es", "ta", "de"]

    results = []
    latencies = []
    initial_rss = proc.memory_info().rss / (1024 * 1024)

    console.print(f"[yellow]Warming up engine and running {repetitions} repetitions across language pairs...[/yellow]")

    for desc, text in bench_sentences:
        for tgt in target_languages:
            pair_latencies = []
            char_count = len(text)

            for rep in range(repetitions):
                t0 = time.perf_counter()
                seg = TranslationSegment(id=f"bench-{tgt}-{rep}", text=text)
                out = pipeline.translate_segment(
                    segment=seg,
                    source_lang="en",
                    target_lang=tgt,
                    enable_qc=True,
                    route_override="mock",
                    enable_cache=False,  # Measure real compute, disable cache lookup
                )
                elapsed_ms = (time.perf_counter() - t0) * 1000
                pair_latencies.append(elapsed_ms)
                latencies.append(elapsed_ms)

            avg_lat = sum(pair_latencies) / len(pair_latencies)
            chars_per_sec = (char_count / (avg_lat / 1000)) if avg_lat > 0 else 0

            results.append({
                "category": desc,
                "target_lang": tgt,
                "char_length": char_count,
                "avg_latency_ms": round(avg_lat, 2),
                "chars_per_sec": round(chars_per_sec, 2),
            })

    peak_rss = proc.memory_info().rss / (1024 * 1024)
    ram_delta = peak_rss - initial_rss

    # Summary table
    table = Table(title="Benchmark Latency & Throughput Results", show_header=True)
    table.add_column("Category", style="cyan")
    table.add_column("Target Lang", style="yellow")
    table.add_column("Avg Latency (ms)", style="bold green")
    table.add_column("Throughput (chars/s)", style="magenta")

    for r in results:
        table.add_row(r["category"], r["target_lang"].upper(), f"{r['avg_latency_ms']} ms", f"{r['chars_per_sec']}")

    console.print(table)

    summary_metrics = {
        "system_info": system_info,
        "repetitions_per_test": repetitions,
        "mean_latency_ms": round(sum(latencies) / len(latencies), 2),
        "min_latency_ms": round(min(latencies), 2),
        "max_latency_ms": round(max(latencies), 2),
        "initial_rss_mb": round(initial_rss, 2),
        "peak_rss_mb": round(peak_rss, 2),
        "ram_delta_mb": round(ram_delta, 2),
        "detailed_runs": results,
    }

    hw_table = Table(title="Hardware & Resource Profiling", show_header=True)
    hw_table.add_column("Resource", style="cyan", width=25)
    hw_table.add_column("Measurement", style="bold green", width=25)

    hw_table.add_row("CPU Physical / Logical", f"{system_info['cpu_cores_physical']} physical / {system_info['cpu_cores_logical']} logical")
    hw_table.add_row("System RAM Capacity", f"{system_info['total_ram_gb']} GB")
    hw_table.add_row("Peak Process RSS", f"{summary_metrics['peak_rss_mb']} MB")
    hw_table.add_row("RAM Headroom Remaining", f"{system_info['total_ram_gb'] * 1024 - summary_metrics['peak_rss_mb']:.0f} MB")
    hw_table.add_row("Average End-to-End Latency", f"{summary_metrics['mean_latency_ms']} ms")

    console.print(hw_table)

    out_file = Path("d:/incubrix/benchmarks/benchmark_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary_metrics, f, indent=2)

    console.print(Panel(f"[bold green]Benchmark data saved to: {out_file}[/bold green]", expand=False))
    return summary_metrics
