import {
  httpActionGeneric as httpAction,
  httpRouter,
  makeFunctionReference,
} from "convex/server";

const feedQuery = makeFunctionReference("native:feed");
const detailQuery = makeFunctionReference("native:detail");
const storageQuery = makeFunctionReference("native:storageProbe");
const uptimeAction = makeFunctionReference("clock:backendUptime");
const maximumId = 9223372036854775807n;

function identity(text) {
  if (typeof text !== "string" || !/^[0-9]+$/.test(text)) return null;
  const value = BigInt(text);
  return value > 0n && value <= maximumId ? value.toString() : null;
}

function json(text, status = 200) {
  return new Response(text, {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function error(message, status) {
  return json(JSON.stringify({ error: message }), status);
}

// IDs never pass through Number. Only validated integer text is interpolated;
// all untrusted string fields use JSON escaping, including embedded NUL.
function postJson(post) {
  const id = identity(post.id);
  if (id === null || !Number.isSafeInteger(post.like_count) || post.like_count < 0) {
    throw new Error("Invalid native post projection");
  }
  return `{"id":${id},"body":${JSON.stringify(post.body)},"created_at":${JSON.stringify(post.created_at)},"author":${JSON.stringify(post.author)},"like_count":${post.like_count}}`;
}

const read = httpAction(async (ctx, request) => {
  try {
    const path = new URL(request.url).pathname;
    if (path === "/health") {
      try {
        await ctx.runQuery(storageQuery, {});
      } catch {
        return json('{"status":"degraded","db":"unreachable","error":"storage unavailable"}', 503);
      }
      const uptime = await ctx.runAction(uptimeAction, {});
      if (!Number.isSafeInteger(uptime) || uptime < 0) throw new Error("Backend clock unavailable");
      return json(`{"status":"ok","db":"ok","uptime_s":${uptime}}`);
    }
    if (path === "/feed") {
      const posts = await ctx.runQuery(feedQuery, {});
      return json(`{"posts":[${posts.map(postJson).join(",")}]}`);
    }
    const match = /^\/posts\/([^/]*)$/.exec(path);
    if (match) {
      const id = identity(match[1]);
      if (id === null) return error("invalid post id", 400);
      const post = await ctx.runQuery(detailQuery, { id: id.padStart(19, "0") });
      return post === null
        ? error("post not found", 404)
        : json(`{"post":${postJson(post)}}`);
    }
    return error("not found", 404);
  } catch {
    return error("internal server error", 500);
  }
});

const http = httpRouter();
http.route({ pathPrefix: "/", method: "GET", handler: read });
export default http;
