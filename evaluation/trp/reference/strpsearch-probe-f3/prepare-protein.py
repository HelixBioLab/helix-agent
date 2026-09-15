import gemmi, pathlib, hashlib, json
p=pathlib.Path('/work/2xqh.cif'); st=gemmi.read_structure(str(p))
before={c.name:len(c) for c in st[0]}
st.remove_ligands_and_waters()
out=pathlib.Path('/work/protein-only/2xqh.cif'); out.parent.mkdir()
st.make_mmcif_document().write_file(str(out))
pathlib.Path('/work/protein-only-transform.json').write_text(json.dumps({'method':'gemmi.Structure.remove_ligands_and_waters; diagnostic input transformation, not upstream default','input_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'residues_before':before,'residues_after':{c.name:len(c) for c in st[0]}},indent=2))
