"""Present five independently rendered silent Infinity studies at the locked develop strength."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess
from build_iteration_review import three_visual
from build_review import checked_file,component_root,load_component_lock,verify_approved_visuals,verify_no_embedded_generators

STUDIES=[
 ('current','Blue current','Bright digits travel in a broad, undulating current across an electric-blue field.'),
 ('monument','Monument','Cropped, oversized digits shift like monumental pieces of colored typography.'),
 ('orbit','Orbit','Warm and cool digits revolve through a dark numerical space at different radii.'),
 ('weather','Color weather','Translucent, oversized digits overlap, turn and breathe into changing color mixtures.'),
 ('rooms','Endless rooms','Successive rooms made of digits advance through a deep green numerical space.'),
]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--visuals',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--choices',type=Path,default=Path('config/radcliffe-comparison-choices-2026-09-07.json'))
    a=p.parse_args();a.output=a.output.resolve();a.visuals=a.visuals.resolve()
    verify_no_embedded_generators();verify_approved_visuals()
    for k in ('audio','video'):component_root(k)
    assert not a.output.exists(),'Use a new folder and preserve previous work'
    choices=json.loads(a.choices.read_text());selected=next(x for x in choices['portraits'] if x['project']=='Infinity')
    assert selected['developPercent']==200 and selected['bedReductionPercent']==50
    a.output.mkdir(parents=True);(a.output/'visuals').mkdir();(a.output/'posters').mkdir();(a.output/'provenance').mkdir()
    report=dict(schemaVersion='1.0',createdAt=datetime.now(timezone.utc).isoformat(),status='experimental_visual_comparison_pending',
                constraints={'backgroundObjects':'0123456789 only','font':'same licensed Brandon Grotesque Bold as the source','developmentPercent':200,
                             'photographicGeometry':'unchanged','nativeDurationSec':11,'comparisonDurationSec':33,'cycles':3},
                componentLock=load_component_lock(),comparisonChoices=checked_file(a.choices),
                assembler=checked_file(__file__),encodingImplementation=checked_file(Path(__file__).with_name('build_iteration_review.py')),
                template=checked_file(Path(__file__).with_name('blue_sky_review.html')),
                ffmpegVersion=subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0],
                humanVisualApproval=None,humanAVLoopApproval=None,
                infinityFieldChoice=None,registryModified=False,audio='none; selected soundtrack and bed choice remain locked',studies=[])
    for number,(kind,title,description) in enumerate(STUDIES,1):
        source=a.visuals/f'Infinity-blue-sky-{kind}-200.mp4';manifest=json.loads(source.with_suffix('.json').read_text())
        checked_file(source,manifest['output']['sha256'])
        assert manifest['developmentStrength']==2 and manifest['audio']=='none'
        assert manifest['backgroundExperiment']['objects']=='0123456789 only'
        native=checked_file(source);target=a.output/'visuals'/f'Infinity-{kind}-33s.mp4'
        checks=three_visual(source,target)
        poster=a.output/'posters'/f'{kind}.jpg'
        subprocess.run(['ffmpeg','-v','error','-n','-i',str(target),'-frames:v','1','-q:v','2',str(poster)],check=True)
        result=dict(kind=kind,number=number,title=title,description=description,url=str(target.relative_to(a.output)),poster=str(poster.relative_to(a.output)),
                    native=native,sourceManifest=manifest,checks=checks)
        report['studies'].append(result)
        shutil.copyfile(source.with_suffix('.json'),a.output/'provenance'/source.with_suffix('.json').name)
        print('Review ready: '+title,flush=True)
    root=Path(__file__).resolve().parents[2]
    reference=selected['reviewVisual'];source=root/reference['path'];checked_file(source,reference['sha256'])
    target=a.output/'visuals/Infinity-reference-33s.mp4';shutil.copyfile(source,target)
    poster=a.output/'posters/reference.jpg'
    subprocess.run(['ffmpeg','-v','error','-n','-i',str(target),'-frames:v','1','-q:v','2',str(poster)],check=True)
    report['studies'].append(dict(kind='reference',title='Current static field',description='The existing number design with your chosen 200% develop setting. The number field itself does not move.',
                                 url=str(target.relative_to(a.output)),poster=str(poster.relative_to(a.output)),media=checked_file(target)))
    (a.output/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    shutil.copyfile(Path(__file__).with_name('blue_sky_review.html'),a.output/'index.html')
    shutil.copyfile(a.choices,a.output/'provenance/locked-comparison-choices.json')
    (a.output/'STATUS.md').write_text('# Five Infinity background departures\n\nFive new silent, independent visual experiments, each 33 seconds (three native eleven-second passes), plus the existing static reference. The full-body portrait and 200% develop setting are preserved. Only digits 0–9 in the same font form the backgrounds. No field is selected automatically; human visual and final AV loop reviews remain pending. Audio files, audio choices and Registry records are unchanged.\n')
    checks=[checked_file(x) for x in sorted(a.output.rglob('*')) if x.is_file()]
    (a.output/'SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {Path(r['path']).relative_to(a.output)}\n" for r in checks))
    print('Completed '+str(a.output),flush=True)


if __name__=='__main__':main()
