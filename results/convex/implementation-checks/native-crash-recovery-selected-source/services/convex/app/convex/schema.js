import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

// Public IDs are normalized 19-digit positive signed64 decimal text; ISO UTC
// timestamps remain exact original strings. Native _id/_creationTime are extra.
// Indexes are not SQL UNIQUE/FK declarations: native transaction invariants and
// verified import establish the logical keys/relations.
export default defineSchema({
  users: defineTable({ id: v.string(), username: v.string(), created_at: v.string() })
    .index("by_public_id", ["id"])
    .index("by_username", ["username"]),
  posts: defineTable({ id: v.string(), user_id: v.string(), body: v.string(), created_at: v.string() })
    .index("by_public_id", ["id"])
    .index("by_created_at_id", ["created_at", "id"])
    .index("by_user_id", ["user_id"]),
  likes: defineTable({ user_id: v.string(), post_id: v.string(), created_at: v.string() })
    .index("by_user_post", ["user_id", "post_id"])
    .index("by_post_user", ["post_id", "user_id"]),
  // Persistent allocation metadata only; no like counts or response cache.
  feed_sequences: defineTable({ name: v.string(), last_id: v.string() })
    .index("by_name", ["name"]),
});
