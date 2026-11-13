#!/usr/bin/env python3
"""Record command output, elapsed time and sampled host/device telemetry.

Standard-library only; usable in a provider environment without project deps.
Unavailable measurements remain null. No access tokens or full env are captured.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import signal
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path


def sample():
    record = {
        "utc": datetime.now(UTC).isoformat(),
        "host_memory_kib": None,
        "gpu_sample": None,
        "gpu_error": None,
        "disk_free_bytes": shutil.disk_usage(Path.cwd()).free,
    }
    memory = Path("/proc/meminfo")
    if memory.is_file():
        record["host_memory_kib"] = {
            line.split(":", 1)[0]: int(line.split()[1])
            for line in memory.read_text().splitlines()
            if line.split(":", 1)[0] in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}
        }
    if shutil.which("nvidia-smi"):
        try:
            query = ",".join(
                [
                    "timestamp",
                    "name",
                    "memory.used",
                    "memory.total",
                    "utilization.gpu",
                    "temperature.gpu",
                    "power.draw",
                    "clocks.sm",
                    "clocks.mem",
                ]
            )
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=" + query, "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if result.returncode:
                record["gpu_error"] = result.stderr.strip()
            else:
                fields = query.split(",")
                csv = result.stdout.strip()
                values = [v.strip() for v in csv.splitlines()[0].split(",")] if csv else []
                # GB10 unified memory reports memory.* as [N/A]; host_memory_kib
                # above is the authoritative memory reading on that platform.
                record["gpu_sample"] = {
                    "fields": fields,
                    "csv": csv,
                    "values": dict(zip(fields, values, strict=False)),
                }
        except (OSError, subprocess.TimeoutExpired) as exc:
            record["gpu_error"] = str(exc)
    else:
        record["gpu_error"] = "nvidia-smi unavailable"
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=21600)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or args.timeout <= 0:
        parser.error("a command and positive timeout are required")
    log = args.out.with_suffix(".log")
    if args.out.exists() or log.exists():
        parser.error("choose new output paths; prior evidence is never overwritten")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "started_utc": datetime.now(UTC).isoformat(),
        "argv": command,
        "platform": platform.platform(),
        "exit_code": None,
        "timed_out": False,
        "state": "STARTING",
        "samples": [],
        "log": str(log),
        "environment": {
            key: os.environ[key]
            for key in (
                "RUN_ID",
                "TRAIN_MODE",
                "PILOT_DATA",
                "TRAIN_MAX_SEQ_LENGTH",
                "TRAIN_MAX_STEPS",
                "TRAIN_BATCH_SIZE",
                "TRAIN_GRAD_ACCUM",
                "TRAIN_MEASURE_WARMUP_STEPS",
                "SERVED_MODEL",
                "WORKLOAD_DOMAIN",
            )
            if key in os.environ
        },
    }
    started = time.monotonic()
    process = None
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=3
        )
        record["git_commit"] = revision.stdout.strip() if revision.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        record["git_commit"] = None

    def persist():
        record["elapsed_s"] = time.monotonic() - started
        temporary = args.out.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(record, indent=2), encoding="utf-8")
        for attempt in range(20):
            try:
                temporary.replace(args.out)
                break
            except PermissionError:
                # Windows readers/virus scanners can briefly hold the destination.
                if attempt == 19:
                    raise
                time.sleep(0.025)

    child_env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    child_env.setdefault("LIVE_METRICS_DIR", str(args.out.parent / (args.out.stem + "_requests")))
    record["request_metrics_dir"] = child_env["LIVE_METRICS_DIR"]
    samples_path = args.out.with_suffix(".samples.jsonl")
    record["samples_file"] = str(samples_path)
    record["sample_count"] = 0
    try:
        persist()
        with (
            log.open("x", encoding="utf-8") as stream,
            samples_path.open("x", encoding="utf-8") as samples,
        ):
            process = subprocess.Popen(
                command,
                stdout=stream,
                stderr=subprocess.STDOUT,
                start_new_session=os.name != "nt",
                env=child_env,
            )
            record["state"] = "RUNNING"
            persist()
            # Output goes directly to disk, so a verbose model cannot fill RAM.
            while True:
                reading = sample()
                record["samples"].append(reading)
                record["samples"] = record["samples"][-120:]
                record["sample_count"] += 1
                samples.write(json.dumps(reading) + "\n")
                samples.flush()
                persist()
                if process.poll() is not None:
                    break
                if time.monotonic() - started >= args.timeout:
                    record["timed_out"] = True
                    if os.name != "nt":
                        os.killpg(process.pid, signal.SIGTERM)
                    else:
                        process.terminate()
                    break
                time.sleep(min(1, args.timeout / 2))
            try:
                record["exit_code"] = process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name != "nt":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                record["exit_code"] = process.wait(timeout=5)
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        record["elapsed_s"] = time.monotonic() - started
        record["ended_utc"] = datetime.now(UTC).isoformat()
        record["state"] = (
            "TIMED_OUT"
            if record["timed_out"]
            else ("COMPLETED" if record["exit_code"] == 0 else "FAILED")
        )
        persist()
    print(
        json.dumps(
            {
                "report": str(args.out),
                "log": str(log),
                "exit_code": record["exit_code"],
                "elapsed_s": record["elapsed_s"],
            }
        )
    )
    return (
        124
        if record["timed_out"]
        else (record["exit_code"] if record["exit_code"] is not None else 1)
    )


if __name__ == "__main__":
    raise SystemExit(main())
