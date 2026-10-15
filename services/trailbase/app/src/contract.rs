use base64::{Engine, engine::general_purpose::URL_SAFE_NO_PAD};
use hmac::{Hmac, Mac};
use serde_json::Value;
use sha2::Sha256;

pub fn positive_id(raw: &str) -> Option<i64> {
    if raw.is_empty() || !raw.bytes().all(|c| c.is_ascii_digit()) {
        return None;
    }
    raw.parse::<i64>().ok().filter(|id| *id > 0)
}

pub fn body(value: Value) -> Result<String, &'static str> {
    let text = value
        .get("body")
        .and_then(Value::as_str)
        .ok_or("body is required")?;
    // ECMAScript WhiteSpace + LineTerminator, matching the reference trim().
    let text = text.trim_matches(|c| {
        matches!(c,
        '\u{0009}'..='\u{000d}' | '\u{0020}' | '\u{00a0}' | '\u{1680}' |
        '\u{2000}'..='\u{200a}' | '\u{2028}' | '\u{2029}' | '\u{202f}' |
        '\u{205f}' | '\u{3000}' | '\u{feff}')
    });
    if text.is_empty() {
        return Err("body is required");
    }
    if text.chars().count() > 500 {
        return Err("body must be at most 500 characters");
    }
    Ok(text.to_owned())
}

pub fn authenticate(
    header: Option<&str>,
    secret: &[u8],
    now: f64,
) -> Result<(i64, String), &'static str> {
    const INVALID: &str = "invalid or expired token";
    let token = header
        .and_then(|s| s.strip_prefix("Bearer "))
        .ok_or("missing bearer token")?;
    let parts: Vec<_> = token.split('.').collect();
    if parts.len() != 3 {
        return Err(INVALID);
    }
    let decode = |part| URL_SAFE_NO_PAD.decode(part).map_err(|_| INVALID);
    let head: Value = serde_json::from_slice(&decode(parts[0])?).map_err(|_| INVALID)?;
    if head.get("alg").and_then(Value::as_str) != Some("HS256") {
        return Err(INVALID);
    }
    let mut mac = Hmac::<Sha256>::new_from_slice(secret).map_err(|_| INVALID)?;
    mac.update(format!("{}.{}", parts[0], parts[1]).as_bytes());
    mac.verify_slice(&decode(parts[2])?).map_err(|_| INVALID)?;
    let payload: Value = serde_json::from_slice(&decode(parts[1])?).map_err(|_| INVALID)?;
    let exp = payload.get("exp").and_then(Value::as_f64).ok_or(INVALID)?;
    if !exp.is_finite() || now >= exp {
        return Err(INVALID);
    }
    if let Some(nbf) = payload.get("nbf") {
        if now < nbf.as_f64().ok_or(INVALID)? {
            return Err(INVALID);
        }
    }
    let id = payload
        .get("sub")
        .and_then(Value::as_str)
        .and_then(positive_id)
        .ok_or("invalid token payload")?;
    let username = payload
        .get("username")
        .and_then(Value::as_str)
        .ok_or("invalid token payload")?;
    Ok((id, username.to_owned()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use base64::{Engine, engine::general_purpose::URL_SAFE_NO_PAD};
    use hmac::{Hmac, Mac};
    use serde_json::json;
    use sha2::Sha256;

    fn sign(header: Value, payload: Value) -> String {
        let text = format!(
            "{}.{}",
            URL_SAFE_NO_PAD.encode(header.to_string()),
            URL_SAFE_NO_PAD.encode(payload.to_string())
        );
        let mut mac = Hmac::<Sha256>::new_from_slice(b"test-key").unwrap();
        mac.update(text.as_bytes());
        format!(
            "Bearer {}.{}",
            text,
            URL_SAFE_NO_PAD.encode(mac.finalize().into_bytes())
        )
    }

    #[test]
    fn validates_decimal_positive_ids() {
        assert_eq!(positive_id("1"), Some(1));
        assert_eq!(positive_id("001"), Some(1));
        for value in [
            "",
            "0",
            "-1",
            "+1",
            "1.0",
            "1e0",
            " 1",
            "١",
            "999999999999999999999",
        ] {
            assert_eq!(positive_id(value), None, "{value}");
        }
    }

    #[test]
    fn trims_ecmascript_whitespace_and_counts_unicode_scalars() {
        assert_eq!(
            body(json!({"body": "\u{feff}\u{a0}café 😀\u{2029}"})),
            Ok("café 😀".into())
        );
        assert_eq!(
            body(json!({"body": "😀".repeat(500)})),
            Ok("😀".repeat(500))
        );
        assert_eq!(
            body(json!({"body": "😀".repeat(501)})),
            Err("body must be at most 500 characters")
        );
        // U+0085 is Rust whitespace, but not ECMAScript trim whitespace.
        assert_eq!(body(json!({"body": "\u{85}"})), Ok("\u{85}".into()));
        for value in [
            json!({}),
            json!([]),
            Value::Null,
            json!({"body": 1}),
            json!({"body": " \u{feff}"}),
        ] {
            assert_eq!(body(value), Err("body is required"));
        }
    }

    #[test]
    fn verifies_each_signature_and_expiry_before_payload() {
        let payload = json!({"sub": "1", "username": "name from token", "exp": 200});
        let header = json!({"alg": "HS256"});
        let auth = sign(header.clone(), payload.clone());
        assert_eq!(
            authenticate(Some(&auth), b"test-key", 100.0),
            Ok((1, "name from token".into()))
        );
        assert_eq!(
            authenticate(Some(&auth), b"wrong-key", 100.0),
            Err("invalid or expired token")
        );
        assert_eq!(
            authenticate(Some(&auth), b"test-key", 200.0),
            Err("invalid or expired token")
        );
        assert_eq!(
            authenticate(None, b"test-key", 100.0),
            Err("missing bearer token")
        );
        assert_eq!(
            authenticate(Some("Basic abc"), b"test-key", 100.0),
            Err("missing bearer token")
        );
        for header in [json!({"alg":"none"}), json!({"alg":"HS512"}), json!([])] {
            assert_eq!(
                authenticate(Some(&sign(header, payload.clone())), b"test-key", 100.0),
                Err("invalid or expired token")
            );
        }
        for payload in [
            json!({"sub":"abc","username":"x","exp":200}),
            json!({"sub":1,"username":"x","exp":200}),
            json!({"sub":"1","exp":200}),
        ] {
            assert_eq!(
                authenticate(Some(&sign(header.clone(), payload)), b"test-key", 100.0),
                Err("invalid token payload")
            );
        }
        for payload in [
            json!({"sub":"1","username":"x"}),
            json!({"sub":"1","username":"x","exp":true}),
        ] {
            assert_eq!(
                authenticate(Some(&sign(header.clone(), payload)), b"test-key", 100.0),
                Err("invalid or expired token")
            );
        }
    }
}
