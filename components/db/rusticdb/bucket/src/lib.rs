#![feature(question_mark)]
#[macro_use]
extern crate rustfbp;
extern crate capnp;

pub struct Portal {
    kvs: HashMap<String, String>,
}

impl Portal {
    fn new() -> Self {
        Portal {
            kvs: HashMap::new(),
        }
    }
    fn clear(&mut self) {
        self.kvs.clear();
    }
}

component! {
    db_rusticdb_bucket, contracts(tuple, generic_text)
    inputs(operation: tuple),
    inputs_array(),
    outputs(output: generic_text),
    outputs_array(),
    option(),
    acc(), portal(Portal => Portal::new())
    fn run(&mut self) -> Result<()> {
        let mut ip_operation = try!(self.ports.recv("operation"));
        try!(handle_ip(self, ip_operation));
        Ok(())
    }
}

pub fn handle_ip(mut comp: &mut db_rusticdb_bucket, mut ip_input: IP) -> Result<()> {
    match &ip_input.action[..] {
        "insert" => {
            let reader = try!(ip_input.get_root::<tuple::Reader>());
            let key = try!(reader.get_first());
            let value = try!(reader.get_second());
            println!("Attempting to insert key: \"{}\" with value: \"{}\"", key, value);
            comp.portal.kvs.insert(key.into(), value.into());
            let mut ip = IP::new();
            {
                let mut builder = ip.init_root::<generic_text::Builder>();
                builder.set_text("inserted into bucket!");
            }
            let _ = comp.ports.send("output", ip);
        }
        "read" => {
            let reader = try!(ip_input.get_root::<tuple::Reader>());
            let key = try!(reader.get_first());
            println!("Reading value for key: {}", key);
            let value = try!(reader.get_second());
            let resp = comp.portal.kvs.get(key).map(|resp| resp.as_str())
            .unwrap_or("");
            let mut ip = IP::new();
            {
                let mut builder = ip.init_root::<generic_text::Builder>();
                builder.set_text(resp);
            }
            ip.action = key.to_string();
            let _ = comp.ports.send("output", ip);
        }
        _ => { let _ = comp.ports.send("output", ip_input); }
    }

    Ok(())
}
