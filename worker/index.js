export default {
    async fetch(_request, env) {
        const row = await env.DB.prepare('SELECT 1 AS value').first()
        return Response.json(row)
    },
}
