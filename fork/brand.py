#!/usr/bin/env python3
"""This fork's own name in Home Assistant: Tessera Dev.

Home Assistant shows an add-on by the `name` in screen_manager/config.yaml and its sidebar entry by `panel_title`, and
the add-on store lists the repository by the `name` in repository.yaml. Renaming those three is enough to tell this
fork from the upstream project at a glance, in the store, on the add-on page and in the sidebar.

Only files Home Assistant reads are touched, never web/src: the editor's bundle in screen_manager/app/static is built
from it and committed, so a branding change there would rewrite the bundle in every sync and every pull request.

    python3 fork/brand.py            put the Tessera Dev name on
    python3 fork/brand.py --check    say whether it is on (exit 1 when it is not, for a hook or CI)
    python3 fork/brand.py --remove   take it off, for a branch that goes upstream

Both directions are the same table read the other way, so this is safe to run twice and after a rebase: it says what
it changed and changes nothing that is already the way it wants it. fork/README.md is the whole procedure.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

# (file, what upstream says, what this fork says). The text has to be unique in the file: an exact swap keeps the rest
# of the line, and the comments and the order of the YAML, as they are.
BRANDING = [
    ('repository.yaml', 'name: Tessera\n', 'name: Tessera Dev\n'),
    ('screen_manager/config.yaml', 'name: Tessera Screen Manager\n', 'name: Tessera Dev Screen Manager\n'),
    ('screen_manager/config.yaml', 'panel_title: Tessera\n', 'panel_title: Tessera Dev\n'),
    ('screen_manager/config.yaml',
     'description: "Tessera: touch screens for Home Assistant.',
     'description: "Tessera Dev, a development fork: touch screens for Home Assistant.'),
]


def swap(remove):
    """Apply the branding, or take it off. Returns (changed, problems) as lists of lines to print."""
    changed, problems = [], []
    for name, upstream, fork in BRANDING:
        source, target = (fork, upstream) if remove else (upstream, fork)
        path = ROOT / name
        text = path.read_text(encoding='utf-8')
        if text.count(target) == 1 and source not in text:
            continue                                    # already the way we want it
        if text.count(source) != 1:
            problems.append(f'{name}: expected exactly one "{source.strip()}"; the file changed upstream, '
                            f'fix fork/brand.py')
            continue
        path.write_text(text.replace(source, target, 1), encoding='utf-8')
        changed.append(f'{name}: {source.strip()} -> {target.strip()}')
    return changed, problems


def check():
    """0 when every line says what this fork says, 1 otherwise."""
    missing = [f'{name}: {fork.strip()}' for name, _, fork in BRANDING
               if fork not in (ROOT / name).read_text(encoding='utf-8')]
    for line in missing:
        print(f'not branded: {line}')
    print('branded as Tessera Dev' if not missing else 'run python3 fork/brand.py')
    return 1 if missing else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true', help='only say whether the branding is on')
    group.add_argument('--remove', action='store_true', help='take the branding off, for a pull request branch')
    args = parser.parse_args()
    if args.check:
        return check()
    changed, problems = swap(args.remove)
    for line in changed:
        print(line)
    for line in problems:
        print(line, file=sys.stderr)
    if not changed and not problems:
        print('nothing to do: already ' + ('upstream' if args.remove else 'Tessera Dev'))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
