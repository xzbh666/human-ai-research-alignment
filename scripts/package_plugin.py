"""Build one standalone plugin ZIP; keep the marketplace outside the archive."""
import argparse
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/human-ai-research-alignment'


def validate():
 manifest = json.loads((PLUGIN/'plugin.json').read_text())
 compat = json.loads((PLUGIN/'.codex-plugin/plugin.json').read_text())
 market = json.loads((ROOT/'.agents/plugins/marketplace.json').read_text())
 assert manifest['$schema']=='https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'
 for key in ['name','version','description']:
  assert manifest[key]==compat[key], 'Compatibility identity mismatch: '+key
 assert compat['interface']==manifest['extensions']['com.openai']['interface']
 assert len(compat['interface']['shortDescription'])<=30
 entry=market['plugins'][0]
 assert entry['name']==manifest['name']
 assert entry['source']['source']=='local'
 source=entry['source']['path']
 assert source.startswith('./') and (ROOT/source).resolve()==PLUGIN.resolve()
 assert entry['policy']['installation']=='AVAILABLE'
 assert entry['category']==compat['interface']['category']
 assert 'pluginId' not in entry, 'Do not bind a personal plugin ID to a workspace catalog'
 for name in ['__init__.py','__main__.py','cli.py']:
  assert (ROOT/'harp'/name).read_bytes()==(PLUGIN/'skills/human-ai-research-alignment/harp'/name).read_bytes(), 'Sync bundled CLI: '+name
 assert (ROOT/'pyproject.toml').read_bytes()==(PLUGIN/'skills/human-ai-research-alignment/pyproject.toml').read_bytes()
 files=[PLUGIN/'plugin.json',PLUGIN/'.codex-plugin/plugin.json']
 skill=PLUGIN/'skills/human-ai-research-alignment'
 files.extend(skill/name for name in ['SKILL.md','README.md','pyproject.toml'])
 files.extend(skill/'harp'/name for name in ['__init__.py','__main__.py','cli.py'])
 for path in files:
  assert path.is_file() and not path.is_symlink()
 return files


def build(output):
 files=validate()
 output=Path(output).resolve()
 if PLUGIN.resolve() in output.parents:
  raise ValueError('Archive must be outside the plugin directory')
 output.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
  for path in files:
   archive.write(path,Path(PLUGIN.name)/path.relative_to(PLUGIN))
 with zipfile.ZipFile(output) as archive:
  assert archive.testzip() is None
 return output

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',default=str(ROOT/'dist/human-ai-research-alignment.zip'))
 print(build(parser.parse_args().output))
