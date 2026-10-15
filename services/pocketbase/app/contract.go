package main

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"math"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"
)

var errInvalidJSON = errors.New("invalid JSON")

func positiveID(text string) (int64, error) {
	if text == "" || text[0] == '0' {
		return 0, errors.New("invalid positive ID")
	}
	for _, digit := range text {
		if digit < '0' || digit > '9' {
			return 0, errors.New("invalid positive ID")
		}
	}
	value, err := strconv.ParseInt(text, 10, 64)
	if err != nil || value <= 0 {
		return 0, errors.New("invalid positive ID")
	}
	return value, nil
}

// encoding/json otherwise replaces malformed UTF-8 and unpaired UTF-16 escape
// sequences. Reject them instead; never silently alter submitted or signed data.
func strictJSON(raw []byte) (any, error) {
	if !utf8.Valid(raw) || !json.Valid(raw) {
		return nil, errInvalidJSON
	}
	inside := false
	for i := 0; i < len(raw); {
		if raw[i] == '"' {
			inside = !inside
			i++
			continue
		}
		if !inside || raw[i] != '\\' {
			i++
			continue
		}
		if i+1 >= len(raw) {
			return nil, errInvalidJSON
		}
		if raw[i+1] != 'u' {
			i += 2
			continue
		}
		if i+6 > len(raw) {
			return nil, errInvalidJSON
		}
		code, err := strconv.ParseUint(string(raw[i+2:i+6]), 16, 16)
		if err != nil {
			return nil, errInvalidJSON
		}
		if code >= 0xD800 && code <= 0xDBFF {
			if i+12 > len(raw) || raw[i+6] != '\\' || raw[i+7] != 'u' {
				return nil, errInvalidJSON
			}
			low, err := strconv.ParseUint(string(raw[i+8:i+12]), 16, 16)
			if err != nil || low < 0xDC00 || low > 0xDFFF {
				return nil, errInvalidJSON
			}
			i += 12
		} else {
			if code >= 0xDC00 && code <= 0xDFFF {
				return nil, errInvalidJSON
			}
			i += 6
		}
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.UseNumber()
	var value any
	if err := decoder.Decode(&value); err != nil {
		return nil, errInvalidJSON
	}
	var valid func(any, int) bool
	valid = func(value any, depth int) bool {
		if depth > 128 {
			return false
		}
		switch v := value.(type) {
		case json.Number:
			n, err := v.Float64()
			return err == nil && !math.IsNaN(n) && !math.IsInf(n, 0)
		case []any:
			for _, item := range v {
				if !valid(item, depth+1) {
					return false
				}
			}
		case map[string]any:
			for _, item := range v {
				if !valid(item, depth+1) {
					return false
				}
			}
		}
		return true
	}
	if !valid(value, 0) {
		return nil, errInvalidJSON
	}
	return value, nil
}

func ecmaWhitespace(r rune) bool {
	switch r {
	case '\t', '\n', '\v', '\f', '\r', ' ', 0x00a0, 0x1680, 0x2028, 0x2029, 0x202f, 0x205f, 0x3000, 0xfeff:
		return true
	}
	return r >= 0x2000 && r <= 0x200a
}

func postBody(raw []byte) (string, string) {
	value, err := strictJSON(raw)
	if err != nil {
		return "", "malformed JSON body"
	}
	object, ok := value.(map[string]any)
	if !ok {
		return "", "body is required"
	}
	body, ok := object["body"].(string)
	if !ok {
		return "", "body is required"
	}
	body = strings.TrimFunc(body, ecmaWhitespace)
	if body == "" {
		return "", "body is required"
	}
	if utf8.RuneCountInString(body) > 500 {
		return "", "body must be at most 500 characters"
	}
	return body, ""
}

type identity struct {
	ID       string
	Username string
}

func verifyIdentity(header string, key []byte) (identity, string) {
	invalid := func() (identity, string) { return identity{}, "invalid or expired token" }
	if !strings.HasPrefix(header, "Bearer ") {
		return identity{}, "missing bearer token"
	}
	parts := strings.Split(strings.TrimPrefix(header, "Bearer "), ".")
	if len(parts) != 3 {
		return invalid()
	}
	signature, err := base64.RawURLEncoding.DecodeString(parts[2])
	if err != nil {
		return invalid()
	}
	mac := hmac.New(sha256.New, key)
	_, _ = mac.Write([]byte(parts[0] + "." + parts[1]))
	if !hmac.Equal(signature, mac.Sum(nil)) {
		return invalid()
	}
	headerBytes, err := base64.RawURLEncoding.DecodeString(parts[0])
	if err != nil {
		return invalid()
	}
	headerValue, err := strictJSON(headerBytes)
	if err != nil {
		return invalid()
	}
	headerObject, ok := headerValue.(map[string]any)
	if !ok || headerObject["alg"] != "HS256" {
		return invalid()
	}
	payload, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return invalid()
	}
	value, err := strictJSON(payload)
	if err != nil {
		return invalid()
	}
	claims, ok := value.(map[string]any)
	if !ok {
		return invalid()
	}
	exp, ok := claims["exp"].(json.Number)
	if !ok {
		return invalid()
	}
	expiry, err := exp.Float64()
	if err != nil || expiry <= float64(time.Now().UnixNano())/1e9 {
		return invalid()
	}
	if nbf, exists := claims["nbf"]; exists {
		number, ok := nbf.(json.Number)
		if !ok {
			return invalid()
		}
		notBefore, err := number.Float64()
		if err != nil || notBefore > float64(time.Now().UnixNano())/1e9 {
			return invalid()
		}
	}
	sub, ok := claims["sub"].(string)
	if !ok {
		return identity{}, "invalid token payload"
	}
	if _, err := positiveID(sub); err != nil {
		return identity{}, "invalid token payload"
	}
	username, ok := claims["username"].(string)
	if !ok {
		return identity{}, "invalid token payload"
	}
	return identity{ID: sub, Username: username}, ""
}
