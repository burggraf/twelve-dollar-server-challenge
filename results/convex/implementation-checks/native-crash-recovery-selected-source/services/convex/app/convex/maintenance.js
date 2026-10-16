// Untimed ADMIN-ONLY application-delta reset, never an application HTTP route.
// Supported native APIs only; no underlying SQL driver or platform-table reset.
import { internalMutationGeneric as internalMutation } from "convex/server";
import { v } from "convex/values";

const baseline = "0000000000000500000";
// Immutable seed/generate.mjs: posts < END (2026-01-01), likes add <7days.
// Thus EVERY canonical like precedes this exclusive seed ceiling. Current
// application writes must be later; independent full canonical verification
// after reset is mandatory, never inferred merely from these deletion counts.
const seedCeiling = "2026-01-08T00:00:00.000Z";
const iso = /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/;
const zero = "0000000000000000000";
const lastUser = "0000000000000050000";
// Hard untimed-reset safety bound: at most1,000,000 allocated application deltas
// per frozen attempt. Wide-ID edge probes use their separate owned fixture reset.
const lastBenchmarkPost = "0000000000001500000";
const normalized = (id) => /^\d{19}$/.test(id) && id > zero;
const canonicalUser = (id) => normalized(id) && id <= lastUser;
async function allocation(ctx) {
  const sequence = await ctx.db.query("feed_sequences")
    .withIndex("by_name", (q) => q.eq("name", "posts")).unique();
  if (!sequence || !normalized(sequence.last_id) || sequence.last_id < baseline || sequence.last_id > lastBenchmarkPost) throw new Error("Unexpected allocation namespace; preserve state");
  return sequence;
}

export const resetLikesPage = internalMutation({
  args: { cursor: v.union(v.string(), v.null()) },
  handler: async (ctx, { cursor }) => {
    const sequence = await allocation(ctx);
    const latest = new Date(Date.now() + 1000).toISOString();
    // Exactly ONE paginated query per native mutation; existing index only.
    const page = await ctx.db.query("likes").withIndex("by_post_user").order("asc")
      .paginate({ cursor, numItems: 1000 });
    let deleted = 0;
    for (const like of page.page) {
      if (!iso.test(like.created_at)) throw new Error("Unexpected like timestamp; preserve state");
      if (like.created_at >= seedCeiling) {
        if (!canonicalUser(like.user_id) || !normalized(like.post_id) || like.post_id > sequence.last_id || like.created_at > latest) throw new Error("Unexpected added-like ownership; preserve state");
        const post = await ctx.db.query("posts").withIndex("by_public_id", (q) => q.eq("id", like.post_id)).unique();
        if (!post) throw new Error("Unexpected orphan like; preserve state");
        await ctx.db.delete(like._id);
        deleted++;
      }
    }
    return { cursor: page.continueCursor, isDone: page.isDone, deleted };
  },
});

export const resetPostsBatch = internalMutation({
  args: {},
  handler: async (ctx) => {
    const sequence = await allocation(ctx);
    const latest = new Date(Date.now() + 1000).toISOString();
    const posts = await ctx.db.query("posts")
      .withIndex("by_public_id", (q) => q.gt("id", baseline)).order("asc").take(100);
    for (const post of posts) {
      if (!normalized(post.id) || post.id > sequence.last_id || !canonicalUser(post.user_id) || !iso.test(post.created_at) || post.created_at < seedCeiling || post.created_at > latest) throw new Error("Unexpected noncanonical post ownership; preserve state");
      const likes = await ctx.db.query("likes").withIndex("by_post_user", (q) => q.eq("post_id", post.id)).take(1);
      if (likes.length) throw new Error("Reset added likes before posts; preserve state");
      await ctx.db.delete(post._id);
    }
    return { deleted: posts.length };
  },
});

export const resetAllocation = internalMutation({
  args: {},
  handler: async (ctx) => {
    const remaining = await ctx.db.query("posts")
      .withIndex("by_public_id", (q) => q.gt("id", baseline)).take(1);
    if (remaining.length) throw new Error("Noncanonical posts remain; preserve allocation");
    const sequence = await allocation(ctx);
    if (sequence.last_id !== baseline) await ctx.db.patch(sequence._id, { last_id: baseline });
    return { last_id: baseline };
  },
});
