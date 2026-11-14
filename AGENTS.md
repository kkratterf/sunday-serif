# AGENTS.md

Rules for AI coding agents (Claude, Codex, Copilot, Cursor, ...) and humans working on Sunday Serif.
Read this file before changing anything. If a rule here conflicts with an instruction from the maintainer, the maintainer wins.

## What this repo is

Sunday Serif is an open source (OFL) text serif made for Sunday, the slow social network. One family, roman and italic, with four variable axes: weight (`wght` 400–600) and three effects, Light Burn (`BURN` −100…100), Ink Bleed (`INKB` 0…100) and Worn Print (`WORN` 0…100). Sunday Serif Blur is a static colour companion font built from the statics.

| Path | What it is |
| --- | --- |
| `sources/SundaySerif.designspace`, `sources/SundaySerif-Italic.designspace` | Axes, masters, named instances (Regular/Medium/SemiBold) and the Light Burn rules (`rvrn` swaps to `.varAlt01/02` past +55/+65) |
| `sources/Roman/`, `sources/Italic/` | UFO masters, 81 per style: for each weight (Regular, Medium, SemiBold), 21 Light Burn masters (−100…+100, step 10) plus Ink100 and Worn100 masters at Light Burn −100, 0 and +100 |
| `scripts/build.py` | The whole build: fontmake → post-processing (names, STAT, version, gasp/prep) → statics (pathops, effects at 0) → WOFF2 → Blur |
| `scripts/blur.py` | Makes Sunday Serif Blur (COLRv0) from a static TTF |
| `VERSION` | The release version (SemVer). The single source of truth for the font version |
| `site/` | The website (sunday-serif.kkratter.com), deployed to GitHub Pages by `.github/workflows/pages.yml` |
| `OFL.txt`, `FONTLOG.txt`, `AUTHORS.txt`, `CONTRIBUTORS.txt` | License and font history, shipped inside every release zip |

`fonts/` and `build/` are build output and are never committed.

## Language of the project

- **Code, comments, commit messages, PR titles and PR descriptions, README, FONTLOG: English.**
- Release notes section titles (`.github/release.yml`) are in Italian, like the maintainer's other repos.

## Build and test

Needs [uv](https://docs.astral.sh/uv/) (it fetches Python 3.12). These mirror CI (`.github/workflows/ci.yml`):

```bash
make            # fonts/variable, fonts/ttf, fonts/otf, fonts/webfonts, fonts/blur (~2 min)
make variable   # only the variable fonts, for quick checks while editing
make test       # fontbakery check-universal on variable, statics and Blur (~6 min)
```

Two virtualenvs on purpose: `.venv` (build, `requirements.txt`) and `.venv-qa` (fontbakery, `requirements-qa.txt`), because their pinned dependencies clash. Change pins only in a `build:` PR, rebuild, and compare the output with the previous build.

## How the sources work

- Every weight has the same 27 master locations, and **all 81 masters of a style must stay point-compatible** (same glyphs, same contours, same point structure). fontmake fails the build otherwise.
- The "pores" used by Worn Print are extra 8-point contours at the end of each glyph. Each weight has its own set, and every master carries the pores of all three weights: its own, plus the other weights' pores collapsed to a single point (invisible). Keep that order (base contours, Regular pores, Medium pores, SemiBold pores) when editing a glyph.
- A design change to a glyph has to be made in every master where it shows. In practice: edit the Light Burn 0 master of each weight in Fontra (or another UFO editor), then check the extremes (−100, +100) and the effect masters with `make variable`.
- New glyphs need: an outline in every master, the same pore structure (or no pores), a Unicode value, kerning groups when they relate to an existing letter, and a `.varAlt01` alternate plus a designspace rule if the base letter has one.
- Do not commit generated UFO instances, `.glyphs` exports or editor caches.

## Rules for changes

- **CI must be green** (build + fontbakery with zero FAIL) before a PR is ready. Never skip or silence a fontbakery check to get green: if a check is a false alarm, explain why in the PR and exclude it explicitly in the Makefile with a comment.
- Every visual change ships with a **before/after proof image** in the PR description (the same text at the same size, both versions).
- Keep the font names stable: family "Sunday Serif" / "Sunday Serif Blur", files and PostScript names `SundaySerif-*`. "Sunday Serif" is a Reserved Font Name: never rename it, and do not reuse it for a derivative.
- Do not change axis tags, ranges or defaults without a `feat!:` PR: websites and apps depend on them.
- Third-party outlines only under the OFL or a compatible licence, credited in `FONTLOG.txt`, `AUTHORS.txt` and the copyright string.
- Keep PRs small and focused: one issue, one PR. Do not mix a design change with a build change.
- Match the style of the surrounding code.

## Docs, roadmap and planning

- **Do not commit docs, roadmaps, plans, audits, reports or design notes to this repo.** No `ROADMAP.md`, `PLAN.md`, `docs/`, `notes/`, proof sheets. The roadmap lives outside the repo; proof images go in PR descriptions.
- Allowed documentation: `README.md` (user-facing usage), `FONTLOG.txt` (one line per release, the OFL convention), code comments, and this file plus `CLAUDE.md`.
- **Backlog = GitHub issues only.** No GitHub Projects, no milestones. Every issue carries labels:
  - area: `design` (shapes, spacing, kerning, new characters), `effects` (Light Burn, Ink Bleed, Worn Print, Blur), `site`, `ci` (build, CI, release), `bug`
  - priority: `P0`, `P1`, `P2`
  - version: `v0.1`, `v0.2`, `v0.3`, ...
- Before opening an issue, search for duplicates. Reference the issue from the PR (`Closes #N`).

## Naming conventions

### Commits

[Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`

- Summary in English, imperative mood, lower case, no trailing period, ≤ 72 characters.
- Types: `feat` (new glyphs, features, axes), `fix`, `perf` (smaller files), `refactor`, `docs` (README/FONTLOG/comments only), `ci`, `build`, `chore`, `revert`.
- Scopes: `glyphs`, `spacing`, `kerning`, `features`, `burn`, `ink`, `worn`, `blur`, `build`, `site`, `ci`, `release`.
- Breaking changes (renamed axis, removed glyph or style): `feat(burn)!: ...` plus a `BREAKING CHANGE:` footer.
- Body explains *why*, wrapped at 72 columns.

Examples: `feat(glyphs): add the Latin Extended-B letters for Romanian`, `fix(kerning): tighten To and Yo in the italic`, `ci: cache the build virtualenv`.

### Pull requests

- **Title = a Conventional Commit line** (same format as above). Prefer squash merge, so the title becomes the commit on `main`.
- Description: what changed, why, how it was tested, a before/after proof for anything visual, and `Closes #N`.
- Add the matching **area label** (`design`, `effects`, `site`, `ci`, `bug`). Release notes are grouped by these labels (`.github/release.yml`); use `skip-changelog` for changes users don't care about.
- Open as draft while CI is red or work is incomplete.

### Branches

`type/short-kebab-description`, e.g. `feat/latin-ext-b`, `fix/italic-k-kerning`.
Agent platforms that assign their own branch names (e.g. `claude/...`) are fine; the PR title carries the convention.

## Versions and releases

- SemVer, tags `vX.Y.Z`, the same naming as `kkratterf/maramao` and `kkratterf/fratmscript`: the release title is the bare tag (`v0.2.0`, never "Sunday Serif v0.2.0"), published by `github-actions[bot]`, notes generated from `.github/release.yml` (sections by area label, in Italian). Assets: `SundaySerif-X.Y.Z.zip` and `SHA256SUMS.txt`.
- The font version inside the files is derived from `VERSION` by `scripts/build.py`: `X.Y.Z` → `X.YYZ` (v0.1.0 → 0.010, v0.12.3 → 0.123, v1.0.0 → 1.000). So minor ≤ 99 and patch ≤ 9; the build refuses anything else.
- Minor release = a version milestone, cut when all `P0` issues of that version label are closed and `main` is green. Patch release for a fix users need (a broken glyph, a wrong metric).
- 1.0.0 means the glyph set, names and axes are stable.
- **Merging the version-bump PR is the release.** Nobody has to start a workflow by hand.
- **No `CHANGELOG.md`.** The changelog lives in GitHub Release notes; `FONTLOG.txt` gets one summary line per release.

### How to cut a release (agents and humans)

1. Check that every `P0` issue of the version label is closed and `main` is green.
2. Open a PR titled `chore(release): vX.Y.Z` that changes only `VERSION` (from `X.Y.Z-dev` to `X.Y.Z`) and adds the release line at the top of the ChangeLog in `FONTLOG.txt`. Label it `skip-changelog`.
3. Merge it (squash) once CI is green. `release.yml` runs on every push to `main` that touches `VERSION`: if the tag `vX.Y.Z` does not exist yet, it builds the fonts, runs fontbakery, zips them with the licence files, tags, and publishes the GitHub Release with notes grouped by label.
4. Check the "Release" run in Actions and the new release page, then tell the maintainer the version is out.

- Between releases `VERSION` holds the next version with a `-dev` suffix (`0.2.0-dev`): the build stamps it, the release workflow ignores it. The bump PR removes the suffix; right after a release, a `chore(release): start vX.Y.Z-dev` PR (label `skip-changelog`) sets the next one.
- Any other suffix (`0.3.0-beta.1`) becomes a pre-release.
- If a release run fails, fix the cause in a normal PR (it may change `release.yml`): merging it runs the workflow again, which publishes the version whose tag is still missing. The maintainer can also start `release.yml` by hand (`workflow_dispatch`); with `dry_run: true` it builds everything and publishes nothing (the zip goes to the workflow artifacts).

### What agents cannot do here

Agent sandboxes are refused these actions, so ask the maintainer instead of retrying or working around them:

- start, re-run or cancel workflows (`workflow_dispatch`, re-runs): that is why releases start from a merge;
- delete branches or tags, force-push;
- create, edit or delete GitHub Releases;
- change repository settings: description, topics, Pages, custom domain, secrets, branch protection.

## Merging

- Agents may push branches, open PRs and merge their own PRs once CI is green and the PR closes its issue(s), **except design changes**: a PR labelled `design` or `effects` waits for the maintainer's approval of the proof image. Agents never push directly to `main`, force-push `main`, or bypass a failing check. The maintainer is told about releases, not about every merge.
- Never rewrite history on someone else's branch.
