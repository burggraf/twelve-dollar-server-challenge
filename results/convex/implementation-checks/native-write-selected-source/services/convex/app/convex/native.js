import { internalQueryGeneric as internalQuery, internalMutationGeneric as internalMutation } from "convex/server";
import { v } from "convex/values";

// Untimed private native integration probe; not a public application endpoint.
export const storageProbe = internalQuery({
  args: {},
  handler: async (ctx) => {
    const [users, posts, likes] = await Promise.all(
      ["users", "posts", "likes"].map((table) => ctx.db.query(table).take(1)),
    );
    return { users, posts, likes };
  },
});

export const canonicalPage = internalQuery({
  args: {
    table: v.union(v.literal("users"), v.literal("posts"), v.literal("likes")),
    cursor: v.union(v.null(), v.string()),
  },
  handler: async (ctx, { table, cursor }) => {
    const index = table === "likes" ? "by_post_user" : "by_public_id";
    return await ctx.db.query(table).withIndex(index).order("asc")
      .paginate({ cursor, numItems: 1000 });
  },
});

async function projectPost(ctx, post) {
  if (!post) return null;
  const [author, likes] = await Promise.all([
    ctx.db.query("users").withIndex("by_public_id", (q) => q.eq("id", post.user_id)).unique(),
    ctx.db.query("likes").withIndex("by_post_user", (q) => q.eq("post_id", post.id)).collect(),
  ]);
  if (!author) return null;
  return {
    // Internal JSON-safe decimal representation. The compatibility HTTP surface
    // must serialize this as an exact integer, not an unsafe JS Number.
    id: BigInt(post.id).toString(),
    body: post.body,
    created_at: post.created_at,
    author: author.username,
    like_count: likes.length,
  };
}

export const feed = internalQuery({
  args: {},
  handler: async (ctx) => {
    const result = [];
    let cursor = null;
    do {
      const page = await ctx.db.query("posts").withIndex("by_created_at_id")
        .order("desc").paginate({ cursor, numItems: 20 });
      const posts = await Promise.all(page.page.map((post) => projectPost(ctx, post)));
      for (const post of posts) {
        if (post) result.push(post);
        if (result.length === 20) return result;
      }
      if (page.isDone) break;
      cursor = page.continueCursor;
    } while (true);
    return result;
  },
});

// Native serializable transactions/OCC protect allocation and indexed absence
// reads. These are logical application keys, not physical SQL UNIQUE/FKs.
export const createPost = internalMutation({
  args: { userId: v.string(), body: v.string() },
  handler: async (ctx, { userId, body }) => {
    const author = await ctx.db.query("users")
      .withIndex("by_public_id", (q) => q.eq("id", userId)).unique();
    if (!author) throw new Error("Missing post author");
    const sequence = await ctx.db.query("feed_sequences")
      .withIndex("by_name", (q) => q.eq("name", "posts")).unique();
    if (!sequence || !/^\d{19}$/.test(sequence.last_id)) throw new Error("Invalid allocation metadata");
    const next = BigInt(sequence.last_id) + 1n;
    if (next > 9223372036854775807n) throw new Error("Post identity exhausted");
    const id = next.toString().padStart(19, "0");
    await ctx.db.patch(sequence._id, { last_id: id });
    const collision = await ctx.db.query("posts")
      .withIndex("by_public_id", (q) => q.eq("id", id)).unique();
    // Throw after the sequence patch: the SAME native transaction rolls back
    // allocation as well as any post write. Never overwrite a colliding ID.
    if (collision) throw new Error("Post identity collision");
    const created_at = new Date(Date.now()).toISOString();
    await ctx.db.insert("posts", { id, user_id: userId, body, created_at });
    return { post: { id: next.toString(), body, created_at, author: author.username, like_count: 0 } };
  },
});

export const likePost = internalMutation({
  args: { userId: v.string(), postId: v.string() },
  handler: async (ctx, { userId, postId }) => {
    const post = await ctx.db.query("posts")
      .withIndex("by_public_id", (q) => q.eq("id", postId)).unique();
    if (!post) return { status: 404, error: "post not found" };
    const user = await ctx.db.query("users")
      .withIndex("by_public_id", (q) => q.eq("id", userId)).unique();
    if (!user) throw new Error("Missing liking user");
    const existing = await ctx.db.query("likes")
      .withIndex("by_user_post", (q) => q.eq("user_id", userId).eq("post_id", postId)).unique();
    if (existing) return { already_liked: true };
    await ctx.db.insert("likes", { user_id: userId, post_id: postId, created_at: new Date(Date.now()).toISOString() });
    return { already_liked: false };
  },
});

export const detail = internalQuery({
  args: { id: v.string() },
  handler: async (ctx, { id }) => {
    const post = await ctx.db.query("posts")
      .withIndex("by_public_id", (q) => q.eq("id", id)).unique();
    return await projectPost(ctx, post);
  },
});
