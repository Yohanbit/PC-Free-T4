# Upload a previously exported ZIP without mounting Drive in the desktop.
import zipfile, json, hashlib, stat, datetime
from google.colab import files
from pathlib import PurePosixPath
RESTORE_SAVES_DIRECTORY='' # Set the exact saves directory for this Minecraft instance.
assert RESTORE_SAVES_DIRECTORY, 'Indicar primero la carpeta saves de la instancia de Minecraft.'
target=Path(RESTORE_SAVES_DIRECTORY).expanduser().resolve()
app_home=Path(browser_env['HOME']).resolve()
assert target.is_relative_to(app_home), 'Restaurar solo dentro del home de aplicaciones.'
assert target.name=='saves', 'La carpeta de destino debe llamarse saves.'
uploaded=files.upload()
assert len(uploaded)==1, 'Subir solamente un respaldo ZIP por intento.'
filename=next(iter(uploaded))
archive_path=Path(filename)
assert archive_path.suffix.lower()=='.zip'
with zipfile.ZipFile(archive_path) as archive:
    infos=archive.infolist()
    assert len({i.filename for i in infos})==len(infos), 'ZIP con rutas repetidas.'
    assert sum(i.file_size for i in infos)<=2*1024**3, 'Respaldo demasiado grande.'
    manifest=json.loads(archive.read('manifest.json'))
    assert manifest['format']=='pc-free-worlds-v1'
    expected={item['path']:item for item in manifest['files']}
    assert set(expected)=={i.filename for i in infos if i.filename!='manifest.json' and not i.is_dir()}
    for info in infos:
        path=PurePosixPath(info.filename)
        assert not path.is_absolute() and '..' not in path.parts and '\\' not in info.filename
        assert not stat.S_ISLNK(info.external_attr>>16), 'No admitir enlaces simbólicos.'
        if info.filename=='manifest.json' or info.is_dir():
            continue
        assert len(path.parts)>=3 and path.parts[0]=='worlds'
        item=expected[info.filename]
        assert info.file_size==item['size']
        with archive.open(info) as source:
            assert hashlib.file_digest(source,'sha256').hexdigest()==item['sha256'], 'Integridad incorrecta.'
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    target.mkdir(parents=True,exist_ok=True)
    restored={}
    for item in manifest['files']:
        path=PurePosixPath(item['path'])
        name=path.parts[1]
        if name not in restored:
            directory=target/(name+'-restored-'+stamp)
            directory.mkdir(exist_ok=False)
            restored[name]=directory
        output=restored[name].joinpath(*path.parts[2:])
        assert output.resolve().is_relative_to(restored[name].resolve())
        output.parent.mkdir(parents=True,exist_ok=True)
        with archive.open(item['path']) as source, output.open('xb') as dest:
            shutil.copyfileobj(source,dest)
        account=pwd.getpwnam('pcfree-browser')
        os.chown(output,account.pw_uid,account.pw_gid)
    account=pwd.getpwnam('pcfree-browser')
    for directory in restored.values():
        for d in [directory,*[p for p in directory.rglob('*') if p.is_dir()]]:
            os.chown(d,account.pw_uid,account.pw_gid)
    print('Mundos restaurados en carpetas nuevas; no se sobrescribieron mundos existentes.')
    print(*restored.values(),sep='\n')
