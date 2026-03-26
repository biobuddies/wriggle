import workerModule from './worker.wasm'

type DB = {
    prepare(query: string): {
        raw(): Promise<unknown>
    }
}

type Env = {
    DB: DB
}

type WorkerExports = WebAssembly.Exports & {
    http_offset: WebAssembly.Global
    query(requestLength: number): [number, number]
    http: WebAssembly.Memory
    request: WebAssembly.Memory
    respond(bodyLength: number): [number, number]
    sql: WebAssembly.Memory
}

const decoder = new TextDecoder()
const encoder = new TextEncoder()
const workerInstancePromise = WebAssembly.instantiate(workerModule)


export default {
    async fetch(request: Request, env: Env): Promise<Response> {
        const worker = (await workerInstancePromise).exports as WorkerExports
        const { http, http_offset, query, respond, sql } = worker
        const request_length = encoder.encodeInto(request.url, new Uint8Array(worker.request.buffer)).written
        const [sql_offset, sql_length] = query(request_length)
        const rows = await env.DB.prepare(
            decoder.decode(new Uint8Array(sql.buffer, sql_offset, sql_length))
        ).raw()
        const http_length = encoder.encodeInto(
            JSON.stringify(rows),
            new Uint8Array(http.buffer, http_offset.value),
        ).written
        const [offset, length] = respond(http_length)
        const [headers, responseBody] = decoder.decode(
            new Uint8Array(http.buffer, offset, length)
        ).split('\n\n')
        return new Response(responseBody, {
            headers: Object.fromEntries(headers.split('\n').map((header) => header.split(/:(.+)/))),
        })
    },
}
