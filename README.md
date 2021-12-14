![CI](https://github.com/simonchatts/reg-flake-input/workflows/CI/badge.svg)

# reg-flake-input

One of the selling points of nix flakes is finally saying goodbye to channels,
and [all their
issues](https://github.com/nix-dot-dev/nix.dev/issues/16#issuecomment-713701415).

And indeed, once you have converted things like a NixOS system, or just a user
profile (on NixOS, Darwin, or whatever) to a flake, then the dependencies are
nicely pinned. But there remain a few operations that default to the
channel-provided nixpkgs, such as:

 - `nix shell nixpkgs#<package>` (along with `nix run` etc)
 - `nix-shell` uses (eg where [shebang
   support](https://nixos.org/manual/nix/unstable/command-ref/nix-shell.html#use-as-a--interpreter)
   is needed, which is not yet present in the new flake-aware commands)
 - any `shell.nix` files lying around that still `import <nixpkgs>`

The tool here is intended to mop up these corner cases. The idea is that if you
have eg your user profile specified in a flake, then you just run
`reg-flake-input`, and this pins all these corner cases to the nixpkgs specified
in that `flake.lock` file.

In this way, you can upgrade all these instances at once, simply by running
`reg-flake-input` again whenever you update that `flake.lock` file, and
hopefully never have to think about channels ever again.

The mechanism is twofold:

 - Create a [user nix
   registry](https://nixos.org/manual/nix/stable/command-ref/new-cli/nix3-registry.html)
   entry for `nixpkgs` (or whatever) matching the `flake.lock` definition. This
   covers use cases like `nix shell nixpkgs#<package>`, `nix run
   nixpkgs#<package>` etc.

 - Ensure this version of nixpkgs is in the nix store, and add a per-user gcroot
   to preserve it across garbage collection, and write out a
   `~/.nix-path` file that updates `NIX_PATH` with the appropriate `nixpkgs=`
   entry.

   This means that if you source `~/.nix-env` from your `~/.zshrc`, you are also
   covered for the `nix-shell` and `import <nixpkgs>` cases above. (Note:
   currently this is limited to zsh.)

This explanation was all in the mainline case (nixpkgs specifically, with a
local `flake.lock` file, using the user nix registry), but you can override
these defaults with command-line arguments:

 - `--lock-file` specifies a different `flake.lock` file
 - `--entry-name` specifies a different package than `nixpkgs`
 - `--registry-file` specifies a different file than the user nix registry file

# Installing

You can just run this flake on-demand, eg:

    nix run github:simonchatts/reg-flake-inputs# -- --help

displays the help text.

You can also include the flake in a persistent profile. In the profile flake (eg
user or system profile) include `github:simonchatts/reg-flake-input` as a flake
input, add its `overlay` output to the profile overlays, and then use the
`reg-flake-input` package in the profile.
