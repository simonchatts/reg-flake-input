#!/usr/bin/env python3
#
# Update nix registry entries from a flake.lock file.
#
# See the help text below for more details.
#
# simonchatts, Dec 2021

import argparse, json, pathlib, subprocess, sys

# User registry file
REG_FILE = pathlib.Path.home() / ".config" / "nix" / "registry.json"


def parse_args():
    "Parse command-line arguments"
    parser = argparse.ArgumentParser(
        description="""\
Update nix registry entries from a flake.lock file.

Basic usage is just run with no arguments, which:

 - reads the 'flake.lock' file in the current directory
 - extracts the 'nixpkgs' version specified there
 - writes it to the user nix registry (under ~/.config/nix)
 - ensure this nixpkgs is in the nix store
 - provide a NIX_PATH declaration in ~/.nix-path

so subsequent invocations of eg 'nix shell nixpkgs#<package>'
use the nixpkgs version that is pinned in the flake.lock file.

The NIX_PATH declaration is just to mop up any remaining things
like nix-shell usage involving <nixpkgs>. It's up to the user to
actually source ~/.nix-path to opt into this.""",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--lock-file",
        default="flake.lock",
        help="flake.lock file (default: ./flake.lock)",
    )
    parser.add_argument(
        "--entry-name", default="nixpkgs", help="entry name (default: nixpkgs)"
    )
    parser.add_argument(
        "--registry-file",
        default=REG_FILE,
        help="nix registry file (default: user registry)",
    )
    return parser.parse_args()


def get_current_registry(args):
    "Load any current registry entries, minus the specified entry if present"
    try:
        reg = json.load(open(args.registry_file))
        assert reg["version"] == 2
        # Remove the specified entry if already present
        for (idx, flake) in enumerate(reg["flakes"]):
            if flake["from"]["id"] == args.entry_name:
                reg["flakes"].pop(idx)
                break
    except Exception as e:
        reg = {"version": 2, "flakes": []}
    return reg


def update_registry(reg, entry, args):
    "Update the registry file with the provided entry"
    reg["flakes"].append(
        {
            "from": {"type": "indirect", "id": args.entry_name},
            "to": entry,
        }
    )
    try:
        with open(args.registry_file, "w") as f:
            json.dump(reg, f, indent=2)
    except Exception as e:
        sys.exit(f"Unable to write registry file: {e}")


def update_nix_path(entry):
    """
    Update NIX_PATH for a nixpkgs rev from GitHub.

    This is just for things like nix-shell using import <nixpkgs>,
    and assumes this is a nixpkgs rev from GitHub.
    """
    url = f'https://github.com/{entry["owner"]}/{entry["repo"]}/archive/{entry["rev"]}.zip'
    r = subprocess.run(
        [
            "nix-prefetch-url",
            url,
            entry["narHash"],
            "--name",
            "nixpkgs",
            "--unpack",
            "--print-path",
        ],
        stdout=subprocess.PIPE,
    )
    if r.returncode == 0:
        nixpkgs = r.stdout.decode("ascii").split("\n")[1]
        with open(pathlib.Path.home() / ".nix-path", "w") as f:
            f.write(f"export NIX_PATH=nixpkgs={nixpkgs}")
    else:
        print(
            "Warning: skipping NIX_PATH update, since unable "
            + f"to download nixpkgs: {r}"
        )


def main():
    "Run the application"
    sys.tracebacklimit = 0
    args = parse_args()
    try:
        lock_file = json.load(open(args.lock_file))
    except Exception as e:
        sys.exit(
            f"Error: unable to open flake.lock file: {e}\n"
            + "(Just omitting this argument assumes 'flake.lock' in the current directory)"
        )
    try:
        entry = lock_file["nodes"][args.entry_name]["locked"]
    except KeyError:
        sys.exit(
            f"Error: no such entry name '{args.entry_name}' found in {args.lock_file}\n"
            + "(Just omitting this argument assumes 'nixpkgs')"
        )
    reg = get_current_registry(args)
    update_registry(reg, entry, args)
    if args.entry_name == "nixpkgs" and entry["type"] == "github":
        update_nix_path(entry)


if __name__ == "__main__":
    main()
