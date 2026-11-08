# Flaskr post search

This extension to Pallets' Flaskr tutorial adds title and body search to the
existing blog index. Base release: Flask 3.1.3, commit
`22d924701a6ae2e4cd01e9a15bbaf3946094af65`.

## Run locally

From `examples/tutorial`, activate your existing environment:

```bash
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python -m flask --app flaskr run --debug --port 5001
```

Open http://127.0.0.1:5001. For a brand-new database only, run
`python -m flask --app flaskr init-db` before starting the server. This command
resets the database; do not run it over existing posts you want to keep.

## Behavior

- GET `/?q=guitar` searches both post titles and bodies.
- The query is trimmed; empty or whitespace-only input displays all posts.
- Matching is literal and case-insensitive for ASCII text. SQL uses bound
  parameters and `instr(lower(...), lower(?))`; `%` and `_` are not wildcards.
- Posts are ordered by creation time descending, then ID descending for ties.
- The labeled search field preserves the query; Clear returns to `/`.
- Empty searches on an empty blog show "No posts yet." Searches with no matches
  show "No posts found."
- Jinja autoescaping protects the rendered search value and post content.
- Existing registration, login, creation, editing, deletion and ownership checks
  remain in their existing routes. No database schema change is required.

## Files

- `flaskr/blog.py`: optional filtering and deterministic ordering.
- `flaskr/templates/blog/index.html`: search form and empty-state messages.
- `flaskr/static/style.css`: wrapping controls and visible keyboard focus.
- `tests/test_search.py`: functional tests alongside the original test suite.

## Limits and attribution

SQLite's built-in `lower()` does not provide complete Unicode case folding.
Search scans post text; this is intended for the tutorial's small data set, not a
large search service. There is no ranking, stemming, pagination or paper-based
algorithm. The application remains a local educational demo with the original
development defaults.

Original project: https://github.com/pallets/flask, distributed under its included
license. This search extension was prepared with ChatGPT/Codex. Earlier
Claude-style explanations in the accompanying conversation were simulated, not
an actual Claude Code session.
