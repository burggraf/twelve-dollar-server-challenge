//! Runs inside TrailBase's Wasmtime runtime; all storage calls go through its guest SDK.
use crate::contract;
use serde::Serialize;
use std::time::{SystemTime, UNIX_EPOCH};
use trailbase_wasm::db::{self, Transaction, Value};
use trailbase_wasm::http::{HttpRoute, IntoBody, Request, Response, routing};
use trailbase_wasm::{Guest, export};

const SELECT_POST: &str = "SELECT p.id,p.body,p.created_at,u.username,(SELECT count(*) FROM likes l WHERE l.post_id=p.id) FROM posts p JOIN users u ON u.id=p.user_id";
type Reply = Result<Response, Response>;

#[derive(Serialize)]
struct Post {
    id: i64,
    body: String,
    created_at: String,
    author: String,
    like_count: i64,
}
#[derive(Serialize)]
struct PostResult {
    post: Post,
}
#[derive(Serialize)]
struct Feed {
    posts: Vec<Post>,
}
#[derive(Serialize)]
struct ErrorBody<'a> {
    error: &'a str,
}
#[derive(Serialize)]
struct Like {
    liked: bool,
    already_liked: bool,
    post_id: i64,
}
#[derive(Serialize)]
struct Health {
    status: &'static str,
    db: &'static str,
    uptime_s: u64,
}
#[derive(Serialize)]
struct Degraded {
    status: &'static str,
    db: &'static str,
    error: &'static str,
}

fn json(status: u16, body: impl Serialize) -> Response {
    Response::builder()
        .status(status)
        .header("content-type", "application/json")
        .body(
            serde_json::to_vec(&body)
                .expect("serializable response")
                .into_body(),
        )
        .expect("valid static headers/status")
}
fn error(status: u16, message: &str) -> Response {
    json(status, ErrorBody { error: message })
}
fn internal<E>(_error: E) -> Response {
    error(500, "internal server error")
}
fn now() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_secs_f64()
}
fn authenticate(req: &Request) -> Result<(i64, String), Response> {
    // The WASI sandbox intentionally does not inherit host environment variables.
    let secret = trailbase_wasm::fs::read_file("/jwt-secret").map_err(internal)?;
    contract::authenticate(
        req.header("authorization").and_then(|h| h.to_str().ok()),
        &secret,
        now(),
    )
    .map_err(|message| error(401, message))
}
fn id(req: &Request) -> Result<i64, Response> {
    contract::positive_id(req.path_param("id").unwrap_or_default())
        .ok_or_else(|| error(400, "invalid post id"))
}
fn integer(value: Value) -> Result<i64, Response> {
    if let Value::Integer(v) = value {
        Ok(v)
    } else {
        Err(internal(()))
    }
}
fn text(value: Value) -> Result<String, Response> {
    if let Value::Text(v) = value {
        Ok(v)
    } else {
        Err(internal(()))
    }
}
fn post(row: Vec<Value>) -> Result<Post, Response> {
    let [id, body, created_at, author, like_count]: [Value; 5] =
        row.try_into().map_err(internal)?;
    Ok(Post {
        id: integer(id)?,
        body: text(body)?,
        created_at: text(created_at)?,
        author: text(author)?,
        like_count: integer(like_count)?,
    })
}

async fn health(_: Request) -> Response {
    // Probe application storage as well as the connection. Failure contains no internal SQL/secrets.
    if db::query("SELECT 1 FROM users LIMIT 1", []).await.is_err() {
        return json(
            503,
            Degraded {
                status: "degraded",
                db: "unreachable",
                error: "storage probe failed",
            },
        );
    }
    let start = trailbase_wasm::fs::read_file("/started-at")
        .ok()
        .and_then(|v| String::from_utf8(v).ok())
        .and_then(|v| v.trim().parse::<u64>().ok())
        .unwrap_or(now() as u64);
    json(
        200,
        Health {
            status: "ok",
            db: "ok",
            uptime_s: (now() as u64).saturating_sub(start),
        },
    )
}
async fn feed(_: Request) -> Reply {
    let rows = db::query(
        format!("{SELECT_POST} ORDER BY p.created_at DESC,p.id DESC LIMIT 20"),
        [],
    )
    .await
    .map_err(internal)?;
    Ok(json(
        200,
        Feed {
            posts: rows.into_iter().map(post).collect::<Result<_, _>>()?,
        },
    ))
}
async fn detail(req: Request) -> Reply {
    let rows = db::query(
        format!("{SELECT_POST} WHERE p.id=?"),
        [Value::Integer(id(&req)?)],
    )
    .await
    .map_err(internal)?;
    let row = rows
        .into_iter()
        .next()
        .ok_or_else(|| error(404, "post not found"))?;
    Ok(json(200, PostResult { post: post(row)? }))
}
async fn create(mut req: Request) -> Reply {
    let (user_id, author) = authenticate(&req)?;
    let bytes = req
        .body()
        .bytes()
        .await
        .map_err(|_| error(400, "malformed JSON body"))?;
    let value = serde_json::from_slice(&bytes).map_err(|_| error(400, "malformed JSON body"))?;
    let body = contract::body(value).map_err(|message| error(400, message))?;
    let mut tx = Transaction::begin().map_err(internal)?;
    let rows = tx
        .query(
            "INSERT INTO posts(user_id,body) VALUES(?,?) RETURNING id,created_at",
            &[Value::Integer(user_id), Value::Text(body.clone())],
        )
        .map_err(internal)?;
    let [new_id, created_at]: [Value; 2] = rows
        .into_iter()
        .next()
        .ok_or_else(|| internal(()))?
        .try_into()
        .map_err(internal)?;
    let result = Post {
        id: integer(new_id)?,
        body,
        created_at: text(created_at)?,
        author,
        like_count: 0,
    };
    // Explicit commit precedes the response, including stepping RETURNING to completion.
    tx.commit().map_err(internal)?;
    Ok(json(201, PostResult { post: result }))
}
async fn like(req: Request) -> Reply {
    let (user_id, _) = authenticate(&req)?;
    let post_id = id(&req)?;
    let mut tx = Transaction::begin().map_err(internal)?;
    if tx
        .query("SELECT 1 FROM posts WHERE id=?", &[Value::Integer(post_id)])
        .map_err(internal)?
        .is_empty()
    {
        return Err(error(404, "post not found"));
    }
    let changed = tx.execute("INSERT INTO likes(user_id,post_id) VALUES(?,?) ON CONFLICT(user_id,post_id) DO NOTHING", &[Value::Integer(user_id), Value::Integer(post_id)]).map_err(internal)?;
    tx.commit().map_err(internal)?;
    Ok(json(
        if changed == 1 { 201 } else { 200 },
        Like {
            liked: true,
            already_liked: changed == 0,
            post_id,
        },
    ))
}
async fn not_found(_: Request) -> Response {
    error(404, "not found")
}

struct FeedApp;
impl Guest for FeedApp {
    fn http_handlers() -> Vec<HttpRoute> {
        vec![
            routing::get("/health", health),
            routing::get("/feed", feed),
            routing::get("/posts/{id}", detail),
            routing::post("/posts", create),
            routing::post("/posts/{id}/like", like),
            routing::get("/", not_found),
            routing::get("/{*path}", not_found),
            routing::post("/{*path}", not_found),
        ]
    }
}
export!(FeedApp);
