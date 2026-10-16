// Untimed, ADMIN-ONLY native test utilities, never application HTTP routes.
// Refuse unexpected ownership/ranges instead of silently reseeding application
// or platform state. No native system tables, credentials or SQL driver.
import { internalMutationGeneric as internalMutation, internalQueryGeneric as internalQuery } from "convex/server";
import { v } from "convex/values";

const baseline = "0000000000000500000";
async function allocation(ctx) {
  const result = await ctx.db.query("feed_sequences")
    .withIndex("by_name", (q) => q.eq("name", "posts")).unique();
  if (!result) throw new Error("Missing canonical allocation metadata");
  return result;
}
async function extraPosts(ctx) {
  return await ctx.db.query("posts")
    .withIndex("by_public_id", (q) => q.gt("id", baseline)).take(129);
}

export const writeProbeState = internalQuery({
  args: {},
  handler: async (ctx) => {
    const sequence = await allocation(ctx);
    return { sequence: sequence.last_id, extra_posts: (await extraPosts(ctx)).length };
  },
});

const wide = "9007199254740993".padStart(19, "0");
const ghost = "999999".padStart(19, "0");
const edgeTime = "2098-01-01T00:00:00.000Z";
function edgeMarker(marker) {
  if (!/^tds-native-edge-probe:[A-Za-z0-9_-]{1,64}:$/.test(marker)) throw new Error("Invalid edge namespace");
}
function edgeRows(marker) {
  const result = [{ id: wide, user_id: wide, body: marker + "café\u0000😀", created_at: edgeTime }];
  for (let i = 0; i < 24; i++) result.push({
    id: (501000n + BigInt(i)).toString().padStart(19, "0"), user_id: ghost,
    body: marker + "orphan-" + i, created_at: "2099-01-01T00:00:00.000Z",
  });
  return result;
}

export const installStoredEdges = internalMutation({
  args: { marker: v.string() },
  handler: async (ctx, { marker }) => {
    edgeMarker(marker);
    const sequence = await allocation(ctx);
    if (sequence.last_id !== baseline || (await extraPosts(ctx)).length) throw new Error("Edge setup requires clean canonical state");
    const [existing, absentAuthor, duplicateName] = await Promise.all([
      ctx.db.query("users").withIndex("by_public_id", (q) => q.eq("id", wide)).unique(),
      ctx.db.query("users").withIndex("by_public_id", (q) => q.eq("id", ghost)).unique(),
      ctx.db.query("users").withIndex("by_username", (q) => q.eq("username", "native-wide-user")).unique(),
    ]);
    if (existing || absentAuthor || duplicateName) throw new Error("Unexpected edge fixture ownership");
    await ctx.db.insert("users", { id: wide, username: "native-wide-user", created_at: edgeTime });
    for (const post of edgeRows(marker)) await ctx.db.insert("posts", post);
    return { users_added: 1, posts_added: 25 };
  },
});

export const resetStoredEdges = internalMutation({
  args: { marker: v.string() },
  handler: async (ctx, { marker }) => {
    edgeMarker(marker);
    const sequence = await allocation(ctx);
    if (sequence.last_id !== baseline) throw new Error("Unexpected edge allocation; preserve state");
    const posts = await extraPosts(ctx);
    const expected = new Map(edgeRows(marker).map((post) => [post.id, post]));
    if (posts.length !== expected.size) throw new Error("Unexpected edge range; preserve state");
    const likes = [];
    for (const post of posts) {
      const row = expected.get(post.id);
      if (!row || post.user_id !== row.user_id || post.body !== row.body || post.created_at !== row.created_at) throw new Error("Unexpected edge post ownership");
      const entries = await ctx.db.query("likes").withIndex("by_post_user", (q) => q.eq("post_id", post.id)).take(3);
      if (entries.length > 1 || entries.some((like) => like.user_id !== wide || like.post_id !== wide)) throw new Error("Unexpected edge like ownership");
      likes.push(...entries);
    }
    const user = await ctx.db.query("users").withIndex("by_public_id", (q) => q.eq("id", wide)).unique();
    if (!user || user.username !== "native-wide-user" || user.created_at !== edgeTime) throw new Error("Unexpected edge user ownership");
    for (const like of likes) await ctx.db.delete(like._id);
    for (const post of posts) await ctx.db.delete(post._id);
    await ctx.db.delete(user._id);
    return { users_deleted: 1, posts_deleted: posts.length, likes_deleted: likes.length };
  },
});

export const resetWriteProbe = internalMutation({
  args: { marker: v.string() },
  handler: async (ctx, { marker }) => {
    if (!/^tds-native-write-probe:[A-Za-z0-9_-]{1,64}:$/.test(marker)) throw new Error("Invalid probe namespace");
    const sequence = await allocation(ctx);
    const posts = await extraPosts(ctx);
    if (posts.length > 128 || sequence.last_id !== (500000n + BigInt(posts.length)).toString().padStart(19, "0")) {
      throw new Error("Unexpected probe allocation/range; preserve state");
    }
    const likes = [];
    for (let i = 0; i < posts.length; i++) {
      const post = posts[i];
      if (post.id !== (500001n + BigInt(i)).toString().padStart(19, "0") || !post.body.startsWith(marker)) {
        throw new Error("Unexpected probe post ownership; preserve state");
      }
      likes.push(...await ctx.db.query("likes")
        .withIndex("by_post_user", (q) => q.eq("post_id", post.id)).collect());
      if (likes.length + posts.length > 1000) throw new Error("Probe cleanup bound exceeded; preserve state");
    }
    for (const like of likes) await ctx.db.delete(like._id);
    for (const post of posts) await ctx.db.delete(post._id);
    if (posts.length) await ctx.db.patch(sequence._id, { last_id: baseline });
    return { deleted_posts: posts.length, deleted_likes: likes.length };
  },
});
