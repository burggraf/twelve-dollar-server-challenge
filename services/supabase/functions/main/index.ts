// Native Edge Runtime dispatcher, fixed to this application's user worker.
// No third-party imports, response caches, identity caches or application retries.
const startedAt = String(Date.now());
Deno.serve(async (req: Request) => {
  try {
    const worker = await EdgeRuntime.userWorkers.create({
      servicePath: '/home/deno/functions/feed',
      memoryLimitMb: 150,
      workerTimeoutMs: 400_000,
      context: { supervisor: { requestAbsentTimeoutMs: 60_000 } },
      noModuleCache: false,
      envVars: Object.entries({...Deno.env.toObject(), SERVING_STARTED_AT: startedAt}),
    });
    return await worker.fetch(req);
  } catch {
    return new Response(JSON.stringify({error:'internal server error'}),{status:500,headers:{'content-type':'application/json'}});
  }
});
