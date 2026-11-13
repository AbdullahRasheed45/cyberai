"""Read-only live rental status, served on loopback with no mutation API."""

# Embedded dashboard JavaScript is kept as source text rather than Python expressions.
# ruff: noqa: E501

from __future__ import annotations

import contextlib
import json
from collections import deque
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def snapshot(root: Path, runs: Path):
    trackers = []
    for path in sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:50]:
        value = read_json(path)
        if isinstance(value, dict) and "sample_count" in value and "state" in value:
            value["file"] = path.name
            log = Path(value.get("log", "")).resolve()
            if log.is_relative_to(root.resolve()) and log.is_file():
                try:
                    with log.open("rb") as stream:
                        stream.seek(max(0, log.stat().st_size - 8192))
                        value["console_tail"] = stream.read(8192).decode("utf-8", errors="replace")
                except OSError:
                    value["console_tail"] = "log temporarily unavailable"
            samples = value.get("samples", [])
            latest = samples[-1] if samples else {}
            value["signals"] = []
            if latest.get("utc"):
                age = (datetime.now(UTC) - datetime.fromisoformat(latest["utc"])).total_seconds()
                value["sample_age_s"] = age
                if value["state"] == "RUNNING" and age > 15:
                    value["signals"].append("STALE_TELEMETRY: inspect process and connection")
            memory = latest.get("host_memory_kib") or {}
            if (
                memory.get("MemTotal")
                and memory.get("MemAvailable", memory["MemTotal"]) / memory["MemTotal"] < 0.1
            ):
                value["signals"].append(
                    "LOW_AVAILABLE_RAM: inspect swap and context/batch allocation"
                )
            if latest.get("gpu_error"):
                value["signals"].append("GPU_TELEMETRY_UNAVAILABLE")
            if value["state"] in {"FAILED", "TIMED_OUT"}:
                value["signals"].append("COMMAND_FAILED: inspect saved console log")
            trackers.append(value)
    training = []
    paths = sorted(
        runs.glob("*/step_measurements.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    for path in paths[:20]:
        try:
            with path.open(encoding="utf-8") as stream:
                lines = deque(stream, maxlen=100)
            records = []
            for line in lines:
                # A currently appending final line is retried on next refresh.
                with contextlib.suppress(ValueError):
                    records.append(json.loads(line))
            losses = []
            loss_file = path.parent / "training_logs.jsonl"
            if loss_file.is_file():
                with loss_file.open(encoding="utf-8") as stream:
                    for line in deque(stream, maxlen=20):
                        with contextlib.suppress(ValueError):
                            losses.append(json.loads(line))
            training.append(
                {"run": path.parent.name, "recent_steps": records, "recent_training_logs": losses}
            )
        except OSError:
            continue
    paths = sorted(root.glob("*_requests/*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    requests = []
    for path in paths[:200]:
        value = read_json(path)
        if isinstance(value, dict):
            value["group"] = path.parent.name
            requests.append(value)
    return {
        "updated_utc": datetime.now(UTC).isoformat(),
        "trackers": trackers,
        "training": training,
        "recent_requests": requests,
        "request_files_total": len(paths),
        "note": "Recent windows only; raw files retain history. Samples are observations, not bottleneck proof.",
    }


PAGE = """<!doctype html><meta charset="utf-8"><title>Spark live tracker</title>
<style>body{font:15px system-ui;background:#101820;color:#e5edf3;margin:28px}h1{font-size:24px}
table{border-collapse:collapse;width:100%;margin:12px 0 28px}td,th{text-align:left;padding:9px;border-bottom:1px solid #36434e}
pre{white-space:pre-wrap;background:#1d2933;padding:14px}small{color:#b6cbd8}svg{background:#1d2933;width:100%;height:100px}</style>
<h1>DGX Spark live tracker</h1><p id="connection">Connecting…</p>
<small>Refresh: 2 seconds. Read-only. Missing measurements stay unavailable. Use saved raw data for comparisons.</small>
<h2>Commands and hardware</h2><div id="commands"></div>
<h2>Training progress</h2><div id="training"></div>
<h2>Recent inference requests</h2><div id="requests"></div>
<script>
const text=(tag,s)=>{let e=document.createElement(tag);e.textContent=s;return e};
function table(parent,headers,rows){let t=document.createElement('table'),r=document.createElement('tr');headers.forEach(h=>r.append(text('th',h)));t.append(r);rows.forEach(row=>{let r=document.createElement('tr');row.forEach(v=>r.append(text('td',v??'unavailable')));t.append(r)});parent.append(t)}
function chart(parent,values){if(!values.length)return;let s=document.createElementNS('http://www.w3.org/2000/svg','svg');s.setAttribute('viewBox','0 0 600 100');let p=document.createElementNS(s.namespaceURI,'polyline'),max=Math.max(...values,1);p.setAttribute('points',values.map((v,i)=>`${i*590/Math.max(values.length-1,1)+5},${95-v/max*90}`).join(' '));p.setAttribute('fill','none');p.setAttribute('stroke','#79d6bb');p.setAttribute('stroke-width','2');s.append(p);parent.append(s)}
async function refresh(){try{let r=await fetch('/api/state',{cache:'no-store'});if(!r.ok)throw Error(r.status);let d=await r.json();document.getElementById('connection').textContent='Updated '+d.updated_utc;
let c=document.getElementById('commands');c.replaceChildren();d.trackers.forEach(t=>{c.append(text('h3',t.file+' — '+t.state));let a=t.samples.at(-1)||{};c.append(text('pre',JSON.stringify({elapsed_s:t.elapsed_s,exit_code:t.exit_code,sample_age_s:t.sample_age_s,signals:t.signals,host_memory_kib:a.host_memory_kib,gpu:a.gpu_sample,gpu_error:a.gpu_error,disk_free_bytes:a.disk_free_bytes},null,2)))});
let tr=document.getElementById('training');tr.replaceChildren();d.training.forEach(t=>{tr.append(text('h3',t.run+' — seconds per completed optimizer step'));chart(tr,t.recent_steps.map(s=>s.seconds));table(tr,['Step','Seconds','Actual tokens','Tokens/s','CUDA allocated bytes'],t.recent_steps.slice(-10).map(s=>[s.completed_step,s.seconds.toFixed(3),s.nonpadding_tokens,(s.nonpadding_tokens/s.seconds).toFixed(1),s.cuda_allocated_bytes]));tr.append(text('pre',JSON.stringify(t.recent_training_logs,null,2)))});
d.trackers.forEach(t=>{if(t.console_tail){c.append(text('h4',t.file+' console tail'));c.append(text('pre',t.console_tail))}});
let q=document.getElementById('requests');q.replaceChildren();table(q,['Group','Model','Input tokens','Output tokens','Seconds','TTFT s','Decode tok/s','Request output tok/s','Result'],d.recent_requests.slice(0,30).map(s=>[s.group,s.model,s.prompt_tokens,s.completion_tokens,s.runtime_s.toFixed(3),s.ttft_s,s.decode_tok_s,s.completion_tokens!=null?(s.completion_tokens/s.runtime_s).toFixed(1):null,s.ok?'OK':s.error]));
}catch(e){document.getElementById('connection').textContent='Connection/error: '+e.message+'; last displayed data may be stale'}setTimeout(refresh,2000)}refresh();
</script>"""


def server(root: Path, runs: Path, port=8765):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path == "/":
                body, content_type, status = PAGE.encode(), "text/html; charset=utf-8", 200
            elif self.path == "/api/state":
                body = json.dumps(snapshot(root, runs)).encode()
                content_type, status = "application/json", 200
            else:
                body, content_type, status = b"not found", "text/plain", 404
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("artifacts"))
    parser.add_argument("--runs", type=Path, default=Path("runs"))
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with server(args.root.resolve(), args.runs.resolve(), args.port) as http:
        print(f"Live tracker: http://127.0.0.1:{http.server_port}", flush=True)
        with contextlib.suppress(KeyboardInterrupt):
            http.serve_forever()


if __name__ == "__main__":
    main()
