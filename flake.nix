# Flake for reg-flake-input
{
  description = "Update nix registry entries from a flake.lock file";
  outputs = { self, nixpkgs }:
    let
      # Boilerplate
      name = "reg-flake-input";
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system:
        let pkgs = import nixpkgs {
          inherit system;
          overlays = [ self.overlay ];
        }; in f pkgs);
    in
    {
      # Outputs
      overlay = final: prev: { "${name}" = final.callPackage ./. { }; };
      packages = forAllSystems (pkgs: { "${name}" = pkgs."${name}"; });
      defaultPackage = forAllSystems (pkgs: pkgs."${name}");

      # Development environment
      devShell = forAllSystems (pkgs: import ./shell.nix { inherit pkgs; });

      # Very basic CI: just code formatting
      checks = forAllSystems (pkgs: {
        "${name}" = pkgs."${name}";
        format = pkgs.runCommand "check-format"
          { buildInputs = [ pkgs.black pkgs.nixpkgs-fmt ]; }
          ''
            ${pkgs.black}/bin/black --check ${./.}
            ${pkgs.nixpkgs-fmt}/bin/nixpkgs-fmt --check ${./.}
            touch $out
          '';
      });
    };
}
