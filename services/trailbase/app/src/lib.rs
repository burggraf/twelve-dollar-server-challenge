#[cfg(any(test, target_arch = "wasm32"))]
mod contract;

#[cfg(target_arch = "wasm32")]
mod routes;
