# Explicit, manual export. Never copies launcher accounts, browser profiles,
# Steam, RustDesk, tokens, or the complete application home directory.
import zipfile, hashlib, json, datetime
assert 'browser_env' in globals(), 'Primero preparar la cuenta de aplicaciones.'
app_home=Path(browser_env['HOME']).resolve()
world_candidates=[]
for level in app_home.rglob('level.dat'):
    if level.is_symlink():
        continue
    world=level.parent.resolve()
    if world.is_relative_to(app_home) and world.is_dir():
        world_candidates.append(world)
world_candidates=sorted(set(world_candidates))
print('Mundos encontrados; seleccionar explícitamente los deseados:')
for index,world in enumerate(world_candidates):
    print(index,world)

# Edit these values only after "Guardar y salir" in Minecraft.
CONFIRM_GAME_SAVED_AND_CLOSED=False
SELECTED_WORLD_INDICES=[]
if not CONFIRM_GAME_SAVED_AND_CLOSED or not SELECTED_WORLD_INDICES:
    print('Sin respaldo todavía. Guardar y salir del mundo, editar confirmación e índices, y repetir solo la operación.')
else:
    assert all(isinstance(i,int) and 0<=i<len(world_candidates) for i in SELECTED_WORLD_INDICES)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    destination=Path('/tmp')/('PC-Free-worlds-'+stamp+'.zip')
    total=0
    manifest={'format':'pc-free-worlds-v1','created_utc':stamp,'files':[]}
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for index in sorted(set(SELECTED_WORLD_INDICES)):
            world=world_candidates[index]
            for source in sorted(world.rglob('*')):
                if source.is_symlink() or not source.is_file() or source.name=='session.lock':
                    continue
                assert source.resolve().is_relative_to(world)
                size=source.stat().st_size
                total+=size
                assert total<=2*1024**3, 'Respaldo mayor de 2 GiB; preparar exportación específica.'
                name='worlds/'+str(index)+'-'+world.name+'/'+source.relative_to(world).as_posix()
                digest=hashlib.file_digest(source.open('rb'),'sha256').hexdigest()
                archive.write(source,name)
                manifest['files'].append({'path':name,'size':size,'sha256':digest})
        archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    print('Respaldo creado:',destination.name,'| Bytes:',destination.stat().st_size)
    print('Solo mundos. Para mundos con mods, conservar también su lista/versiones de mods por separado.')
    from google.colab import files
    files.download(str(destination))
