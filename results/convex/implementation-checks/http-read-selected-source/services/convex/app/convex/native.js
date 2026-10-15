import { internalQueryGeneric as internalQuery } from "convex/server";
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

export const detail = internalQuery({
  args: { id: v.string() },
  handler: async (ctx, { id }) => {
    const post = await ctx.db.query("posts")
      .withIndex("by_public_id", (q) => q.eq("id", id)).unique();
    return await projectPost(ctx, post);
  },
});
