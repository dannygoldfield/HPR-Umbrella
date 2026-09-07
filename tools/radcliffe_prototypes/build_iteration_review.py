"""Prepare independent visual and audio reviews, without granting approvals."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import wave
import numpy as np
from build_review import checked_file,require,component_root,load_component_lock,verify_approved_visuals,verify_no_embedded_generators
from prepare_selected import packets,inspect_audio


def frame_hashes(source, repeats=0):
    data=subprocess.check_output(['ffmpeg','-v','error','-stream_loop',str(repeats),'-i',str(source),
                                  '-map','0:v:0','-f','framehash','-hash','sha256','-'],text=True)
    return [line.rsplit(',',1)[1].strip() for line in data.splitlines() if line and not line.startswith('#')]


def three_visual(source, target):
    original=frame_hashes(source)
    repeated=frame_hashes(source,2)
    require(len(original)==264 and repeated==original*3,'Native visual frames did not repeat exactly')
    # Encode the entire viewing sample in one pass so codec state does not restart at either join.
    subprocess.run(['ffmpeg','-v','error','-n','-stream_loop','2','-i',str(source),'-map','0:v:0','-an',
                    '-c:v','libx264','-threads','2','-preset','medium','-crf','16','-pix_fmt','yuv420p',
                    '-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-color_range','tv',
                    '-frames:v','792','-movflags','+faststart',str(target)],check=True)
    delivery=packets(target)
    require(len(delivery)==792,'Wrong number of review video frames')
    require(all(abs(t-i/24)<.000002 for i,t in enumerate(sorted(float(p['pts_time']) for p in delivery))),'Video timeline gap')
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(target),'-vf','scale=270:480,format=gray','-f','rawvideo','-'])
    frames=np.frombuffer(raw,dtype=np.uint8).reshape((792,480,270)).astype(np.int16)
    deltas=np.abs(frames[1:]-frames[:-1]).mean(axis=(1,2))
    p99=float(np.quantile(deltas,.99))
    joins=[dict(timeSec=n/24,meanLumaDelta=float(deltas[n-1])) for n in (264,528)]
    require(all(j['meanLumaDelta']<=max(.05,p99*1.5) for j in joins),'An encoded visual join is an outlier')
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(target)]))
    require(len(probe['streams'])==1 and float(probe['streams'][0]['duration'])==33,'Requires one silent 33-second stream')
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(target),'-f','null','-'],check=True)
    return dict(media=checked_file(target),frames=792,threeExactInputCycles=True,continuousEncode=True,
                continuity=dict(joins=joins,ordinaryP99=p99,maximumDelta=float(deltas.max()),
                                decodedIdenticalAdjacentPairs=int((deltas==0).sum()),humanLoopApproval=None))


def three_audio(source,target):
    with wave.open(str(source),'rb') as f:
        params=f.getparams();pcm=f.readframes(f.getnframes())
        require((f.getframerate(),f.getnchannels(),f.getnframes())==(48000,2,528000),'Native 11-second source required')
    with wave.open(str(target),'wb') as f:f.setparams(params);f.writeframes(pcm*3)
    with wave.open(str(target),'rb') as f:require(f.readframes(f.getnframes())==pcm*3,'Audio cycles changed')
    return dict(media=checked_file(target),threeExactPcmCopies=True,joins=inspect_audio(target))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('selections','visuals','audio','output'):p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();verify_no_embedded_generators();verify_approved_visuals()
    for name in ('audio','video'):component_root(name)
    require(not a.output.exists(),'Use a new review folder; preserve earlier work')
    items=json.loads(a.selections.read_text())['selections']
    for item in items:
        checked_file(item['visualSource']['media']['path'],item['visualSource']['media']['sha256'])
        checked_file(item['audioSource']['media']['path'],item['audioSource']['media']['sha256'])
    a.output.mkdir(parents=True)
    for name in ('visuals','audio','originals','provenance'):(a.output/name).mkdir()
    report=dict(schemaVersion='1.0',status='independent_component_review_pending',createdAt=datetime.now(timezone.utc).isoformat(),
                sourceSelections=checked_file(a.selections),componentLock=load_component_lock(),
                assembler=checked_file(__file__),ffmpegVersion=subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0],
                humanVisualApproval=None,humanAudioApproval=None,humanAVApproval=None,registryModified=False,
                portraits=[],fields=[])
    audio_manifests=[(m,json.loads(m.read_text())) for m in a.audio.glob('*/*.json')]
    for item in items:
        key=item['project'];portrait=dict(key=key,label=item['projectLabel'],development=[],audio=[],soundtrackOption=item['option'])
        original=Path(item['delivery']['media']['path']);checked_file(original,item['delivery']['media']['sha256'])
        dest=a.output/'originals'/original.name;shutil.copyfile(original,dest)
        portrait['original']=str(dest.relative_to(a.output))
        for strength in (100,125,150):
            source=a.visuals/f'{key}-develop-{strength}.mp4';manifest=json.loads(source.with_suffix('.json').read_text())
            checked_file(source,manifest['output']['sha256'])
            target=a.output/'visuals'/f'{key}-develop-{strength}-33s.mp4'
            verified=three_visual(source,target);verified.update(strength=strength,url=str(target.relative_to(a.output)),sourceManifest=manifest)
            portrait['development'].append(verified)
        ap,adjusted=next((m,d) for m,d in audio_manifests if d['sourceAudioId']==item['audioId'])
        require(adjusted['foregroundSamplesIdentical'] and adjusted['bedLinearGain']==.9,'Bed-only proof required')
        for kind,source in [('original',Path(item['audioSource']['media']['path'])),('bed90',Path(adjusted['output']['path']))]:
            if kind=='bed90':checked_file(source,adjusted['output']['sha256'])
            target=a.output/'audio'/f'{key}-{kind}-33s.wav';verified=three_audio(source,target)
            verified.update(kind=kind,url=str(target.relative_to(a.output)),source=checked_file(source))
            if kind=='bed90':verified['sourceManifest']=adjusted
            portrait['audio'].append(verified)
        report['portraits'].append(portrait)
        print('Review ready: '+portrait['label'],flush=True)
    for kind in ('static','wave','pressure','flow'):
        source=a.visuals/f'Infinity-field-{kind}-125.mp4';manifest=json.loads(source.with_suffix('.json').read_text())
        checked_file(source,manifest['output']['sha256'])
        target=a.output/'visuals'/f'Infinity-field-{kind}-125-33s.mp4'
        verified=three_visual(source,target);verified.update(kind=kind,url=str(target.relative_to(a.output)),sourceManifest=manifest)
        report['fields'].append(verified)
    (a.output/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    shutil.copyfile(Path(__file__).with_name('iteration_review.html'),a.output/'index.html')
    (a.output/'STATUS.md').write_text('# HPR — next iteration\n\nIndependent visual and audio comparisons. All new candidates await human review.\n\nThe original three samples and Registry approvals are preserved. These are not final application deliveries.\n\nVisuals are silent and repeat exactly three times. Audio comparisons repeat native eleven-second PCM exactly three times. Final AV assembly follows separate visual and audio selection.\n')
    checks=[checked_file(f) for f in sorted(a.output.rglob('*')) if f.is_file()]
    (a.output/'SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {Path(r['path']).relative_to(a.output)}\n" for r in checks))
    print('Completed review: '+str(a.output),flush=True)


if __name__=='__main__':main()
