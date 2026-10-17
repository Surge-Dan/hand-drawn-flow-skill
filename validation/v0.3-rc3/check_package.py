"""Validate references and archive fidelity; does not validate generated images."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib, json, re, subprocess, sys
import yaml

root = Path(__file__).resolve().parents[2]
skill = root / 'hand-drawn-flow'
validator = Path.home()/'.codex/skills/.system/skill-creator/scripts/quick_validate.py'
subprocess.run([sys.executable, '-X', 'utf8', str(validator), str(skill)], check=True)
subprocess.run(['git','diff','--check'], cwd=root, check=True)
ui = yaml.safe_load((skill/'agents/openai.yaml').read_text(encoding='utf-8'))
assert 25 <= len(ui['interface']['short_description']) <= 64
assert '$hand-drawn-flow' in ui['interface']['default_prompt']
assert ui['policy']['allow_implicit_invocation'] is True
files = sorted(p for p in skill.rglob('*') if p.is_file())
links = 0
for p in files:
    if p.suffix != '.md': continue
    for dest in re.findall(r'\]\(([^)]+)\)', p.read_text(encoding='utf-8')):
        if '://' in dest or dest.startswith('#'): continue
        target = (p.parent/dest.split('#')[0]).resolve()
        assert target.is_relative_to(skill.resolve()) and target.exists(), (p,dest)
        links += 1
out = root/'dist/hand-drawn-flow-v0.3.0-rc.3.zip'
out.parent.mkdir(exist_ok=True)
with ZipFile(out,'w',ZIP_DEFLATED) as z:
    for p in files: z.write(p,p.relative_to(root).as_posix())
with ZipFile(out) as z:
    assert len(z.namelist()) == len(files)
    assert z.testzip() is None
    for p in files:
        assert hashlib.sha256(p.read_bytes()).digest() == hashlib.sha256(z.read(p.relative_to(root).as_posix())).digest()
result = {'version':'0.3.0-rc.3','structure_validation':'passed','ui_validation':'passed','diff_check':'passed','internal_links_checked':links,'archive_file_count':len(files),'archive_bytes':out.stat().st_size,'archive_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'archive_source_hashes_match':True,'new_image_validation':'not_run','global_install':False}
(Path(__file__).parent/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
