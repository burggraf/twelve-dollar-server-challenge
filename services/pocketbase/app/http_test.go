package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
)

const testSecret = "pocketbase-contract-test-only-not-a-runtime-key"

func nativeTestHandler(t *testing.T) (core.App, http.Handler) {
	t.Helper()
	t.Setenv("JWT_SECRET", testSecret)
	app := nativeTestApp(t)
	router, err := apis.NewRouter(app)
	if err != nil {
		t.Fatal(err)
	}
	if err := app.OnServe().Trigger(&core.ServeEvent{App: app, Router: router}, func(e *core.ServeEvent) error { return nil }); err != nil {
		t.Fatal(err)
	}
	handler, err := router.BuildMux()
	if err != nil {
		t.Fatal(err)
	}
	return app, handler
}

func signedTestToken(t *testing.T, claims map[string]any) string {
	t.Helper()
	header := base64.RawURLEncoding.EncodeToString([]byte(`{"alg":"HS256","typ":"JWT"}`))
	payload, err := json.Marshal(claims)
	if err != nil {
		t.Fatal(err)
	}
	text := header + "." + base64.RawURLEncoding.EncodeToString(payload)
	mac := hmac.New(sha256.New, []byte(testSecret))
	_, _ = mac.Write([]byte(text))
	return text + "." + base64.RawURLEncoding.EncodeToString(mac.Sum(nil))
}

func validTestToken(t *testing.T) string {
	return signedTestToken(t, map[string]any{"sub": "1", "username": "owner", "exp": time.Now().Unix() + 3600})
}

func nativeRequest(handler http.Handler, method, path, body, auth string) *httptest.ResponseRecorder {
	request := httptest.NewRequest(method, path, strings.NewReader(body))
	request.Header.Set("Content-Type", "application/json")
	if auth != "" {
		request.Header.Set("Authorization", auth)
	}
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)
	return response
}

func TestNativeHTTPHealthAndExactErrorContract(t *testing.T) {
	_, handler := nativeTestHandler(t)
	response := nativeRequest(handler, "GET", "/health", "", "")
	if response.Code != 200 {
		t.Fatalf("native feed health route missing or failed: status=%d body=%s", response.Code, response.Body.String())
	}
	var health struct {
		Status string `json:"status"`
		DB     string `json:"db"`
		Uptime int64  `json:"uptime_s"`
	}
	if err := json.Unmarshal(response.Body.Bytes(), &health); err != nil || health.Status != "ok" || health.DB != "ok" || health.Uptime < 0 {
		t.Fatalf("invalid storage health: %v %s", err, response.Body.String())
	}
	token := "Bearer " + validTestToken(t)
	cases := []struct {
		method, path, body, auth string
		status                   int
		want                     string
	}{
		{"GET", "/unknown", "", "", 404, `{"error":"not found"}`},
		{"GET", "/posts/abc", "", "", 400, `{"error":"invalid post id"}`},
		{"GET", "/posts/0", "", "", 400, `{"error":"invalid post id"}`},
		{"GET", "/posts/9223372036854775808", "", "", 400, `{"error":"invalid post id"}`},
		{"GET", "/posts/9223372036854775807", "", "", 404, `{"error":"post not found"}`},
		{"POST", "/posts/abc/like", "{", "", 401, `{"error":"missing bearer token"}`},
		{"POST", "/posts/abc/like", "", token, 400, `{"error":"invalid post id"}`},
		{"POST", "/posts", "{", "", 401, `{"error":"missing bearer token"}`},
		{"POST", "/posts", "{}", "Bearer broken", 401, `{"error":"invalid or expired token"}`},
		{"POST", "/posts", "{", token, 400, `{"error":"malformed JSON body"}`},
		{"POST", "/posts", `{"body":true}`, token, 400, `{"error":"body is required"}`},
		{"POST", "/posts", `null`, token, 400, `{"error":"body is required"}`},
		{"POST", "/posts", `{"body":"\ufeff\u00a0\u2029"}`, token, 400, `{"error":"body is required"}`},
		{"POST", "/posts", `{"body":"\ud800"}`, token, 400, `{"error":"malformed JSON body"}`},
		{"POST", "/posts", `{"body":"` + string([]byte{0xff}) + `"}`, token, 400, `{"error":"malformed JSON body"}`},
		{"POST", "/posts", `{"body":"ok","extra":1e400}`, token, 400, `{"error":"malformed JSON body"}`},
		{"POST", "/posts", `{"body":"` + strings.Repeat("😀", 501) + `"}`, token, 400, `{"error":"body must be at most 500 characters"}`},
	}
	for _, c := range cases {
		t.Run(c.method+c.path+c.want, func(t *testing.T) {
			got := nativeRequest(handler, c.method, c.path, c.body, c.auth)
			if got.Code != c.status || strings.TrimSpace(got.Body.String()) != c.want {
				t.Fatalf("want%d %s; got%d %s", c.status, c.want, got.Code, got.Body.String())
			}
		})
	}
}

func TestNativeHTTPStrictSignedClaims(t *testing.T) {
	_, handler := nativeTestHandler(t)
	for _, sub := range []any{nil, true, 1, "0", "01", "-1", "1.0", "1e0", " 1", "9223372036854775808"} {
		token := signedTestToken(t, map[string]any{"sub": sub, "username": "owner", "exp": time.Now().Unix() + 3600})
		got := nativeRequest(handler, "POST", "/posts", `{"body":"reject"}`, "Bearer "+token)
		if got.Code != 401 || strings.TrimSpace(got.Body.String()) != `{"error":"invalid token payload"}` {
			t.Fatalf("invalid signed subject accepted/misclassified: %v status%d %s", sub, got.Code, got.Body.String())
		}
	}
	for _, exp := range []any{nil, true, "future", 0} {
		token := signedTestToken(t, map[string]any{"sub": "1", "username": "owner", "exp": exp})
		got := nativeRequest(handler, "POST", "/posts", `{"body":"reject"}`, "Bearer "+token)
		if got.Code != 401 || strings.TrimSpace(got.Body.String()) != `{"error":"invalid or expired token"}` {
			t.Fatalf("invalid expiry accepted/misclassified: status%d %s", got.Code, got.Body.String())
		}
	}
}
