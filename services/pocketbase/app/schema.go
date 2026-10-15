package main

import (
	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
	"github.com/pocketbase/pocketbase/tools/types"
)

const sequenceID = "feedpostcounter"

func init() {
	m.Register(installCollections, nil, "1792022400_feed_collections.go")
}

// PocketBase's supported customizable Text primary key preserves each original
// integer identity as its exact decimal string. Numeric ordering is explicit in
// the equivalent baseline index; no float64 Number field rounds 64-bit IDs.
func numericCollection(name string) *core.Collection {
	collection := core.NewBaseCollection(name)
	id := collection.Fields.GetByName("id").(*core.TextField)
	id.Min = 1
	id.Max = 19
	id.Pattern = "^[1-9][0-9]{0,18}$"
	id.AutogeneratePattern = ""
	collection.ListRule = types.Pointer("")
	collection.ViewRule = types.Pointer("")
	// nil native Create/Update/Delete rules keep direct client writes locked.
	return collection
}

func timestampField() *core.TextField {
	return &core.TextField{Name: "created_at", Required: true, Max: 24, Pattern: `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$`}
}

func installCollections(app core.App) error {
	users := numericCollection("feed_users")
	users.Fields.Add(&core.TextField{Name: "username", Required: true, Max: 5000}, timestampField())
	users.AddIndex("feed_users_username_unique", true, "username", "")
	if err := app.Save(users); err != nil {
		return err
	}

	posts := numericCollection("feed_posts")
	posts.Fields.Add(
		&core.RelationField{Name: "user_id", CollectionId: users.Id, Required: true, MaxSelect: 1},
		&core.TextField{Name: "body", Required: true, Min: 1, Max: 500},
		timestampField(),
	)
	posts.AddIndex("posts_created_at_id_idx", false, "created_at DESC, CAST(id AS INTEGER) DESC", "")
	posts.AddIndex("posts_user_id_idx", false, "user_id", "")
	if err := app.Save(posts); err != nil {
		return err
	}

	likes := core.NewBaseCollection("feed_likes")
	likes.ListRule = types.Pointer("")
	likes.ViewRule = types.Pointer("")
	likes.Fields.Add(
		&core.RelationField{Name: "user_id", CollectionId: users.Id, Required: true, MaxSelect: 1},
		&core.RelationField{Name: "post_id", CollectionId: posts.Id, Required: true, MaxSelect: 1},
		timestampField(),
	)
	// Native records additionally require their ordinary generated record ID.
	// This unique index retains the original logical compound like identity.
	likes.AddIndex("feed_likes_user_post_unique", true, "user_id, post_id", "")
	likes.AddIndex("likes_post_id_idx", false, "post_id", "")
	if err := app.Save(likes); err != nil {
		return err
	}

	// Persistent ID-allocation metadata only, not a response/like-count cache.
	// Read/update this exact scalar and save the new post in RunInTransaction.
	sequence := core.NewBaseCollection("feed_sequences")
	sequence.Fields.Add(&core.TextField{Name: "last_id", Required: true, Max: 19, Pattern: "^(0|[1-9][0-9]{0,18})$"})
	if err := app.Save(sequence); err != nil {
		return err
	}
	record := core.NewRecord(sequence)
	record.Id = sequenceID
	record.Set("last_id", "0")
	return app.Save(record)
}
