"""Append bed-only audio comparisons without changing visual or browser choices."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from build_iteration_review import three_audio
from extend_development_review import verify_inventory
from build_review import (checked_file,require,component_root,load_component_lock,
                          verify_approved_visuals,verify_no_embedded_generators)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--review',type=Path,required=True)
    p.add_argument('--audio',type=Path,required=True)
    a=p.parse_args();root=a.review.resolve()
    verify_no_embedded_generators();verify_approved_visuals()
    for name in ('audio','video'):component_root(name)
    inventory=verify_inventory(root)
    report=json.loads((root/'review.json').read_text())
    require(len(report['portraits'])==3,'Expected the existing three portraits')
    manifests=[(m,json.loads(m.read_text())) for m in a.audio.glob('AUD-*/*.json')]
    sources=[]
    for portrait in report['portraits']:
        require({v['kind'] for v in portrait['audio']}=={'original','bed90'},'Review already extended or unexpected audio set')
        original=next(v for v in portrait['audio'] if v['kind']=='original')
        reference=next(v for v in portrait['audio'] if v['kind']=='bed90')['sourceManifest']
        for gain in (.75,.5):
            matches=[(m,d) for m,d in manifests if d['sourceAudioId']==reference['sourceAudioId'] and d['bedLinearGain']==gain]
            require(len(matches)==1,'One native candidate required for each bed reduction')
            manifest_path,d=matches[0]
            require(d['sourceManifestSha256']==reference['sourceManifestSha256'],'Original composition changed')
            require(d['sourceWavSha256']==original['source']['sha256'],'Original delivered source changed')
            require(d['sourceRawReproducedExactly'] and d['foregroundSamplesIdentical'] and d['sourceMasterGainPreserved'],'Bed-only reconstruction proof required')
            require(d['sourceMasterGainDb']==reference['sourceMasterGainDb'],'Master gain changed')
            require(d['durationSec']==11 and d['durationBank']=='11s','Native eleven-second family required')
            require(d['humanAudioApproval'] is None and d['humanLoopApproval'] is None,'New comparisons must remain pending human review')
            require(d['loopValidation']['click_check_passed'] and d['loudness']['true_peak_dbfs']<=-1,'Native technical checks failed')
            checked_file(d['sourceManifest'],d['sourceManifestSha256'])
            for name in ('output','raw','generatorCode','mixingCode','generatorConfig'):
                checked_file(d[name]['path'],d[name]['sha256'])
            sources.append((portrait,gain,manifest_path,d))
    snapshot=root/'provenance/sound-through-bed90';destination=root/'audio/bed-25-50'
    require(not snapshot.exists() and not destination.exists(),'Preserve the previous extension; use a fresh review to repeat')
    snapshot.mkdir(parents=True);destination.mkdir()
    for name in ('index.html','review.json','STATUS.md','SHA256SUMS.txt'):
        shutil.copyfile(root/name,snapshot/name)
    extension=dict(type='bed_level_comparison',createdAt=datetime.now(timezone.utc).isoformat(),
                   predecessor=checked_file(snapshot/'review.json'),componentLock=load_component_lock(),
                   assembler=checked_file(__file__),reviewTemplate=checked_file(Path(__file__).with_name('iteration_review.html')),
                   addedBedReductionPercent=[25,50],humanAudioApproval=None,registryModified=False)
    for portrait,gain,manifest_path,manifest in sources:
        remaining=round(gain*100);reduction=100-remaining
        target=destination/f"{portrait['key']}-bed{remaining}-33s.wav"
        verified=three_audio(Path(manifest['output']['path']),target)
        require(all(j['clickScreenPassed'] for j in verified['joins']['joins']),'Repeated audio join screening failed')
        verified.update(kind=f'bed{remaining}',bedReductionPercent=reduction,url=str(target.relative_to(root)),
                        source=checked_file(manifest['output']['path'],manifest['output']['sha256']),
                        sourceManifest=manifest,sourceManifestFile=checked_file(manifest_path))
        portrait['audio'].append(verified)
        print(f"Verified {portrait['label']}: bed {reduction}% lower",flush=True)
    for item in inventory:checked_file(item['path'],item['sha256'])
    extension['preservedMedia']=[i for i in inventory if Path(i['path']).suffix in ('.mp4','.wav')]
    report.setdefault('extensions',[]).append(extension)
    temporary=root/'review.next.json';temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(root/'review.json')
    shutil.copyfile(Path(__file__).with_name('iteration_review.html'),root/'index.next.html')
    (root/'index.next.html').replace(root/'index.html')
    with (root/'STATUS.md').open('a') as f:
        f.write('\nSound comparison expanded: original bed, 10%, 25%, and 50% reductions for each selected soundtrack. Percentages refer to bed amplitude, not perceived loudness or the whole mix. Original foreground samples, event timing, source master gain, all visual media, and browser draft choices are preserved. New 33-second WAVs contain three exact native eleven-second PCM passes; technical level and join screening passed. Human audio and loop review remain pending.\n')
    checks=[checked_file(f) for f in sorted(root.rglob('*')) if f.is_file() and f!=root/'SHA256SUMS.txt']
    temporary=root/'SHA256SUMS.next.txt'
    temporary.write_text(''.join(f"{r['sha256']}  {Path(r['path']).relative_to(root)}\n" for r in checks));temporary.replace(root/'SHA256SUMS.txt')
    print('Expanded sound comparison: '+str(root),flush=True)


if __name__=='__main__':main()
