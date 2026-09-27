# Elorater — YC Startup Arena

Pairwise Elo arena for YC-style startup pitches. Founders submit ideas, get
10 placement matches against anchored ideas, and receive an Elo, percentile,
and per-match reasons. Public submissions are free and listed; private
ratings are hidden from the leaderboard + fetch API.

Reconstructed Sep 2026 from `__pycache__` remnants (`seed_yc_arena`,
`load_yc_fixture`, migrations for `Contest`/`Submission`/`EloRating`/`Match`).
There was no git history in this folder, so history starts here — squashed
into a single `core/0001_initial` migration. A snapshot of the interim
superthink (MCP Tournament/Option) system lives in
`backup_superthink_2026-09-27/` (gitignored).

## Run

```bash
python manage.py migrate
python manage.py seed_yc_arena --reset --matches 8   # 26 apps (8 real YC + 18 AI) + AI tournament
# or: python manage.py load_yc_fixture                # 8 real YC apps at 1500, unrated
python manage.py runserver
```

Pages: `/` leaderboard · `/submit/` · `/startup/<id>/`
API: `GET /api/leaderboard/` · `POST /api/submit/`

`POST /api/submit/` body: `{company_name, pitch|product, tagline?, founders_blurb?, is_public?}`
(defaults to private for API use). Returns `{elo, rank, placement_matches, matches[]}`.

## How rating works

- Every entry starts at 1500 Elo (provisional K=48 for the first 10 matches, then 32).
- New submissions play 10 placement matches vs top public anchors.
- `seed_yc_arena` judges with deterministic `heuristic-v1` (specificity +
  traction signals − buzzwords), recorded per match with reasons.
- `load_yc_arena` replays recorded AI admit judgments (judge=`human-yc-rank`).
  Rankings are AI-only; there is no human voting.

## Layout

- `core/models.py` — Contest, Submission, EloRating, Match, ContestField, SubmissionValue
- `core/services.py` — Elo math + heuristic judge + run_tournament / run_full_round_robin
- `core/views.py` — ARENA_TITLE/DESCRIPTION, get_arena, leaderboard/submit/detail + fetch API
- `core/management/commands/seed_yc_arena.py` — 30-app preseed (8 real funded + AI)
- `core/management/commands/load_yc_fixture.py` — wipe + load `core/fixtures/yc_apps.json`
