from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib, json, re
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
SKILL=ROOT/'hand-drawn-explainer'
files=sorted(p for p in SKILL.rglob('*') if p.is_file())
links=[]
for p in files:
    if p.suffix!='.md': continue
    for dest in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if '://' in dest or dest.startswith('#'): continue
        target=(p.parent/dest.split('#')[0]).resolve()
        assert target.is_relative_to(SKILL.resolve()),(p,dest,'outside package')
        assert target.exists(),(p,dest,'missing')
        links.append(str(target.relative_to(SKILL)))
out=ROOT/'dist'/'hand-drawn-explainer-v0.3.0-rc.1.zip'
out.parent.mkdir(exist_ok=True)
with ZipFile(out,'w',ZIP_DEFLATED) as z:
    for p in files:z.write(p,p.relative_to(ROOT).as_posix())
with ZipFile(out) as z:
    assert len(z.namelist())==len(files)
    assert z.testzip() is None
    for p in files:
        assert hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(z.read(p.relative_to(ROOT).as_posix())).digest()
size=Image.open(ROOT/'validation/v0.3/editorial-original.png').size
result={'version':'0.3.0-rc.1','files':len(files),'local_links_checked':len(links),'archive_bytes':out.stat().st_size,'archive_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'archive_source_hashes_match':True,'editorial_dimensions':size,'editorial_semantic_status':'failed','narrative_status':'not_generated','quick_validate':'passed using system Python; bundled Python lacks yaml','git_diff_check':'passed','global_install':False}
(ROOT/'validation/v0.3/checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
