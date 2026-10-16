import {
  httpActionGeneric as httpAction,
  httpRouter,
  makeFunctionReference,
} from "convex/server";
import { authenticate, HttpError, parseJSON, positiveId, validateBody } from "./contract.js";

const feedQuery = makeFunctionReference("native:feed");
const detailQuery = makeFunctionReference("native:detail");
const storageQuery = makeFunctionReference("native:storageProbe");
const uptimeAction = makeFunctionReference("clock:backendUptime");
const createMutation = makeFunctionReference("native:createPost");
const likeMutation = makeFunctionReference("native:likePost");
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

const write = httpAction(async (ctx, request) => {
  try {
    const path = new URL(request.url).pathname;
    const like = /^\/posts\/([^/]*)\/like$/.exec(path);
    if (path !== "/posts" && !like) return error("not found", 404);
    const subject = await authenticate(request.headers.get("Authorization"), process.env.JWT_SECRET);
    const userId = subject.id.padStart(19, "0");
    if (path === "/posts") {
      let value;
      try {
        value = parseJSON(new Uint8Array(await request.arrayBuffer()));
      } catch {
        return error("malformed JSON body", 400);
      }
      const body = validateBody(value);
      const result = await ctx.runMutation(createMutation, { userId, body });
      if (result.error) return error(result.error, result.status);
      // Original creation response uses the signed claim; subsequent reads
      // independently join users.username, without modifying the stored user.
      result.post.author = subject.username;
      return json(`{"post":${postJson(result.post)}}`, 201);
    }
    const id = positiveId(like[1]);
    const result = await ctx.runMutation(likeMutation, { userId, postId: id.padStart(19, "0") });
    if (result.error) return error(result.error, result.status);
    return json(`{"liked":true,"already_liked":${result.already_liked},"post_id":${id}}`, result.already_liked ? 200 : 201);
  } catch (failure) {
    return failure instanceof HttpError ? error(failure.message, failure.status) : error("internal server error", 500);
  }
});

const http = httpRouter();
http.route({ pathPrefix: "/", method: "GET", handler: read });
http.route({ pathPrefix: "/", method: "POST", handler: write });
export default http;
