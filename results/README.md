# Benchmark artifact storage

Git tracks the benchmark reports, summaries, manifests, checksums, resource samples,
logs, and supporting review documents. It does **not** track these bulky generated
files under `results/`:

- `samples.json` / `samples.json.gz`: the raw k6 metric stream emitted by a run.
- `source.tar.gz`: the source overlay captured by `scripts/benchmark.py` for a run.

New runs generate these files automatically. A new run does **not** reproduce the
exact historical timing samples or source overlay. Keep existing local copies:
they are audit evidence, not disposable caches. The repository cleanup untracks
these files without deleting or modifying them locally.

A fresh clone therefore contains the readable results and small supporting
evidence, **not complete historical run bundles**. `SHA256SUMS` files remain
unchanged and still describe the complete original bundles. To verify every entry
with `sha256sum -c SHA256SUMS`, first restore the corresponding raw stream and source
archive to their original run directory. Do not regenerate historical artifacts or
rewrite their checksums to make a partial checkout appear complete.

When distributing full evidence, store the original bulk files outside Git (for
example, in release assets or object storage), preserving run paths and checksums,
and record their download location alongside the report. No external artifact
upload or storage location is established by this cleanup. Until one is provided,
full historical verification requires the retained local copies.

Source, dependency lockfiles, migrations, seed generators, and golden test fixtures
remain tracked. Generated datasets, private runtime state, dependencies, and build
caches are excluded by the root `.gitignore`.

Check the ignore policy with:

```sh
python3 -m unittest discover -s test -p test_gitignore.py -v
```
