"""Offline checks only: no Colab/GPU/login/Drive/network access."""
import ast, json, os, sys, tempfile, types, shutil, pwd, zipfile, hashlib
from pathlib import Path

root=Path(__file__).resolve().parents[1]
for p in (root/'scripts').glob('*.py'):
    ast.parse(p.read_text(),filename=str(p))
for path in root.glob('*.ipynb'):
    document=json.loads(path.read_text())
    assert document['nbformat']==4
    for cell in document['cells']:
        if cell['cell_type']=='code':
            assert cell['outputs']==[] and cell['execution_count'] is None
            ast.parse(''.join(cell['source']))
desktop=json.loads((root/'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
cell2_code=''.join(desktop['cells'][2]['source'])
ns={}
exec(compile(cell2_code,'cell2','exec'),ns)
embedded=ns.get('SOURCES',{})
for name,source in embedded.items():
    assert source==(root/'scripts'/name).read_text(encoding='utf-8'), 'Cuaderno desactualizado: '+name
assert 'selkies-desktop.py' in embedded and 'compat-steam.py' in embedded and 'compat-apps.py' in embedded
assert '.Xauthority' in embedded['selkies-desktop.py'] and "'-ac'" not in embedded['selkies-desktop.py']
assert 'matching_version' in embedded['selkies-desktop.py']

with tempfile.TemporaryDirectory(prefix='pcfree-backup-test-') as folder:
    home=Path(folder)/'home';home.mkdir()
    world=home/'.minecraft/saves/TestWorld';world.mkdir(parents=True)
    (world/'region').mkdir()
    (world/'level.dat').write_bytes(b'fictional-level')
    (world/'region/r.0.0.mca').write_bytes(b'fictional-region')
    (world/'session.lock').write_text('do-not-copy')
    (home/'.steam').mkdir()
    (home/'.steam/secret-account.txt').write_text('do-not-copy')
    exported=[]
    files=types.SimpleNamespace(download=lambda p:exported.append(Path(p)),upload=lambda:{})
    google=types.ModuleType('google');colab=types.ModuleType('google.colab');colab.files=files
    sys.modules['google']=google;sys.modules['google.colab']=colab
    env={'browser_env':{'HOME':str(home)},'Path':Path,'os':os,'shutil':shutil,'pwd':types.SimpleNamespace(getpwnam=lambda _:types.SimpleNamespace(pw_uid=os.getuid(),pw_gid=os.getgid()))}
    exporter=(root/'scripts/10-export-worlds.py').read_text()
    exporter=exporter.replace('CONFIRM_GAME_SAVED_AND_CLOSED=False','CONFIRM_GAME_SAVED_AND_CLOSED=True').replace('SELECTED_WORLD_INDICES=[]','SELECTED_WORLD_INDICES=[0]')
    exec(compile(exporter,'test-export','exec'),env)
    assert len(exported)==1
    archive=exported[0]
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        assert any(name.endswith('/level.dat') for name in names)
        assert not any('session.lock' in name or 'secret-account' in name for name in names)
    upload=Path(folder)/'restore.zip';shutil.copyfile(archive,upload);archive.unlink()
    target=home/'restored/saves'
    restore=(root/'scripts/11-restore-worlds.py').read_text().replace("RESTORE_SAVES_DIRECTORY=''",'RESTORE_SAVES_DIRECTORY='+repr(str(target)))
    oldcwd=Path.cwd();os.chdir(folder)
    files.upload=lambda:{'restore.zip':upload.read_bytes()}
    try:
        exec(compile(restore,'test-restore','exec'),env)
        assert len(list(target.glob('*/level.dat')))==1
        restored=next(target.glob('*/level.dat'))
        assert restored.read_bytes()==b'fictional-level'
        assert next(target.glob('*/region/r.0.0.mca')).read_bytes()==b'fictional-region'
        assert (world/'level.dat').read_bytes()==b'fictional-level'
        # Reject a validly checksummed archive attempting traversal.
        payload=b'not-a-world'
        badname='worlds/Test/../../escape.dat'
        with zipfile.ZipFile(upload,'w') as z:
            z.writestr(badname,payload)
            z.writestr('manifest.json',json.dumps({'format':'pc-free-worlds-v1','files':[{'path':badname,'size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}]}))
        try:
            exec(compile(restore,'test-malicious-restore','exec'),env)
        except AssertionError:
            pass
        else:
            raise AssertionError('Traversal archive was not rejected')
        assert not (Path(folder)/'escape.dat').exists()
    finally:
        os.chdir(oldcwd)

print('PASS: syntax, empty notebook outputs, embedded sources, fictional world round-trip, privacy boundaries, traversal rejection.')
print('NOT TESTED: fresh Colab setup, real Minecraft saves, Google Drive authorization/copy, Steam login, game controllers.')
