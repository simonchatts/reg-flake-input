# Development environment
{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python3
    black
    nixpkgs-fmt
  ];
}
