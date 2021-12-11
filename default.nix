# production package for reg-flake-input
{ stdenv, python3 }:
let
  pname = "reg-flake-input";
  version = "1.0.0";
in
stdenv.mkDerivation {
  inherit pname version;
  buildInputs = [ python3 ];
  src = ./.;
  # Just copy over the single .py file, substituting a real python path,
  # and removing the .py file extension.
  installPhase = ''
    mkdir -p $out/bin
    substitute ${pname}.py $out/bin/${pname} \
      --replace "#!/usr/bin/env python3" "#!${python3}/bin/python3"
    chmod +x $out/bin/${pname}
  '';
}
