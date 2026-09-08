"""Coordinate standalone generators and independent reviews for a new local round."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from build_review import ROOT,component_root,verify_approved_visuals,verify_no_embedded_generators,checked_file


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selections',type=Path,required=True)
    p.add_argument('--name',required=True,help='New local round directory name')
    p.add_argument('--node',default='node')
    a=p.parse_args()
    if not a.name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in a.name):
        raise ValueError('Use a simple new round name')
    verify_no_embedded_generators();verify_approved_visuals()
    audio=component_root('audio');video=component_root('video')
    ao=audio/'audio/output/candidates'/a.name;vo=video/'media/output/candidates'/a.name
    review=ROOT/'workspace'/a.name
    for out in (ao,vo,review):
        if out.exists():raise FileExistsError(out)
    selections=json.loads(a.selections.read_text())['selections']
    audio_env={**os.environ,'PYTHONPATH':str(audio/'src')+os.pathsep+str(audio/'tools'),'PYTHONDONTWRITEBYTECODE':'1'}
    def run(cmd,env=None):subprocess.run([str(x) for x in cmd],check=True,env=env)
    fields=[]
    for s in selections:
        for component in ('audioSource','visualSource'):
            d=s[component];checked_file(d['media']['path'],d['media']['sha256']);checked_file(d['manifest']['path'],d['manifest']['sha256'])
        run([sys.executable,audio/'tools/prototype_bed_reduction.py','--source-manifest',s['audioSource']['manifest']['path'],
             '--config',audio/'config/generator.xml','--output',ao],audio_env)
        manifest=Path(s['visualSource']['manifest']['path'])
        visual_source=json.loads(manifest.read_text())
        if 'backgroundTypography' in visual_source:
            typography=visual_source['backgroundTypography']
            checked_file(typography['localFile'],typography['localFileSha256'])
        for strength in (1,1.25,1.5):
            run([sys.executable,video/'tools/prototype_iteration.py','--manifest',manifest,
                 '--output',vo/f"{s['project']}-develop-{round(strength*100)}.mp4",'--strength',strength])
        if 'subjectLayer' in json.loads(manifest.read_text())['sourceArtifacts']:fields.append(manifest)
    if len(fields)!=1:raise ValueError('This focused round requires one existing layered number-field portrait')
    assets=vo/'field-assets'
    run([sys.executable,video/'tools/prototype_iteration.py','--manifest',fields[0],'--output',assets,'--field-assets'])
    run([a.node,video/'tools/webgl_field.cjs',assets])
    run([sys.executable,video/'tools/composite_fields.py','--manifest',fields[0],'--assets',assets,'--output',vo])
    run([sys.executable,Path(__file__).with_name('build_iteration_review.py'),'--selections',a.selections,
         '--visuals',vo,'--audio',ao,'--output',review])


if __name__=='__main__':main()
