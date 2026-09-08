"""Append independently rendered 175/200% visuals to an existing private review."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from build_iteration_review import three_visual, frame_hashes
from build_review import (checked_file, require, component_root, load_component_lock,
                          verify_approved_visuals, verify_no_embedded_generators)


def verify_inventory(root):
    entries=[]
    for line in (root/'SHA256SUMS.txt').read_text().splitlines():
        digest,name=line.split('  ',1)
        path=(root/name).resolve()
        require(path.is_relative_to(root),'Inventory path outside review')
        entries.append(checked_file(path,digest))
    return entries


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--review',type=Path,required=True)
    p.add_argument('--visuals',type=Path,required=True)
    a=p.parse_args();root=a.review.resolve()
    verify_no_embedded_generators();verify_approved_visuals()
    for name in ('audio','video'):component_root(name)
    inventory=verify_inventory(root)
    report=json.loads((root/'review.json').read_text())
    require(len(report['portraits'])==3,'Expected the existing three-portrait review')
    sources=[]
    for portrait in report['portraits']:
        require({v['strength'] for v in portrait['development']}=={100,125,150},'Review already extended or unexpected strengths')
        parent=portrait['development'][-1]['sourceManifest']['parentManifest']
        for strength in (175,200):
            path=a.visuals/f"{portrait['key']}-develop-{strength}.mp4"
            manifest=json.loads(path.with_suffix('.json').read_text())
            require(manifest['developmentStrength']==strength/100,'Wrong development strength')
            require(manifest['parentManifest']==parent,'Photograph or original recipe changed')
            require(manifest['numberField']=='static' and manifest['audio']=='none' and not manifest['grain'],'Unexpected visual change')
            require(manifest['losslessNativeMaster'] and manifest['frames']==264 and manifest['durationSec']==11,'Requires lossless native eleven-second visual')
            require(manifest['humanLoopApproval'] is None,'Experimental sources must remain pending review')
            checked_file(path,manifest['output']['sha256'])
            for name in ('generatorCode','developmentSource','sourceRecipe'):
                checked_file(manifest[name]['path'],manifest[name]['sha256'])
            for source in manifest['inputs']:checked_file(source['path'],source['sha256'])
            sources.append((portrait,strength,path,manifest))
    snapshot=root/'provenance/development-through-150'
    destination=root/'visuals/develop-175-200'
    require(not snapshot.exists() and not destination.exists(),'Preserve the existing extension; use a fresh review to repeat this operation')
    snapshot.mkdir(parents=True);destination.mkdir()
    for name in ('index.html','review.json','STATUS.md','SHA256SUMS.txt'):
        shutil.copyfile(root/name,snapshot/name)
    extension=dict(createdAt=datetime.now(timezone.utc).isoformat(),
                   predecessor=checked_file(snapshot/'review.json'),
                   componentLock=load_component_lock(),assembler=checked_file(__file__),
                   reviewTemplate=checked_file(Path(__file__).with_name('iteration_review.html')),
                   strengths=[175,200],preservedMedia=[],humanVisualApproval=None,registryModified=False)
    for portrait,strength,source,manifest in sources:
        target=destination/f"{portrait['key']}-develop-{strength}-33s.mp4"
        verified=three_visual(source,target)
        if verified['continuity']['decodedIdenticalAdjacentPairs']:
            hashes=frame_hashes(target)
            identical=sum(a==b for a,b in zip(hashes,hashes[1:]))
            require(identical==0,'A full-resolution decoded development hold was introduced')
            verified['continuity']['fullResolutionIdenticalAdjacentPairs']=identical
            verified['continuity']['proxyDuplicatesResolvedAtFullResolution']=True
        verified.update(strength=strength,url=str(target.relative_to(root)),sourceManifest=manifest,
                        sourceManifestFile=checked_file(source.with_suffix('.json')))
        portrait['development'].append(verified)
        print(f"Verified {portrait['label']}: {strength}%",flush=True)
    # Recheck every original file before replacing only the review documents.
    for item in inventory:checked_file(item['path'],item['sha256'])
    extension['preservedMedia']=[i for i in inventory if Path(i['path']).suffix in ('.mp4','.wav')]
    report.setdefault('extensions',[]).append(extension)
    report['defaultDevelopStrength']=150
    report['tentativeDevelopPreference']={'strength':150,'appliesTo':'all three portraits','approved':False}
    temporary=root/'review.next.json'
    temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(root/'review.json')
    shutil.copyfile(Path(__file__).with_name('iteration_review.html'),root/'index.next.html')
    (root/'index.next.html').replace(root/'index.html')
    with (root/'STATUS.md').open('a') as f:
        f.write('\n175% and 200% develop comparisons have been added for all three portraits. 150% is a tentative preference and the starting preview, not a selection or approval. All earlier media, audio comparisons, number-field comparisons, and browser draft choices are preserved. Each new silent sample contains three native eleven-second passes, encoded continuously to 33 seconds.\n')
    checks=[checked_file(f) for f in sorted(root.rglob('*')) if f.is_file() and f!=root/'SHA256SUMS.txt']
    temporary=root/'SHA256SUMS.next.txt'
    temporary.write_text(''.join(f"{r['sha256']}  {Path(r['path']).relative_to(root)}\n" for r in checks))
    temporary.replace(root/'SHA256SUMS.txt')
    print('Extended review: '+str(root),flush=True)


if __name__=='__main__':main()
