{ stdenv, buildFractalideSubnet, upkeepers
  , db_rusticdb_bucket
  , io_print
  , tuple
  ,...}:

  buildFractalideSubnet rec {
   src = ./.;
   subnet = ''
   '${tuple}:(first="key1",second="value1")~insert' -> operation bucket(${db_rusticdb_bucket}) output -> input io_print(${io_print})
   '${tuple}:(first="key1")~read' -> operation bucket()
     '';

   meta = with stdenv.lib; {
    description = "Subnet: testing rusticdb";
    homepage = https://github.com/yesco/rusticdb;
    license = with licenses; [ mpl20 ];
    maintainers = with upkeepers; [ yesco ];
  };
}
