with import <nixpkgs> {};
stdenv.mkDerivation {
  name = "env";
  buildInputs = with python27Packages; [
    jabberbot
    xmpppy
    feedparser
    requests2
    dns
    pyopenssl
  ];
}
