# Running this fork as Tessera Dev

This is a fork of [MaxGramser/homeassistant_espscreen](https://github.com/MaxGramser/homeassistant_espscreen). It
runs in Home Assistant under its own name, **Tessera Dev**, so there is never any doubt about which of the two is on
the screen. Work that is meant for the upstream project goes there as a pull request without that name, and without
anything else that belongs only to this fork.

Everything in this `fork/` folder exists only here. Upstream has no such folder, so it never causes a conflict when
this fork is brought up to date, and it is never part of a pull request.

## What carries the name

Home Assistant reads three things and nothing else:

| Where | Upstream | Here |
|---|---|---|
| `repository.yaml` `name` | Tessera | Tessera Dev |
| `screen_manager/config.yaml` `name` | Tessera Screen Manager | Tessera Dev Screen Manager |
| `screen_manager/config.yaml` `panel_title` | Tessera | Tessera Dev |

`fork/brand.py` puts those on and takes them off:

```sh
python3 fork/brand.py            # put the name on
python3 fork/brand.py --check    # say whether it is on (exit 1 when it is not)
python3 fork/brand.py --remove   # take it off, for a branch that goes upstream
```

It is one commit of its own, and it is never cherry-picked into a pull request. Later work goes on top of it; `fork/pr.sh` takes the commits you name, so the branding does not have to stay at the tip of `main`.
Running it twice changes nothing, so after a rebase you run it again instead of resolving the same conflict by hand.

The editor's own sidebar inside the add-on still says Tessera. That is on purpose: the page is built from `web/src`
into `screen_manager/app/static`, which is committed, so renaming it there would rewrite the whole bundle in every
sync and in every pull request. The name in Home Assistant's sidebar is what tells the two apart.

## Installing it in Home Assistant

Home Assistant's add-on store takes a repository, not a branch: it reads the repository's **default branch**. So the
branch you want to run is the one that has to be `main` here (or whatever you set as the default branch on GitHub,
under Settings, General, Default branch).

1. Settings, Add-ons, Add-on store, the three dots top right, Repositories.
2. Add `https://github.com/agillis/tessera`.
3. The store gets a **Tessera Dev** section with **Tessera Dev Screen Manager** in it. Install that one.

Two things to know:

- **It is a separate add-on**, not an update of the upstream one: Home Assistant names an add-on after its repository
  as well. Its data (`screens.json`, the tiles, the ESPHome profiles it made) starts empty, so the screens have to be
  added again, or the data folder copied over from a backup of the other add-on.
- **Don't run both at once.** Both map host port 8098 for the camera pictures the screens fetch, and both would send
  layouts to the same screens. Stop the one you are not using. (Changing `ports:` in
  `screen_manager/config.yaml` here is enough to run them side by side, but then the screens have to be told the
  other port, so it is simpler to stop one.)

Home Assistant offers an update when the `version` in `screen_manager/config.yaml` is higher than the one it runs. So
a change you want to see on your own Home Assistant needs a version bump and a `CHANGELOG.md` entry, the same rule
upstream has (`AGENTS.md`).

## Day to day

```sh
# your own work, on main
git switch main
... edit ...
tools/check.sh                  # --firmware as well when the firmware changed
git commit -am "What changed"
# bump screen_manager/config.yaml and write the CHANGELOG entry, then
git push
```

Keep one change per commit and keep the version bump out of it, in a commit of its own. That is what makes a pull
request cheap later: the change alone travels, without the release bookkeeping that would collide with whatever
upstream released in the meantime.

## Taking over what upstream released

```sh
fork/sync.sh --fetch     # only look: what is new upstream
fork/sync.sh             # fetch, rebase main onto upstream/main, put the Tessera Dev name back
fork/sync.sh --merge     # merge instead of rebasing, for a branch someone else also has
```

A conflict stops the script on purpose. Resolve it, finish the rebase (`git rebase --continue`), and run
`fork/sync.sh` again; it will put the name back and tell you what is left to run. The two files that conflict most
often are `screen_manager/config.yaml` (the `version` line) and `screen_manager/CHANGELOG.md` (both sides added an
entry at the top). Take upstream's version and bump past it, and keep both changelog entries.

After a sync: `tools/check.sh`, then `git push --force-with-lease` (a rebase rewrites what was pushed before).

## Sending a change upstream

```sh
fork/pr.sh fix/stop-build <commit> [<commit> ...]
```

That makes a branch that starts at `upstream/main` with only those commits on it, so the pull request holds the
change and nothing else: not the Tessera Dev name, not your other work in progress. It refuses if the branding ever
did ride along. Nothing is pushed; it prints the `git push` and `gh pr create` lines to run.

Upstream's `AGENTS.md` is the house style to follow in the change itself: plain English, no em dashes, no names or
personal entity ids, `tools/check.sh` green, and a `CHANGELOG.md` entry with the version bump as the last commit of
the branch, where the maintainer can redo or drop it.

## The screens' own firmware still comes from upstream

A screen installed from this add-on builds its firmware from the packages on GitHub, and
`screen_manager/app/core.py` still points those at the upstream repository:

```python
REPO = 'https://github.com/MaxGramser/homeassistant_espscreen'
REF = 'main'
```

So a change to `packages/` or `components/` in this fork does **not** reach a screen installed from Tessera Dev. Two
ways round that, deliberately not done here:

- **Build from this checkout**, which is what `checkout/` is for and what does not touch anything shared:
  `esphome run checkout/cyd.yaml` (see `checkout/README.md`).
- **Point the packages at this fork**: `REPO`/`REF` in `core.py`, the `url:` and `FONT_DIR` in every
  `packages/<board>.yaml` (written by `tools/generate_entries.py`), plus two places that match the upstream name as
  text: `FONT_URL` in `tests/test_release_lint.py` and the `'homeassistant_espscreen' not in raw` check in
  `screen_manager/app/firmware.py`. ESPHome fetches packages over HTTPS, so every firmware change then has to be
  pushed to GitHub before a screen can build it. If you do this, make it part of the branding commit, never part of a
  pull request.
