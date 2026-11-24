#!/usr/bin/env python3
"""Drive the snail-scalp CLI in a disposable workdir and capture observable proof.

The CLI writes every output under relative `data/...` paths. Running it from the
repository would dirty tracked files, so this helper always runs it with cwd set
to a workdir created by verify_init.sh. It records the command, stdout, stderr,
and exit code as separate artifacts. A timeout kills only the process group this
helper started; it never kills by process name.
"""

import argparse
import os
import shlex
import signal
import subprocess
import sys
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, help="Repository root containing src/snail_scalp")
    p.add_argument("--workdir", required=True, help="Disposable workdir from verify_init.sh")
    p.add_argument("--artifacts", required=True, help="Directory for proof artifacts")
    p.add_argument("--label", required=True, help="Artifact basename, e.g. screen-offline")
    p.add_argument(
        "--site-packages",
        default=os.environ.get("SNAIL_VERIFY_SITE_PACKAGES", ""),
        help="Extra site-packages dir to append to PYTHONPATH when uv is unavailable",
    )
    p.add_argument("--timeout", type=float, default=30.0, help="Wall-clock limit in seconds")
    p.add_argument(
        "--interrupt",
        action="store_true",
        help="Send SIGINT on timeout so long-lived modes can print their shutdown line",
    )
    p.add_argument("cli_args", nargs=argparse.REMAINDER, help="Arguments after -- go to the CLI")
    return p.parse_args()


def stop(proc, use_sigint):
    sig = signal.SIGINT if use_sigint else signal.SIGKILL
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        return
    if not use_sigint:
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def main():
    a = parse_args()
    cli_args = [arg for arg in a.cli_args if arg != "--"]
    if not cli_args:
        print("No CLI arguments supplied after --", file=sys.stderr)
        return 2

    repo = Path(a.repo).resolve()
    workdir = Path(a.workdir).resolve()
    artifacts = Path(a.artifacts).resolve()
    if not (repo / "src" / "snail_scalp" / "cli.py").is_file():
        print(f"Not a snail-scalp repo: {repo}", file=sys.stderr)
        return 2
    if not workdir.is_dir():
        print(f"Workdir missing: {workdir}", file=sys.stderr)
        return 2
    artifacts.mkdir(parents=True, exist_ok=True)

    pythonpath = str(repo / "src")
    if a.site_packages:
        pythonpath += os.pathsep + a.site_packages
    env = dict(os.environ, PYTHONPATH=pythonpath)

    cmd = [sys.executable, "-m", "snail_scalp", *cli_args]
    proc = subprocess.Popen(
        cmd,
        cwd=workdir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=a.timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        stop(proc, a.interrupt)
        stdout, stderr = proc.communicate()
    rc = proc.returncode

    (artifacts / f"{a.label}.command.txt").write_text(
        " ".join(shlex.quote(part) for part in cmd) + "\n"
    )
    (artifacts / f"{a.label}.stdout.txt").write_text(stdout)
    (artifacts / f"{a.label}.stderr.txt").write_text(stderr)
    (artifacts / f"{a.label}.exit.txt").write_text(f"{rc}\n")

    status = "TIMEOUT" if timed_out else "OK"
    print(f"[{status}] {a.label}: exit={rc} artifacts={artifacts}/{a.label}.{{command,stdout,stderr,exit}}.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
