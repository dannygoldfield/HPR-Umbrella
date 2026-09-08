#!/usr/bin/env python3
"""Export the latest explicitly selected HPR comparisons as shareable AV prototypes.

This is Umbrella assembly only. It never changes generators, mixes or approvals.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import wave
import zipfile

from build_review import (ROOT, checked_file, require, component_root, load_component_lock,
                          verify_no_embedded_generators, verify_approved_visuals,
                          _probe, _measure_loudness, _validate_pair, _validate_source_wav)
from prepare_selected import packets, inspect_audio, NAMES


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def resolve(record):
    base = ROOT if record['component'] == 'umbrella' else component_root(record['component'])
    path = base / record['path']
    checked_file(path, record['sha256'])
    return path


def export(item, visual_choice, visual_review_checks, output):
    visual = resolve(visual_choice['reviewVisual'])
    native_visual = resolve(visual_choice['nativeVisual'])
    visual_manifest_path = resolve(visual_choice['visualManifest'])
    visual_manifest = json.loads(visual_manifest_path.read_text())
    require(visual_manifest['output']['sha256'] == checked_file(native_visual)['sha256'], 'Native visual provenance mismatch')
    require(visual_manifest['developmentStrength'] * 100 == item['developPercent'], 'Wrong develop setting')
    require(visual_review_checks['media']['sha256'] == checked_file(visual)['sha256'], 'Review visual checks do not match selected media')
    require(visual_review_checks['threeExactInputCycles'] and visual_review_checks['continuousEncode'], 'Use the verified continuously encoded three-pass visual')
    audio = resolve(item['nativeAudio'])
    review_audio = resolve(item['reviewAudio'])
    audio_manifest_path = resolve(item['audioManifest'])
    audio_manifest = json.loads(audio_manifest_path.read_text())
    require(audio_manifest['audioId'] == item['audioCandidateId'] and audio_manifest['sourceAudioId'] == item['sourceAudioId'], 'Wrong selected soundtrack')
    require(audio_manifest['bedLinearGain'] == item['bedLinearGain'] and audio_manifest['bedReductionPercent'] == item['bedReductionPercent'], 'Wrong selected bed level')
    require(audio_manifest['foregroundSamplesIdentical'] and audio_manifest['sourceMasterGainPreserved'], 'Foreground and source master gain must be preserved')
    require(audio_manifest['durationSec'] == 11 and audio_manifest['durationBank'] == '11s', 'Native eleven-second audio required')
    require(audio_manifest['output']['sha256'] == checked_file(audio)['sha256'], 'Audio provenance mismatch')
    require(audio_manifest['loopValidation']['click_check_passed'], 'Source audio click screening failed')
    native_format = _validate_source_wav(audio, 11)
    _validate_source_wav(review_audio, 33)
    with wave.open(str(audio), 'rb') as f:
        pcm = f.readframes(f.getnframes())
    with wave.open(str(review_audio), 'rb') as f:
        require(f.readframes(f.getnframes()) == pcm * 3, 'The selected audio review must contain three unchanged native PCM cycles')
    source_probe = _probe('ffprobe', visual)
    require(len(source_probe['streams']) == 1 and source_probe['streams'][0]['codec_type'] == 'video', 'Source visual must be silent')
    source_level = _measure_loudness('ffmpeg', review_audio)
    target = output / ('HPR_' + NAMES[item['project']] + '_33s.mp4')
    command = ['ffmpeg', '-v', 'error', '-n', '-i', str(visual), '-i', str(review_audio),
               '-map', '0:v:0', '-map', '1:a:0', '-map_metadata', '-1',
               '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k', '-t', '33',
               '-movflags', '+faststart', str(target)]
    subprocess.run(command, check=True)
    probe = _probe('ffprobe', target)
    technical = _validate_pair(probe, 33)
    require(len(probe['streams']) == 2, 'Exactly one audio and one video stream required')
    for s in probe['streams']:
        require(float(s['start_time']) == 0 and float(s['duration']) == 33, 'Both streams must begin at zero and last exactly 33 seconds')
        if s['codec_type'] == 'video':
            require(s['codec_name'] == 'h264' and s['pix_fmt'] == 'yuv420p' and int(s['nb_frames']) == 792, 'Shareable 792-frame H.264 video required')
            require(all(s[k] == 'bt709' for k in ('color_space', 'color_transfer', 'color_primaries')) and s['color_range'] == 'tv', 'Preserve color metadata')
        else:
            require(s['codec_name'] == 'aac', 'Shareable AAC audio required')
    original_packets, delivered_packets = packets(visual), packets(target)
    require(original_packets == delivered_packets and len(delivered_packets) == 792, 'Video packets or presentation timestamps changed')
    times = sorted(float(p['pts_time']) for p in delivered_packets)
    require(all(abs(t-i/24) < .000002 for i,t in enumerate(times)), 'Video timeline has a gap')
    level = _measure_loudness('ffmpeg', target)
    require(abs(level['integratedLufs'] - source_level['integratedLufs']) <= .2, 'AAC encoding changed the selected audio level')
    require(level['truePeakDbfs'] <= -1, 'Audio exceeds the true-peak ceiling')
    loop = inspect_audio(target)
    require(all(j['clickScreenPassed'] for j in loop['joins']), 'An encoded audio join failed click screening')
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(target), '-f', 'null', '-'], check=True)
    for ref in (item['nativeAudio'], item['reviewAudio'], visual_choice['nativeVisual'], visual_choice['reviewVisual']):
        resolve(ref)
    for source, label in ((audio_manifest_path, 'audio'), (visual_manifest_path, 'visual')):
        shutil.copy2(source, output / 'provenance' / (item['project'] + '-' + label + '-manifest.json'))
    return dict(project=item['project'], label=item['label'], developPercent=item['developPercent'],
                bedReductionPercent=item['bedReductionPercent'], soundtrackOption=item['soundtrackOption'],
                selectedAudio=item, selectedVisual=visual_choice, visualReviewChecks=visual_review_checks,
                audioManifest=audio_manifest, nativeAudioFormat=native_format,
                sourceLoudness=source_level, outputLoudness=level, technical=technical,
                videoPacketsAndTimestampsUnchanged=True, videoTimelineContinuous=True,
                sourceAudioThreeExactPcmCycles=True, repeatedPcmSha256=hashlib.sha256(pcm*3).hexdigest(),
                audioFiltersApplied=False, audioGainChangeDb=0,
                audioEncoding='One continuous 320 kb/s AAC encode across all 33 seconds',
                audioJoinChecks=loop, fullDecodePassed=True, renderCommand=command,
                media=checked_file(target), humanFinalVisualApproval=None, humanAVLoopApproval=None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--choices', type=Path, default=ROOT/'config/radcliffe-comparison-choices-2026-09-07.json')
    parser.add_argument('--infinity-choice', type=Path, default=ROOT/'config/radcliffe-endless-rooms-direction-2026-09-07.json')
    args = parser.parse_args()
    output = args.output.resolve()
    archive = output.with_name(output.name + '.zip')
    require(not output.exists() and not archive.exists(), 'Choose a new output folder; preserve previous exports')
    verify_no_embedded_generators()
    verify_approved_visuals()
    lock = load_component_lock()
    for name in lock['components']:
        component_root(name)
    selections = json.loads(args.choices.read_text())
    direction = json.loads(args.infinity_choice.read_text())
    choice = direction['colorSpeedChoice']
    require(choice and choice['status'] == 'comparison_choice_locked', 'An explicit Infinity comparison choice is required')
    require(selections['status'] == 'comparison_choices_locked', 'Explicit develop and audio choices required')
    require({p['project'] for p in selections['portraits']} == {'10000', 'NYChildren', 'Infinity'} and len(selections['portraits']) == 3, 'Exactly three selected portraits required')
    parent_path = resolve(selections['sourceReview'])
    parent = json.loads(parent_path.read_text())
    field_path = resolve(choice['sourceReviewBeforeSelection'])
    fields = json.loads(field_path.read_text())
    registry = ROOT/'workspace/registry/hpr.sqlite3'
    registry_before = checked_file(registry) if registry.exists() else None
    output.mkdir(parents=True)
    provenance = output/'provenance'
    provenance.mkdir()
    for path, name in ((args.choices, 'develop-audio-choices.json'), (args.infinity_choice, 'infinity-choice.json'),
                       (parent_path, 'source-component-review.json'), (field_path, 'source-infinity-review.json')):
        shutil.copy2(path, provenance/name)
    report = dict(schemaVersion='1.0', status='selected_working_prototypes_for_sharing',
                  createdAt=datetime.now(timezone.utc).isoformat(), componentLock=lock,
                  selectionRecords=[checked_file(args.choices), checked_file(args.infinity_choice)],
                  assembler=checked_file(__file__), validationSources=[checked_file(Path(__file__).with_name('prepare_selected.py')), checked_file(ROOT/'tools/assemble_pair_round/assemble_pair_round.py')],
                  umbrellaCommitAtRun=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  ffmpegVersion=subprocess.check_output(['ffmpeg', '-version'], text=True).splitlines()[0],
                  registryModified=False, generatorModified=False, humanAVLoopApproval=None, portraits=[])
    for item in selections['portraits']:
        if item['project'] == 'Infinity':
            visual_choice = choice
            require(choice['developmentPercent'] == item['developPercent'] and choice['soundBedReductionPercent'] == item['bedReductionPercent'], 'Infinity selection conflicts with locked develop/audio choices')
            visual_checks = next(s['checks'] for s in fields['studies'] if s['kind'] == choice['kind'])
        else:
            visual_choice = {k:item[k] for k in ('nativeVisual', 'visualManifest', 'reviewVisual')}
            portrait = next(p for p in parent['portraits'] if p['key'] == item['project'])
            visual_checks = next(v for v in portrait['development'] if v['strength'] == item['developPercent'])
        result = export(item, visual_choice, visual_checks, output)
        report['portraits'].append(result)
        write_json(provenance/(item['project']+'-export.json'), result)
        print('Ready: ' + item['label'] + ' | ' + str(result['outputLoudness']), flush=True)
    if registry_before:
        checked_file(registry, registry_before['sha256'])
    report['registryFingerprintUnchanged'] = registry_before
    write_json(provenance/'export.json', report)
    (output/'README.txt').write_text('HOW PEOPLE RELATE\nDanny Goldfield\n\nThree current working prototypes, '+datetime.now().strftime('%B %d, %Y')+'.\n\nTo Live 10,000 Years\nNYChildren\n1 to Infinity\n\nEach video plays for 33 seconds: three consecutive eleven-second cycles. Please watch with sound.\n\nThese are the latest selected versions. Final audio/video loop review remains pending.\n')
    (provenance/'STATUS.md').write_text('# Latest selected HPR sharing prototypes\n\nThree 1080 × 1920, 24 fps, 33-second H.264/AAC MP4s. Selected picture packets and timestamps are unchanged. Selected native eleven-second audio is repeated exactly three times and encoded continuously with no filters or gain change. Full decoding, stream synchronization, source/output loudness and internal-join click screening passed. Existing visual-loop checks are preserved and apply to the identical video packets. Technical screening does not confer human final loop approval. Neither generator nor Registry was modified.\n')
    (provenance/'SHA256SUMS.txt').write_text(''.join(f"{checked_file(p)['sha256']}  {p.relative_to(output)}\n" for p in sorted(output.rglob('*')) if p.is_file()))
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_STORED) as z:
        for p in sorted(output.iterdir()):
            if p.is_file():
                z.write(p, arcname=output.name+'/'+p.name)
    with zipfile.ZipFile(archive) as z:
        require(z.testzip() is None, 'Sharing archive integrity failed')
        require(len(z.namelist()) == 4, 'Sharing archive must contain three videos and the viewing note')
    print('Sharing ZIP: '+str(archive), flush=True)


if __name__ == '__main__':
    main()
