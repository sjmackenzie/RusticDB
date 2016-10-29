{ stdenv
  , buildFractalideComponent
  , genName, upkeepers
  , tuple
  , generic_text
  , ...}:

buildFractalideComponent rec {
  name = genName ./.;
  src = ./.;
  contracts = [ tuple generic_text ];
  depsSha256 = "0fkqkrh9v4q4b13mr5bng434b6wf0w4d28v830vsqls8fz5qzanq";

  meta = with stdenv.lib; {
    description = "Subnet: simple rustic database";
    homepage = https://github.com/yesco/rusticdb;
    license = with licenses; [ mpl20 ];
    maintainers = with upkeepers; [ yesco ];
  };
}
