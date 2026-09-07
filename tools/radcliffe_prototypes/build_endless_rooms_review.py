"""Build the five-color, three-speed Endless Rooms comparison from silent candidates."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess
import time
from build_iteration_review import three_visual
from build_review import checked_file,component_root,load_component_lock,verify_approved_visuals,verify_no_embedded_generators


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--visuals',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--parent-review',type=Path,required=True)
    p.add_argument('--wait-seconds',type=int,default=0)
    args=p.parse_args();args.output=args.output.resolve();args.visuals=args.visuals.resolve();args.parent_review=args.parent_review.resolve()
    verify_no_embedded_generators();verify_approved_visuals()
    video=component_root('video');component_root('audio')
    recipes_path=video/'config/endless-rooms-color-speed-20260907.json'
    recipes=json.loads(recipes_path.read_text());parent=json.loads((args.parent_review/'review.json').read_text())
    previous=next(s for s in parent['studies'] if s['kind']=='rooms')
    assert not args.output.exists(),'Preserve earlier work; choose a new review folder'
    args.output.mkdir(parents=True)
    for name in ('visuals','posters','provenance'):(args.output/name).mkdir()
    report=dict(schemaVersion='1.0',status='color_speed_comparison_pending',createdAt=datetime.now(timezone.utc).isoformat(),
        preferredFamily='Endless Rooms',preferredDirectionRecord=checked_file(Path(__file__).resolve().parents[2]/'config/radcliffe-endless-rooms-direction-2026-09-07.json'),authority='User preferred Endless Rooms and requested five colors and mixed speeds.',
        developmentPercent=200,audio='none',selectedAudioBedReductionPercent=50,nativeDurationSec=11,comparisonDurationSec=33,
        humanVisualApproval=None,humanAVLoopApproval=None,colorSpeedChoice=None,registryModified=False,
        componentLock=load_component_lock(),recipes=checked_file(recipes_path),parentReview=checked_file(args.parent_review/'review.json'),
        assembler=checked_file(__file__),encodingImplementation=checked_file(Path(__file__).with_name('build_iteration_review.py')),
        template=checked_file(Path(__file__).with_name('endless_rooms_review.html')),
        ffmpegVersion=subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0],colors=[],speeds=[],studies=[])
    for v in recipes['variants']:
        if not any(c['id']==v['color'] for c in report['colors']):report['colors'].append(dict(id=v['color'],label=v['colorLabel'],background=v['palette'][0]))
        if not any(s['id']==v['speed'] for s in report['speeds']):report['speeds'].append(dict(id=v['speed'],label=v['speedLabel'],depthSpeedRelativeToOriginal=v['depthSpeedRelativeToOriginal']))
    deadline=time.monotonic()+args.wait_seconds
    for v in recipes['variants']:
        kind=v['id'];source=args.visuals/f'Infinity-blue-sky-{kind}-200.mp4';mp=source.with_suffix('.json')
        while True:
            try:
                manifest=json.loads(mp.read_text())
                if manifest.get('backgroundExperiment',{}).get('variant',{}).get('id')==kind:break
            except (FileNotFoundError,json.JSONDecodeError):pass
            if time.monotonic()>=deadline:raise RuntimeError('Native candidate is not complete: '+kind)
            time.sleep(1)
        checked_file(source,manifest['output']['sha256'])
        assert manifest['developmentStrength']==2 and manifest['audio']=='none'
        assert manifest['backgroundExperiment']['unwrappedNaturalEndpointIdentical']
        assert manifest['backgroundExperiment']['variant']==v
        target=args.output/'visuals'/f'{kind}-33s.mp4';checks=three_visual(source,target)
        poster=args.output/'posters'/f"{v['color']}.jpg"
        if not poster.exists():subprocess.run(['ffmpeg','-v','error','-n','-i',str(target),'-frames:v','1','-q:v','2',str(poster)],check=True)
        result=dict(kind=kind,color=v['color'],colorLabel=v['colorLabel'],speed=v['speed'],speedLabel=v['speedLabel'],
            title=v['colorLabel']+' · '+v['speedLabel'],description='Endless Rooms in '+v['colorLabel'].lower()+', with '+v['speedLabel'].lower()+' background depth travel.',
            url=str(target.relative_to(args.output)),poster=str(poster.relative_to(args.output)),native=checked_file(source),sourceManifest=manifest,checks=checks)
        report['studies'].append(result);shutil.copyfile(mp,args.output/'provenance'/mp.name)
        (args.output/'provenance'/f'{kind}-review-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
        print('Comparison ready: '+result['title'],flush=True)
    target=args.output/'visuals/previous-endless-rooms-33s.mp4';source=args.parent_review/previous['url']
    checked_file(source,previous['checks']['media']['sha256']);shutil.copyfile(source,target)
    poster=args.output/'posters/reference.jpg';shutil.copyfile(args.parent_review/previous['poster'],poster)
    report['studies'].append(dict(kind='reference',title='Previous Endless Rooms',description='The green version you preferred in the five-background study.',
        url=str(target.relative_to(args.output)),poster=str(poster.relative_to(args.output)),media=checked_file(target)))
    report['template']=checked_file(Path(__file__).with_name('endless_rooms_review.html'))
    (args.output/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    shutil.copyfile(Path(__file__).with_name('endless_rooms_review.html'),args.output/'index.html')
    shutil.copyfile(recipes_path,args.output/'provenance'/recipes_path.name)
    (args.output/'STATUS.md').write_text('# Endless Rooms — five colors, three speeds\n\nFifteen silent comparisons plus the previous Endless Rooms reference. Every video is 33 seconds: three native eleven-second cycles. The portrait, font, photographic geometry and 200% development are fixed. Only background palette and depth-travel speed vary. Slow and Medium use 20% and 60% of the original depth-travel rate; Original pace uses 100%. The center drift and tilt retain their original timing. No browser playback-rate changes, audio regeneration or duration stretching are used.\n\nEndless Rooms is the preferred family. Color/speed selection, final visual loop and AV loop approval remain pending. The other two portraits and all locked develop/audio choices are preserved.\n')
    files=[x for x in sorted(args.output.rglob('*')) if x.is_file()]
    (args.output/'SHA256SUMS.txt').write_text(''.join(f"{checked_file(x)['sha256']}  {x.relative_to(args.output)}\n" for x in files))
    print('Completed '+str(args.output),flush=True)


if __name__=='__main__':main()
