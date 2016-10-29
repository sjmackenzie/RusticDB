{ pkgs, support, allContracts, allComponents, ... }:
let
callPackage = pkgs.lib.callPackageWith (pkgs // support // allContracts // allComponents);
self = rec { # use one line only to insert a component (utils/new_component.py sorts this list)
  db_rusticdb = callPackage ./db/rusticdb {};
  db_rusticdb_bucket = callPackage ./db/rusticdb/bucket {};
  db_rusticdb_test = callPackage ./db/rusticdb/test {};
}; # use one line only to insert a component (utils/new_component.py sorts this list)
in
self
