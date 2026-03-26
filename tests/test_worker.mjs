import test from 'node:test'
import assert from 'node:assert/strict'

import worker from '../worker/index.js'


test('worker sends select one query to D1 and returns the row as JSON', async () => {
    const calls = []
    const env = {
        DB: {
            prepare(query) {
                calls.push(query)
                return {
                    raw: async () => [[1]],
                }
            },
        },
    }

    const response = await worker.fetch(new Request('http://example.test'), env)

    assert.deepEqual(calls, ['SELECT 1'])
    assert.deepEqual(await response.json(), [[1]])
})


test('worker returns whatever prepare() returns', async () => {
    let query
    const env = {
        DB: {
            prepare(received) {
                query = received
                return {
                    raw: async () => [[99, 'canned']],
                }
            },
        },
    }

    const response = await worker.fetch(new Request('http://example.test'), env)

    assert.equal(query, 'SELECT 1')
    assert.deepEqual(await response.json(), [[99, 'canned']])
})
