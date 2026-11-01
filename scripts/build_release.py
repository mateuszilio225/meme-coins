"""Build, extract, validate and publish a local research-only ZIP. No network calls."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile, time, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    output=args.output.resolve();output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists(): raise FileExistsError('Release não sobrescreve ZIP existente')
    allowed={'.py','.md','.toml','.bat','.json','.log','.txt','.sha256'}
    def files(root):
        return sorted(p for p in root.rglob('*') if p.is_file() and p.suffix in allowed
                      and not any(x in ('.git','__pycache__','.venv','data','build','dist') or x.endswith('.egg-info') for x in p.relative_to(root).parts))
    def archive(root,path):
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
            for p in files(root): z.write(p,Path('moonshot_profit_research')/p.relative_to(root))
    with tempfile.TemporaryDirectory(prefix='moonshot release with spaces ') as tmp:
        base=Path(tmp);candidate=base/'candidate.zip';archive(ROOT,candidate)
        with zipfile.ZipFile(candidate) as z: z.extractall(base/'clean extraction')
        extracted=base/'clean extraction'/'moonshot_profit_research'
        env=os.environ.copy();env.pop('PYTHONPATH',None)
        commands=[]
        def run(arguments,name,expect=0):
            p=subprocess.run([sys.executable,'-m','meme_research',*arguments],cwd=extracted,env=env,capture_output=True,text=True)
            (ROOT/'evidence'/f'release-{name}.log').write_text(p.stdout+p.stderr,encoding='utf-8')
            commands.append({'name':name,'arguments':arguments,'exit_code':p.returncode,'expected':expect})
            if p.returncode!=expect: raise RuntimeError(f'{name} falhou: veja evidence/release-{name}.log')
            return p
        tests=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=extracted,env=env,capture_output=True,text=True)
        (ROOT/'evidence'/'release-clean-tests.log').write_text(tests.stdout+tests.stderr)
        if tests.returncode: raise RuntimeError('Testes na extração limpa falharam')
        demo=base/'offline demo with spaces.sqlite'
        run(['--version'],'version')
        run(['demo','--output',str(demo)],'demo')
        config=demo.with_suffix('.toml')
        for command in ('health','audit','watch','moonshot','moonshot-alerts','moonshot-trades','moonshot-profitability','moonshot-forensics','moonshot-missed','moonshot-quality','moonshot-compare','moonshot-scores','economics'):
            run(['--config',str(config),command],command)
        run(['--config',str(config),'evaluate','--period','test'],'expired-demo-test-evaluation',expect=0)
        run(['--config',str(config),'run','--once'],'synthetic-real-collector-protected',expect=1)
        run(['--config',str(config),'ablate','--output',str(base/'ablations clean')],'ablation')
        run(['--config',str(config),'backup','--output',str(base/'backup.sqlite')],'backup')
        # A real no-write report must not change database bytes.
        before=hashlib.sha256(demo.read_bytes()).hexdigest()
        run(['--config',str(config),'moonshot-profitability'],'readonly-repeat')
        if hashlib.sha256(demo.read_bytes()).hexdigest()!=before: raise RuntimeError('Read-only report changed DB')
        # Optional packaging check: pip is not a runtime requirement.
        installed=base/'installed package with spaces'
        package=subprocess.run([sys.executable,'-m','pip','install','--no-deps','--no-build-isolation','--target',str(installed),str(extracted)],cwd=base,env=env,capture_output=True,text=True)
        (ROOT/'evidence'/'release-pip-install.log').write_text(package.stdout+package.stderr)
        if package.returncode==0:
            package_env=env.copy();package_env['PYTHONPATH']=str(installed)
            result=subprocess.run([sys.executable,'-m','meme_research','--version'],cwd=base,env=package_env,capture_output=True,text=True)
            if result.returncode: raise RuntimeError('Installed package import failed')
            commands.append({'name':'installed-package-import','exit_code':result.returncode})
        report={'release':'0.1.0','python':sys.version,'platform':sys.platform,'clean_extraction_test_exit':tests.returncode,
                'test_summary':(tests.stdout+tests.stderr).splitlines()[-5:], 'cli_commands':commands,'pip_target_install_exit':package.returncode,
                'validated_windows':False,'validated_live_market_collection':False,'economic_edge_proven':False,
                'note':'Arquivos da demo só em diretório temporário; ZIP não inclui banco sintético disfarçado de real.'}
        (ROOT/'evidence'/'RELEASE_VALIDATION.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    # All retained evidence is included, then byte manifest is generated.
    manifest=[]
    for p in files(ROOT):
        if p.name=='MANIFEST.sha256': continue
        manifest.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix())
    (ROOT/'MANIFEST.sha256').write_text('\n'.join(manifest)+'\n')
    archive(ROOT,output)
    with tempfile.TemporaryDirectory(prefix='moonshot manifest check ') as tmp:
        with zipfile.ZipFile(output) as z:
            if z.testzip() is not None: raise RuntimeError('ZIP CRC failure')
            z.extractall(tmp)
        check=Path(tmp)/'moonshot_profit_research'
        for line in (check/'MANIFEST.sha256').read_text().splitlines():
            sha,rel=line.split('  ',1)
            if hashlib.sha256((check/rel).read_bytes()).hexdigest()!=sha: raise RuntimeError('Manifest mismatch: '+rel)
    checksum=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(checksum+'  '+output.name+'\n')
    print(json.dumps({'zip':str(output),'bytes':output.stat().st_size,'sha256':checksum,'manifest_files':len(manifest),'commands':len(commands),'tests':report['test_summary']},indent=2))

if __name__=='__main__': main()
