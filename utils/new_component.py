#! /usr/bin/env nix-shell
#! nix-shell -i python -p python rustUnstable.cargo pythonPackages.configobj
#! nix-shell -I nixpkgs=https://github.com/NixOS/nixpkgs/archive/125ffff089b6bd360c82cf986d8cc9b17fc2e8ac.tar.gz

# this script sets up a new rustfbp component
# by reading the utils/component.ini which you have configured
# then:
# * writing the cargo.toml file
# * writing the default.nix file
# * writing the lib.rs file
# * then runs `cargo generate-lockfile` on the component to create the lockfile
# * inserting the component into components/default.nix

import os.path
import sys
import shlex
import subprocess
from configobj import ConfigObj
config = ConfigObj("component.ini")

def write_cargo_deps(deps):
    toml = "rustfbp = \"*\"\ncapnp = \"*\"\n"
    for crate in deps:
        toml += crate + " = \"" + deps[crate] + "\"\n"
    return toml

def create_cargo_toml (component_name, cargo_deps):
    cargo_toml_template = """
[package]
name = \"""" + component_name + """\"
version = "0.1.0"
authors = ["test <test@test.com>"]

[lib]
name = \"""" + component_name + """\"
crate-type = ["dylib"]

[dependencies]
""" + write_cargo_deps(cargo_deps)
    return cargo_toml_template

def write_contracts(ports, include_type):
    contracts = ""
    contract_set = set()
    for port_type in ports:
        for port in ports[port_type]:
            contract_set.add(ports[port_type][port])
    if include_type == "nix_contracts":
        contracts += ' '.join(map("{0}".format, contract_set))
    elif include_type == "rust_contracts":
        contracts += ", ".join(contract_set)
    elif include_type == "nix_header":
        if len(contract_set) > 0:
            contracts += "# contracts:\n, "
        contracts += ', '.join(map("{0}".format, contract_set))
    return contracts

def write_external_dependencies(external_dependencies):
    externs = ""
    externs_set = set()
    for deps in external_dependencies:
        for extern in external_dependencies[deps]:
            externs_set.add(extern)
    if len(externs_set) > 0:
        externs = "# external dependencies:\n, "
        externs += ', '.join(map("{0}".format, externs_set))
    return externs

def write_builtins(external_dependencies):
    externs = ""
    externs_set = set()
    for deps in external_dependencies:
        for extern in external_dependencies[deps]:
            externs_set.add(extern)
    if len(externs_set) > 0:
        externs = "buildInputs = [ "
        externs += ' '.join(map("{0}".format, externs_set))
        externs += " ];\n"
    return externs

def create_default_nix (component_description, ports, external_dependencies):
    default_nix = """
{ stdenv, buildFractalideComponent, genName, upkeepers
""" + write_contracts(ports, "nix_header")  + """
""" + write_external_dependencies(external_dependencies) + """
, ...}:

buildFractalideComponent rec {
  name = genName ./.;
  src = ./.;
  contracts = [""" + write_contracts(ports, "nix_contracts") + """];
  depsSha256 = "2m6n74fm7k99pp13j5d5yyp4j0znc0s10958hhyyh3shq9rj8862";
  """ + write_builtins(external_dependencies) + """
  meta = with stdenv.lib; {
    description = "Component: """ + component_description + """";
    homepage = https://gitlab.com/fractalide/fractalide/tree/master/components/maths/boolean/nand;
    license = with licenses; [ mpl20 ];
    maintainers = with upkeepers; [ dmichiels sjmackenzie];
  };
}
    """
    return default_nix

def write_externs(deps):
    externs = "#![feature(question_mark)]\n#[macro_use]\nextern crate rustfbp;\nextern crate capnp;\n"
    for crate in deps:
        externs += "extern crate " + crate + ";\n"
    return externs

def write_input_output_array_ports(ports):
    formatted_port_types = []
    for port_type in ports:
        port_list = []
        start = port_type + "("
        for port in ports[port_type]:
            port_list.append(port + ": " + ports[port_type][port])
        formatted_port_types.append(start + ", ".join(map("{0}".format, port_list)) + "),")
    return "\n  ".join(formatted_port_types)

def write_extra_ports(extra_ports):
    e_ports = "  option(" + extra_ports["option"] + "),\n  acc(" + extra_ports["acc"] + "), "
    if extra_ports["portal"] == "true":
        e_ports += "portal()"
    return e_ports

def write_simple_input_extractor(port, contract):
    ip = "ip_" + port
    reader = port + "_reader"
    return """
    let mut """ + ip + """ = self.ports.recv(\"""" + port + """\")?;
    let """ + port + """ = {
        let """ + reader + """: """ + contract + """::Reader = """ + ip + """.get_root()?;
        """ + reader + """.get_XXX() // read contract: """ + contract + """ to replace XXX
    };"""

def write_simple_input_extractors(simple_inputs):
    simple_input_extractors = ""
    for port in simple_inputs:
        simple_input_extractors += write_simple_input_extractor(port, simple_inputs[port])
    return simple_input_extractors

def write_inputs_array_extractor(port, contract):
    ip = "ip_" + port
    reader = port + "_reader"
    return """
    let mut """ + ip + """ = self.ports.recv(\"""" + port + """\")?;
    let """ + port + """ = {
        let """ + reader + """: """ + contract + """::Reader = """ + ip + """.get_root()?;
        """ + reader + """.get_XXX() // read contract: """ + contract + """ to replace XXX
    };"""

def write_inputs_array_extractors(input_arrays):
    input_array_extractors = ""
    for port in input_arrays:
        input_array_extractors += write_inputs_array_extractor(port, input_arrays[port])
    return input_array_extractors

def write_simple_outputs_extractor(port, contract):
    out_ip = "out_ip_" + port
    return """
    let mut """ + out_ip + """ = IP::new();
    {
      let mut variable = """ + out_ip + """.init_root::<""" + contract + """::Builder>();
      variable.set_XXX(YYY); // read contract: """ + contract + """ to replace XXX
    }"""

def write_simple_outputs_extractors(simple_outputs):
    simple_outputs_extractors = ""
    for port in simple_outputs:
        simple_outputs_extractors += write_simple_outputs_extractor(port, simple_outputs[port])
    return simple_outputs_extractors

def write_outputs_array_extractor(port, contract):
    out_ip = "out_ip_" + port
    return """
    let mut """ + out_ip + """ = IP::new();
    {
      let mut variable = """ + out_ip + """.init_root::<""" + contract + """::Builder>();
      variable.set_XXX(YYY); // read contract: """ + contract + """ to replace XXX
    }"""

def write_outputs_array_extractors(outputs_array):
    outputs_array_extractors = ""
    for port in outputs_array:
        outputs_array_extractors += write_outputs_array_extractor(port, outputs_array[port])
    return outputs_array_extractors

def write_ip_extractors(ports):
    extractors = ""
    for port_type in ports:
        if port_type == "inputs":
            extractors += write_simple_input_extractors(ports[port_type])
        if port_type == "inputs_array":
            extractors += write_inputs_array_extractors(ports[port_type])
        if port_type == "outputs":
            extractors += write_simple_outputs_extractors(ports[port_type])
        if port_type == "outputs_array":
            extractors += write_outputs_array_extractors(ports[port_type])
    return extractors

def write_simple_outputs_send(port):
    out_ip = "out_ip_" + port
    return """
    self.ports.send(\"""" + port + """\", """ + out_ip + """)?;"""

def write_simple_outputs_sends(simple_outputs):
    simple_outputs_sends = ""
    for port in simple_outputs:
        simple_outputs_sends += write_simple_outputs_send(port)
    return simple_outputs_sends

def write_outputs_array_send(port):
    out_ip = "out_ip_" + port
    return """
    for p in self.ports.get_output_selections(\"""" + port + """\")? {
        self.ports.send_array(\"""" + port + """\", &p, """ + out_ip + """.clone())?;
    }"""

def write_outputs_array_sends(outputs_array):
    outputs_array_sends = ""
    for port in outputs_array:
        outputs_array_sends += write_outputs_array_send(port)
    return outputs_array_sends

def write_sends(ports):
    sends = ""
    for port_type in ports:
        if port_type == "outputs":
            sends += write_simple_outputs_sends(ports[port_type])
        if port_type == "outputs_array":
            sends += write_outputs_array_sends(ports[port_type])
    return sends

def create_lib_rs(component_name, ports, cargo_deps, extra_ports):
    lib_rs = write_externs(cargo_deps) + """
component! {
  """ + component_name + """, contracts(""" + write_contracts(ports, "rust_contracts") + """)
  """ + write_input_output_array_ports(ports) + "\n" + write_extra_ports(extra_ports) + """
  fn run(&mut self) -> Result<()> {
    """ + write_ip_extractors(ports) + write_sends(ports) + """
    Ok(())
  }
}
    """
    return lib_rs

def create_paths(component_name):
    folders = component_name.replace("_","/")
    folders_list = folders.split(os.sep)
    root = "../components"
    path = root + "/" + folders
    if os.path.exists(path + "/default.nix"):
        sys.exit("*** Aborted: component already exists. ***")
    else:
        for folder in folders_list:
            try:
                os.mkdir(os.path.join(root,folder))
            except Exception:
                pass
            root += "/" + folder
    try:
        os.mkdir(os.path.join(path, "src"))
    except Exception:
        pass
    return folders

def write_file(path, contents):
    file = open(path, "w")
    for line in contents:
        file.write(line)

def insert_component_into_filesystem(component_name, cargo_toml, default_nix, lib_rs):
    path = create_paths(component_name)
    write_file("../components/" + path + "/" + "default.nix", default_nix)
    write_file("../components/" + path + "/" + "Cargo.toml", cargo_toml)
    write_file("../components/" + path + "/src/lib.rs", lib_rs)
    return path

def insert_component_into_default_nix(component_name, path):
    header = []
    components = []
    footer = []
    with open('../components/default.nix') as f:
        lines = f.read().splitlines()
        mode = "header"
        for line in lines:
            if mode == "header":
                header.append(line)
                if line == "self = rec { # use one line only to insert a component (utils/new_component.py sorts this list)":
                    mode = "components"
                    continue
            if mode == "components":
                if line == "}; # use one line only to insert a component (utils/new_component.py sorts this list)":
                    mode = "footer"
                    footer.append(line)
                    continue
                components.append(line)
            if mode == "footer":
                footer.append(line)
        components.append("  " + component_name + " = callPackage ./" + path + " {};")
    components.sort()
    with open('../components/default.nix', 'r+') as f:
        f.seek(0)
        for line in header:
            f.write(line + "\n")
        for line in components:
            f.write(line + "\n")
        for line in footer:
            f.write(line + "\n")
        f.truncate()

def generate_lockfile(path):
      cmd = "cargo generate-lockfile --manifest-path " + "../components/" + path + "/Cargo.toml"
      args = shlex.split(cmd)
      output, error = subprocess.Popen(args, stdout = subprocess.PIPE, stderr= subprocess.PIPE).communicate()

cargo_toml = create_cargo_toml(config['component_name'], config['cargo dependencies'])
default_nix = create_default_nix(config['component_description'], config['ports'], config['external dependencies'])
lib_rs = create_lib_rs(config['component_name'], config['ports'], config['cargo dependencies'], config['extra ports'])
path = insert_component_into_filesystem(config['component_name'], cargo_toml, default_nix, lib_rs)
insert_component_into_default_nix(config['component_name'], path)
generate_lockfile(path)

print "*** Created component: " + config['component_name'] + " ***"
