"""End-to-end test local worker serving."""

import json
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen
from time import monotonic, sleep
from urllib.error import URLError
from urllib.request import urlopen

from pytest import fail


def test_run_server_returns_select_one() -> None:
    port = 8791
    process = Popen(
        ['mise', 'run', 'run-server', '--port', str(port)],
        cwd=Path(__file__).resolve().parents[1],
        stderr=STDOUT,
        stdout=PIPE,
        text=True,
    )
    try:
        deadline = monotonic() + 30
        url = f'http://127.0.0.1:{port}'
        while True:
            if process.poll() is not None:
                fail(process.stdout.read() if process.stdout else 'run-server exited early')
            try:
                with urlopen(url, timeout=1) as response:
                    assert json.load(response) == [[1]]
                    return
            except URLError:
                if monotonic() >= deadline:
                    fail(process.stdout.read() if process.stdout else 'run-server did not start')
                sleep(0.1)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except TimeoutError:
            process.kill()
            process.wait(timeout=5)
