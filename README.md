# wriggle

Goal: enforce append-only Write Once, Read Many (WORM) data flows.

Two WebAssembly components for Cloudflare Workers, each built for fast local iteration too:

1. Compile Django-like models and Object Relational Mapping (ORM) queries to WebAssembly
   (WASM) targeting SQLite or Cloudflare D1. Reject clobbering operations such as
   `UPDATE` and locking reads such as `SELECT ... FOR UPDATE`.
2. Compile Jinja templating to WebAssembly (WASM), render those query results, and return the response.
