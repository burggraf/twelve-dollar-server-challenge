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
