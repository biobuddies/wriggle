export default {
    async fetch(_request, env) {
        return Response.json(await env.DB.prepare('SELECT 1').raw())
    },
}
