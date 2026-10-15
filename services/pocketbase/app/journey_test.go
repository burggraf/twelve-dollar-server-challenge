package main

import (
	"encoding/json"
	"net/http/httptest"
	"strconv"
	"strings"
	"sync"
	"testing"

	"github.com/pocketbase/pocketbase/core"
)

func seedNativeHTTP(t *testing.T, app core.App, posts int) {
	t.Helper()
	user := core.NewRecord(applicationCollection(t, app, "feed_users"))
	user.Id = "1"
	user.Set("username", "owner")
	user.Set("created_at", "2026-10-15T00:00:00.000Z")
	if err := app.Save(user); err != nil {
		t.Fatal(err)
	}
	collection := applicationCollection(t, app, "feed_posts")
	for i := 1; i <= posts; i++ {
		record := core.NewRecord(collection)
		record.Id = strconv.Itoa(i)
		record.Set("user_id", "1")
		record.Set("body", "seed")
		record.Set("created_at", "2026-10-15T00:00:00.000Z")
		if err := app.Save(record); err != nil {
			t.Fatal(err)
		}
	}
	sequence, err := app.FindRecordById("feed_sequences", sequenceID)
	if err != nil {
		t.Fatal(err)
	}
	sequence.Set("last_id", strconv.Itoa(posts))
	if err := app.Save(sequence); err != nil {
		t.Fatal(err)
	}
}

func TestNativeHTTPCommittedJourneyAndNumericOrder(t *testing.T) {
	app, handler := nativeTestHandler(t)
	seedNativeHTTP(t, app, 23)
	feed := nativeRequest(handler, "GET", "/feed", "", "")
	if feed.Code != 200 {
		t.Fatalf("native feed route missing/failed: %d %s", feed.Code, feed.Body.String())
	}
	var result struct {
		Posts []struct {
			ID int64 `json:"id"`
		} `json:"posts"`
	}
	if err := json.Unmarshal(feed.Body.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	if len(result.Posts) != 20 {
		t.Fatalf("expected20posts,got%d", len(result.Posts))
	}
	for i, p := range result.Posts {
		if p.ID != int64(23-i) {
			t.Fatalf("native Text IDs sorted lexically instead of numerically: %v", result.Posts)
		}
	}
	body := "\u0085Ω\x00🙂"
	raw, _ := json.Marshal(map[string]string{"body": "\ufeff\u00a0" + body + "\u2029"})
	created := nativeRequest(handler, "POST", "/posts", string(raw), "Bearer "+validTestToken(t))
	if created.Code != 201 {
		t.Fatalf("native committed create failed: %d %s", created.Code, created.Body.String())
	}
	var post struct {
		Post struct {
			ID        int64  `json:"id"`
			Body      string `json:"body"`
			Author    string `json:"author"`
			LikeCount int64  `json:"like_count"`
		} `json:"post"`
	}
	if err := json.Unmarshal(created.Body.Bytes(), &post); err != nil {
		t.Fatal(err)
	}
	if post.Post.ID != 24 || post.Post.Body != body || post.Post.Author != "owner" || post.Post.LikeCount != 0 {
		t.Fatalf("created post changed identity/content: %s", created.Body.String())
	}
	read := nativeRequest(handler, "GET", "/posts/24", "", "")
	if read.Code != 200 || read.Body.String() != created.Body.String() {
		t.Fatalf("acknowledged native post not immediately readable: %d %s", read.Code, read.Body.String())
	}
	first := nativeRequest(handler, "POST", "/posts/24/like", "", "Bearer "+validTestToken(t))
	repeat := nativeRequest(handler, "POST", "/posts/24/like", "", "Bearer "+validTestToken(t))
	if first.Code != 201 || strings.TrimSpace(first.Body.String()) != `{"liked":true,"already_liked":false,"post_id":24}` || repeat.Code != 200 || strings.TrimSpace(repeat.Body.String()) != `{"liked":true,"already_liked":true,"post_id":24}` {
		t.Fatalf("native like is not exact/idempotent: %d %s %d %s", first.Code, first.Body.String(), repeat.Code, repeat.Body.String())
	}
	read = nativeRequest(handler, "GET", "/posts/24", "", "")
	if !strings.Contains(read.Body.String(), `"like_count":1`) {
		t.Fatalf("request-time native count incorrect: %s", read.Body.String())
	}
	for _, collection := range []string{"feed_posts", "feed_likes", "feed_sequences"} {
		response := nativeRequest(handler, "POST", "/api/collections/"+collection+"/records", `{}`, "Bearer "+validTestToken(t))
		if response.Code >= 200 && response.Code < 300 {
			t.Fatalf("compatibility token bypassed locked native CRUD for%s", collection)
		}
	}
}

func TestNativeHTTPConcurrentAtomicIDsAndLikes(t *testing.T) {
	app, handler := nativeTestHandler(t)
	seedNativeHTTP(t, app, 1)
	token := "Bearer " + validTestToken(t)
	var wg sync.WaitGroup
	responses := make([]*httptest.ResponseRecorder, 32)
	for i := range responses {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			responses[i] = nativeRequest(handler, "POST", "/posts/1/like", "", token)
		}(i)
	}
	wg.Wait()
	first := 0
	for _, r := range responses {
		if r.Code == 201 {
			first++
		} else if r.Code != 200 {
			t.Fatalf("concurrent like failed: %d %s", r.Code, r.Body.String())
		}
	}
	if first != 1 {
		t.Fatalf("exactly one new native like required,got%d", first)
	}
	for i := range responses {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			responses[i] = nativeRequest(handler, "POST", "/posts", `{"body":"parallel"}`, token)
		}(i)
	}
	wg.Wait()
	ids := map[int64]bool{}
	for _, r := range responses {
		if r.Code != 201 {
			t.Fatalf("concurrent create failed: %d %s", r.Code, r.Body.String())
		}
		var body struct {
			Post struct {
				ID int64 `json:"id"`
			} `json:"post"`
		}
		if err := json.Unmarshal(r.Body.Bytes(), &body); err != nil {
			t.Fatal(err)
		}
		if ids[body.Post.ID] {
			t.Fatal("duplicate native public ID")
		}
		ids[body.Post.ID] = true
	}
	if len(ids) != 32 {
		t.Fatal("missing committed native posts")
	}
}
