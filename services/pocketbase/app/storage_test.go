package main

import (
	"net/http"
	"strings"
	"testing"

	"github.com/pocketbase/dbx"
)

func TestNativeStartupAppliesRegisteredApplicationMigrations(t *testing.T) {
	app := newFeedApp(t.TempDir())
	if err := app.Bootstrap(); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = app.ClearBootstrap() })
	if _, err := app.FindCollectionByNameOrId("feed_posts"); err != nil {
		t.Fatalf("normal native bootstrap omitted registered application schema: %v", err)
	}
}

func TestNativeStorageFailureAndTransactionalRollback(t *testing.T) {
	app, handler := nativeTestHandler(t)
	seedNativeHTTP(t, app, 1)
	sequence, err := app.FindRecordById("feed_sequences", sequenceID)
	if err != nil {
		t.Fatal(err)
	}
	sequence.Set("last_id", "0")
	if err := app.Save(sequence); err != nil {
		t.Fatal(err)
	}
	// Force an actual native primary-key collision after allocation was saved
	// inside the transaction. The allocation must roll back with the failed post.
	failed := nativeRequest(handler, "POST", "/posts", `{"body":"collision"}`, "Bearer "+validTestToken(t))
	if failed.Code != 500 || strings.TrimSpace(failed.Body.String()) != `{"error":"internal server error"}` {
		t.Fatalf("failed transaction not sanitized: %d %s", failed.Code, failed.Body.String())
	}
	sequence, err = app.FindRecordById("feed_sequences", sequenceID)
	if err != nil || sequence.GetString("last_id") != "0" {
		t.Fatalf("native failed post committed its key allocation: %v", err)
	}
	if err := app.ConcurrentDB().(*dbx.DB).Close(); err != nil {
		t.Fatal(err)
	}
	if err := app.NonconcurrentDB().(*dbx.DB).Close(); err != nil {
		t.Fatal(err)
	}
	health := nativeRequest(handler, "GET", "/health", "", "")
	if health.Code != http.StatusServiceUnavailable || strings.TrimSpace(health.Body.String()) != `{"status":"degraded","db":"unreachable","error":"database unavailable"}` {
		t.Fatalf("real closed native storage did not degrade/sanitize health: %d %s", health.Code, health.Body.String())
	}
	failed = nativeRequest(handler, "POST", "/posts", `{"body":"unavailable"}`, "Bearer "+validTestToken(t))
	if failed.Code != 500 || strings.TrimSpace(failed.Body.String()) != `{"error":"internal server error"}` {
		t.Fatalf("closed native storage write not sanitized: %d %s", failed.Code, failed.Body.String())
	}
}
