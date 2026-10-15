package main

import (
	"testing"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

// These tests bootstrap the real pinned native runtime and its migrations.
// No standalone SQLite driver, fake App, or replacement collection metadata.
func nativeTestApp(t *testing.T) *pocketbase.PocketBase {
	t.Helper()
	app := pocketbase.NewWithConfig(pocketbase.Config{DefaultDataDir: t.TempDir()})
	if err := app.Bootstrap(); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = app.ClearBootstrap() })
	if err := app.RunAppMigrations(); err != nil {
		t.Fatal(err)
	}
	return app
}

func applicationCollection(t *testing.T, app core.App, name string) *core.Collection {
	t.Helper()
	collection, err := app.FindCollectionByNameOrId(name)
	if err != nil {
		t.Fatalf("required native application collection %q is missing: %v", name, err)
	}
	return collection
}

func TestNativeApplicationCollectionsAndWriteBoundary(t *testing.T) {
	app := nativeTestApp(t)
	for _, name := range []string{"feed_users", "feed_posts", "feed_likes", "feed_sequences"} {
		collection := applicationCollection(t, app, name)
		if collection.Type != core.CollectionTypeBase {
			t.Fatalf("%s must be an application base collection, not synthetic native Auth accounts", name)
		}
		if collection.CreateRule != nil || collection.UpdateRule != nil || collection.DeleteRule != nil {
			t.Fatalf("%s native public writes must remain locked", name)
		}
	}
}

func TestNativeNumericIdentityAndLosslessTextRoundtrip(t *testing.T) {
	app := nativeTestApp(t)
	user := core.NewRecord(applicationCollection(t, app, "feed_users"))
	user.Id = "9223372036854775807"
	user.Set("username", "native-identity")
	user.Set("created_at", "2026-10-15T00:00:00.000Z")
	if err := app.Save(user); err != nil {
		t.Fatalf("native ID must preserve full positive signed-64-bit decimal identity: %v", err)
	}
	post := core.NewRecord(applicationCollection(t, app, "feed_posts"))
	post.Id = user.Id
	post.Set("user_id", user.Id)
	body := "Ω\x00🙂\u0085"
	post.Set("body", body)
	post.Set("created_at", "2026-10-15T00:00:00.000Z")
	if err := app.Save(post); err != nil {
		t.Fatalf("native relation/text must preserve numeric IDs and NUL/Unicode: %v", err)
	}
	stored, err := app.FindRecordById("feed_posts", post.Id)
	if err != nil || stored.Id != post.Id || stored.GetString("body") != body || stored.GetString("user_id") != user.Id {
		t.Fatalf("native storage changed logical content or identity: %v", err)
	}
}

func TestNativeRelationValidationAndUniqueLikes(t *testing.T) {
	app := nativeTestApp(t)
	users := applicationCollection(t, app, "feed_users")
	posts := applicationCollection(t, app, "feed_posts")
	likes := applicationCollection(t, app, "feed_likes")
	user := core.NewRecord(users)
	user.Id = "1"
	user.Set("username", "owner")
	user.Set("created_at", "2026-10-15T00:00:00.000Z")
	if err := app.Save(user); err != nil {
		t.Fatal(err)
	}
	post := core.NewRecord(posts)
	post.Id = "1"
	post.Set("user_id", "2")
	post.Set("body", "hello")
	post.Set("created_at", "2026-10-15T00:00:00.000Z")
	if err := app.Save(post); err == nil {
		t.Fatal("native relation accepted a missing user")
	}
	post.Set("user_id", user.Id)
	if err := app.Save(post); err != nil {
		t.Fatal(err)
	}
	makeLike := func() *core.Record {
		like := core.NewRecord(likes)
		like.Set("user_id", user.Id)
		like.Set("post_id", post.Id)
		like.Set("created_at", "2026-10-15T00:00:00.000Z")
		return like
	}
	if err := app.Save(makeLike()); err != nil {
		t.Fatal(err)
	}
	if err := app.Save(makeLike()); err == nil {
		t.Fatal("native collection accepted duplicate logical user/post like")
	}
}
