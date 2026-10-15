package main

import (
	"database/sql"
	"errors"
	"io"
	"math"
	"net/http"
	"strconv"
	"time"

	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase/core"
)

type feedPost struct {
	ID        int64  `db:"id" json:"id"`
	Body      string `db:"body" json:"body"`
	CreatedAt string `db:"created_at" json:"created_at"`
	Author    string `db:"author" json:"author"`
	LikeCount int64  `db:"like_count" json:"like_count"`
}

const postQuery = `SELECT CAST(p.id AS INTEGER) AS id,p.body,p.created_at,u.username AS author,
 (SELECT COUNT(*) FROM feed_likes l WHERE l.post_id=p.id) AS like_count
 FROM feed_posts p JOIN feed_users u ON u.id=p.user_id`

var errMissingPost = errors.New("post not found")

func apiError(e *core.RequestEvent, status int, message string) error {
	return e.JSON(status, struct {
		Error string `json:"error"`
	}{message})
}

func registerFeedRoutes(serve *core.ServeEvent, key []byte, started time.Time) {
	serve.Router.GET("/health", func(e *core.RequestEvent) error {
		var result struct {
			Value int `db:"value"`
		}
		if !e.App.IsBootstrapped() || e.App.DB().NewQuery("SELECT 1 AS value").One(&result) != nil || result.Value != 1 {
			return e.JSON(503, struct {
				Status string `json:"status"`
				DB     string `json:"db"`
				Error  string `json:"error"`
			}{"degraded", "unreachable", "database unavailable"})
		}
		return e.JSON(200, struct {
			Status string `json:"status"`
			DB     string `json:"db"`
			Uptime int64  `json:"uptime_s"`
		}{"ok", "ok", int64(time.Since(started) / time.Second)})
	})
	serve.Router.GET("/feed", func(e *core.RequestEvent) error {
		posts := []feedPost{}
		if err := e.App.DB().NewQuery(postQuery + " ORDER BY p.created_at DESC,CAST(p.id AS INTEGER) DESC LIMIT 20").All(&posts); err != nil {
			return apiError(e, 500, "internal server error")
		}
		return e.JSON(200, struct {
			Posts []feedPost `json:"posts"`
		}{posts})
	})
	serve.Router.GET("/posts/{id}", func(e *core.RequestEvent) error {
		text := e.Request.PathValue("id")
		if _, err := positiveID(text); err != nil {
			return apiError(e, 400, "invalid post id")
		}
		var post feedPost
		err := e.App.DB().NewQuery(postQuery + " WHERE p.id={:id}").Bind(dbx.Params{"id": text}).One(&post)
		if errors.Is(err, sql.ErrNoRows) {
			return apiError(e, 404, "post not found")
		}
		if err != nil {
			return apiError(e, 500, "internal server error")
		}
		return e.JSON(200, struct {
			Post feedPost `json:"post"`
		}{post})
	})
	serve.Router.POST("/posts", func(e *core.RequestEvent) error {
		who, message := verifyIdentity(e.Request.Header.Get("Authorization"), key)
		if message != "" {
			return apiError(e, 401, message)
		}
		raw, err := io.ReadAll(io.LimitReader(e.Request.Body, 1024*1024+1))
		if err != nil || len(raw) > 1024*1024 {
			return apiError(e, 400, "malformed JSON body")
		}
		body, message := postBody(raw)
		if message != "" {
			return apiError(e, 400, message)
		}
		post, err := createPost(e.App, who, body)
		if err != nil {
			return apiError(e, 500, "internal server error")
		}
		return e.JSON(201, struct {
			Post feedPost `json:"post"`
		}{post})
	})
	serve.Router.POST("/posts/{id}/like", func(e *core.RequestEvent) error {
		who, message := verifyIdentity(e.Request.Header.Get("Authorization"), key)
		if message != "" {
			return apiError(e, 401, message)
		}
		text := e.Request.PathValue("id")
		id, err := positiveID(text)
		if err != nil {
			return apiError(e, 400, "invalid post id")
		}
		already, err := likePost(e.App, who.ID, text)
		if errors.Is(err, errMissingPost) {
			return apiError(e, 404, "post not found")
		}
		if err != nil {
			return apiError(e, 500, "internal server error")
		}
		status := http.StatusCreated
		if already {
			status = http.StatusOK
		}
		return e.JSON(status, struct {
			Liked   bool  `json:"liked"`
			Already bool  `json:"already_liked"`
			PostID  int64 `json:"post_id"`
		}{true, already, id})
	})
	serve.Router.Route("", "/", func(e *core.RequestEvent) error { return apiError(e, 404, "not found") })
}

func createPost(app core.App, who identity, body string) (feedPost, error) {
	var result feedPost
	err := app.RunInTransaction(func(tx core.App) error {
		// All writes, including relation validation and key allocation, use the
		// transactional native App, never a second connection or deferred batch.
		if _, err := tx.FindRecordById("feed_users", who.ID); err != nil {
			return err
		}
		sequence, err := tx.FindRecordById("feed_sequences", sequenceID)
		if err != nil {
			return err
		}
		last, err := strconv.ParseInt(sequence.GetString("last_id"), 10, 64)
		if err != nil || last < 0 || last == math.MaxInt64 {
			return errors.New("invalid or exhausted post identity")
		}
		next := last + 1
		sequence.Set("last_id", strconv.FormatInt(next, 10))
		if err := tx.Save(sequence); err != nil {
			return err
		}
		collection, err := tx.FindCollectionByNameOrId("feed_posts")
		if err != nil {
			return err
		}
		post := core.NewRecord(collection)
		post.Id = strconv.FormatInt(next, 10)
		created := time.Now().UTC().Format("2006-01-02T15:04:05.000Z")
		post.Set("user_id", who.ID)
		post.Set("body", body)
		post.Set("created_at", created)
		if err := tx.Save(post); err != nil {
			return err
		}
		result = feedPost{ID: next, Body: body, CreatedAt: created, Author: who.Username, LikeCount: 0}
		return nil
	})
	return result, err
}

func likePost(app core.App, userID, postID string) (bool, error) {
	already := false
	err := app.RunInTransaction(func(tx core.App) error {
		if _, err := tx.FindRecordById("feed_posts", postID); err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				return errMissingPost
			}
			return err
		}
		_, err := tx.FindFirstRecordByFilter("feed_likes", "user_id={:user} && post_id={:post}", dbx.Params{"user": userID, "post": postID})
		if err == nil {
			already = true
			return nil
		}
		if !errors.Is(err, sql.ErrNoRows) {
			return err
		}
		collection, err := tx.FindCollectionByNameOrId("feed_likes")
		if err != nil {
			return err
		}
		record := core.NewRecord(collection)
		record.Set("user_id", userID)
		record.Set("post_id", postID)
		record.Set("created_at", time.Now().UTC().Format("2006-01-02T15:04:05.000Z"))
		return tx.Save(record)
	})
	return already, err
}
