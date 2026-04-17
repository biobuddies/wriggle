"""Build the static worker wasm fixture used by the local worker entrypoint."""

from pathlib import Path
from sys import path

from wasmtime import wat2wasm

path.insert(0, str(Path(__file__).resolve().parents[1]))

from wriggle import select


def encoded(data: bytes | bytearray | memoryview) -> str:
    return '\\' + data.hex('\\', 1) if data else ''


query = select(1).encode()
prefix = b'content-type:application/json\n\n'

Path(__file__).with_name('worker.wasm').write_bytes(
    wat2wasm(
        f'''(module
  (memory $request (export "request") 1)
  (memory $sql (export "sql") 1)
  (memory $http (export "http") 1)
  (data (memory $sql) (i32.const 0) "{encoded(query)}")
  (data (memory $http) (i32.const 0) "{encoded(prefix)}")
  (global (export "http_offset") i32 (i32.const {len(prefix)}))
  (func (export "query") (param i32) (result i32 i32)
    i32.const 0
    i32.const {len(query)}
  )
  (func (export "respond") (param i32) (result i32 i32)
    i32.const 0
    i32.const {len(prefix)}
    local.get 0
    i32.add
  )
)'''
    )
)
