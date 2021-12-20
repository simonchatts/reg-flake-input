#!/usr/bin/env python3
#
# Update nix registry entries from a flake.lock file.
#
# See the help text below for more details.
#
# simonchatts, Dec 2021

import argparse, getpass, json, os, pathlib, subprocess, sys

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
    # First do a nix-prefetch-url, to either confirm this is already downloaded
    # by the hash, or download it, and either way provide a nix store path.
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
    # Treat failures in this function as non-fatal, and just bug out with an
    # error message, for slightly arbitrary reasons.
    if r.returncode != 0:
        print(
            "Warning: skipping NIX_PATH update, since unable "
            + f"to download nixpkgs: {r}",
            file=sys.stderr,
        )
        return

    # OK, we have a valid nix store path for our nixpkgs. First add a gcroot so
    # things hangs around:
    nixpkgs_path = r.stdout.decode("ascii").split("\n")[1]
    gcroot_path = (
        f"/nix/var/nix/gcroots/per-user/{getpass.getuser()}/reg-flake-input-nixpkgs"
    )
    # Unconditionally delete any previous entry...
    try:
        os.remove(gcroot_path)
    except Exception:
        pass
    # ... before writing a new symlink
    try:
        os.symlink(
            nixpkgs_path,
            gcroot_path,
            target_is_directory=True,
        )
    except Exception as e:
        print(f"Error adding {gcroot_path}: {e}", file=sys.stderr)

    # Secondly, write out a .nix-path file for setting NIX_PATH.
    # @@@ Should handle non-zsh shells
    with open(pathlib.Path.home() / ".nix-path", "w") as f:
        f.write(
            f"""\
if [[ "${{SHELL##*/}}" == zsh ]]; then
    # Array version of existing NIX_PATH
    if [ -z "$NIX_PATH" ]; then
        typeset -a np
    else
        IFS=: read -A np <<<"$NIX_PATH" # for bash: -a not -A
    fi

    (( nixpkgs_index = $#np + 1 ))
    for ((i = 1; i <= $#np; i++)); do
        if [[ "${{np[$i]%=*}}" == nixpkgs ]]; then
            nixpkgs_index=$i
        fi
    done
    unset i
    np[$nixpkgs_index]=("nixpkgs={nixpkgs_path}")

    # Finally set NIX_PATH
    export NIX_PATH=$(print -R ${{(j|:|)np}})
fi
"""
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
