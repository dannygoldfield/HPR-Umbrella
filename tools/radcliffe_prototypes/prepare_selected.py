#!/usr/bin/env python3
"""Freeze explicit creative selections and make three-pass application samples.

The native audio bank stays eleven seconds. This is AV delivery assembly only.
No media or review is granted final loop approval by this command.
"""
from __future__ import annotations

import argparse
from array import array
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import wave

from build_review import (ROOT, checked_file, require, latest_review, require_approval,
                          _probe, _measure_loudness, _validate_pair, _validate_source_wav,
                          component_root, load_component_lock, verify_no_embedded_generators,
                          verify_approved_visuals)
from assemble_pair_round import _stable_id

LABELS = {"10000":"To Live 10,000 Years", "NYChildren":"NYChildren", "Infinity":"1 to Infinity"}
NAMES = {"10000":"To_Live_10000_Years", "NYChildren":"NYChildren", "Infinity":"1_to_Infinity"}


def packets(path):
    return json.loads(subprocess.check_output([
        "ffprobe","-v","error","-select_streams","v:0","-show_packets",
        "-show_data_hash","sha256","-show_entries","packet=data_hash,pts_time",
        "-of","json",str(path)
    ]))["packets"]


def inspect_audio(path):
    raw = subprocess.check_output(["ffmpeg","-v","error","-i",str(path),"-map","0:a:0",
                                   "-t","33","-c:a","pcm_s16le","-f","s16le","-"])
    samples = array("h"); samples.frombytes(raw)
    if sys.byteorder != "little": samples.byteswap()
    require(len(samples) == 33*48000*2, "Decoded audio must present exactly 33 seconds")
    ordinary = Counter(max(abs(samples[n+c]-samples[n-2+c]) for c in (0,1))
                       for n in range(2,len(samples),2))
    total = sum(ordinary.values()); cumulative = 0
    for p999 in sorted(ordinary):
        cumulative += ordinary[p999]
        if cumulative >= total*.999: break
    joins = []
    for second in (11,22):
        i = second*48000*2
        step = max(abs(samples[i+c]-samples[i-2+c]) for c in (0,1))
        joins.append({"timeSec":second,"maximumStereoSampleStep":step,
                      "ordinaryStepP999":p999,"clickScreenPassed":step<=p999})
    return {"presentedFramesPerChannel":len(samples)//2,"joins":joins,
            "humanLoopApproval":False,"interpretation":"Technical screening only; human listening must confirm invisible joins."}


def render_three_passes(visual, audio, destination):
    command = ["ffmpeg","-v","error","-n","-stream_loop","2","-i",visual["media"]["path"],
               "-stream_loop","2","-i",audio["media"]["path"],"-map","0:v:0","-map","1:a:0",
               "-c:v","copy","-c:a","aac","-b:a","320k","-t","33","-movflags","+faststart",str(destination)]
    subprocess.run(command,check=True)
    probe = _probe("ffprobe",destination); technical = _validate_pair(probe,33)
    require(len(probe["streams"]) == 2, "Exactly two AV streams required")
    for stream in probe["streams"]:
        require(float(stream["start_time"]) == 0 and float(stream["duration"]) == 33,
                "Both streams must start at zero and last exactly 33 seconds")
        if stream["codec_type"] == "video":
            require(int(stream["nb_frames"]) == 792, "Three passes require 792 video frames")
            require(all(stream[k] == "bt709" for k in ("color_space","color_transfer","color_primaries"))
                    and stream["color_range"] == "tv", "Color metadata must stay unchanged")
    source_packets = packets(visual["media"]["path"]); delivery_packets = packets(destination)
    require([p["data_hash"] for p in delivery_packets] == [p["data_hash"] for p in source_packets]*3,
            "Delivery must contain three exact copies of the approved video packets")
    times = sorted(float(p["pts_time"]) for p in delivery_packets)
    require(all(abs(t-i/24)<.000002 for i,t in enumerate(times)), "Video presentation timeline contains a gap")
    with wave.open(audio["media"]["path"],"rb") as source:
        expected_pcm = source.readframes(source.getnframes())*3
    repeated_pcm = subprocess.check_output(["ffmpeg","-v","error","-stream_loop","2","-i",audio["media"]["path"],
                                            "-map","0:a:0","-c:a","pcm_s16le","-f","s16le","-"])
    require(repeated_pcm == expected_pcm, "Audio delivery input is not exactly three source cycles")
    level = _measure_loudness("ffmpeg",destination)
    require(abs(level["integratedLufs"]-audio["loudness"]["integratedLufs"])<=.2,
            "Continuous delivery changed approved loudness")
    require(level["truePeakDbfs"]<=-1, "Delivery true peak exceeds ceiling")
    subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(destination),"-f","null","-"],check=True)
    for component in (visual,audio): checked_file(component["media"]["path"],component["media"]["sha256"])
    return {"media":checked_file(destination),"technical":technical,"videoFrameCount":792,
            "videoPacketsThreeExactCopies":True,"videoTimelineContinuous":True,
            "audioInputThreeExactCopies":True,"repeatedPcmSha256":hashlib.sha256(expected_pcm).hexdigest(),
            "audioEncoding":"one continuous 320 kb/s AAC encode across all 33 seconds",
            "audioFiltersApplied":False,"audioGainChangeDb":0,"loudness":level,
            "loopChecks":inspect_audio(destination),"renderCommand":command}


def register_pending(db, items, now):
    """Append creative decisions, reserving audio without final loop approval."""
    with db:
        for item in items:
            pair = db.execute("SELECT * FROM pair_candidates WHERE pair_id=?",(item["pairId"],)).fetchone()
            require(pair is None, "Pair already registered; preserve its history and inspect before changing it")
            require(db.execute("SELECT status FROM audio_candidates WHERE audio_id=?",(item["audioId"],)).fetchone()[0] == "banked",
                    "Selected soundtrack is no longer available")
            db.execute("INSERT INTO pair_candidates(pair_id,experiment_id,portrait_id,visual_id,audio_id,media_path,manifest_path,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                       (item["pairId"],"radcliffe-selected-loop-pending-20260906",item["portraitId"],item["visualId"],item["audioId"],
                        item["elevenSecondReference"]["path"],item["manifestPath"],"selected_loop_pending",now))
            db.execute("INSERT INTO candidate_reviews(subject_kind,subject_id,rating,rejected,selected,notes,created_at) VALUES('pair',?,NULL,0,1,?,?)",
                       (item["pairId"],f"User selected {item['projectLabel']}: option {item['option']}. Creative pairing is complete. User reported audible loops in the 11-second review. Final loop approval is pending; requested delivery is three consecutive passes / 33 seconds.",now))
            db.execute("UPDATE audio_candidates SET status='reserved_loop_pending' WHERE audio_id=?",(item["audioId"],))
            db.execute("INSERT INTO final_masters(master_id,portrait_id,revision_id,visual_id,audio_id,pair_id,media_path,manifest_path,status,approved_at,created_at) VALUES(?,?,?,?,?,?,?,?,?,NULL,?)",
                       (item["masterId"],item["portraitId"],item["revisionId"],item["visualId"],item["audioId"],item["pairId"],
                        item["delivery"]["media"]["path"],item["manifestPath"],"loop_pending",now))


def write_page(output, items):
    cards = []
    for item in items:
        file = Path(item["delivery"]["media"]["path"]).name
        cards.append(f'<section><h2>{item["projectLabel"]}</h2><p>Selected soundtrack: option {item["option"]}</p><video controls playsinline preload="metadata" src="{file}"></video><p><a href="{file}" download>Download 33-second MP4</a></p></section>')
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>HPR · Three selected prototypes</title>
<style>body{font:16px system-ui,sans-serif;background:#f4f2eb;color:#292d25;margin:0;padding:26px}main{max-width:1080px;margin:auto}h1{font-size:27px;font-weight:550}h2{font-size:19px}p{line-height:1.5;color:#5b6253}.status{background:#e5eadb;padding:13px 16px;border-radius:5px}article{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}video{width:100%;max-height:62vh;background:#171b16}a{color:#334d35}@media(max-width:730px){article{grid-template-columns:1fr}video{max-height:65vh}}</style>
<main><h1>How People Relate · Radcliffe Yard samples</h1><p class="status"><strong>Creative selections complete · Audio loop verification pending</strong></p><p>Each sample plays three consecutive eleven-second passes, then stops at 33 seconds. Listen through the joins at 11 and 22 seconds. The chosen visuals and soundtrack mixes are unchanged; audio is encoded continuously across all three passes.</p><article>'''+''.join(cards)+'''</article><p>Technical join checks do not replace your listening judgment. These files remain pending until you confirm the joins are inaudible.</p><p><a href="selections.json">Selections and full provenance</a> · <a href="STATUS.md">Production status</a></p></main></html>'''
    (output/"index.html").write_text(html)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--selection",action="append",required=True,help="Explicit user choice: PROJECT=OPTION")
    parser.add_argument("--db",type=Path,default=ROOT/"workspace/registry/hpr.sqlite3")
    parser.add_argument("--no-register",action="store_true",help="Reproduce delivery artifacts without duplicating Registry decisions")
    args=parser.parse_args(); choices={}
    for text in args.selection:
        project,option=text.split("=",1);require(project not in choices,"Duplicate portrait selection");choices[project]=int(option)
    require(set(choices)==set(LABELS),"Supply one explicit choice for each of the three portraits")
    require(len(set(choices.values()))==3,"Use three distinct soundtrack options")
    require(not args.output.exists(),"Use a new output folder; do not overwrite earlier prototypes")
    verify_no_embedded_generators();lock=load_component_lock()
    for name in lock["components"]:component_root(name)
    verify_approved_visuals()
    review=json.loads((args.review/"provenance.json").read_text())
    read_db=sqlite3.connect(args.db.resolve().as_uri()+"?mode=ro",uri=True);read_db.row_factory=sqlite3.Row
    selected=[]
    for project,option in choices.items():
        pair=next(p for p in review["pairs"] if p["project"]==project and p["option"]==option)
        visual=next(v for v in review["visuals"] if v["id"]==pair["visualId"])
        audio=next(a for a in review["audio"] if a["id"]==pair["audioId"])
        require_approval(latest_review(read_db,"audio",audio["id"]),audio["id"])
        require_approval(latest_review(read_db,"visual",visual["id"]),visual["id"])
        for component in (visual,audio):
            checked_file(component["media"]["path"],component["media"]["sha256"])
            checked_file(component["manifest"]["path"],component["manifest"]["sha256"])
        _validate_source_wav(Path(audio["media"]["path"]),11)
        checked_file(pair["media"]["path"],pair["media"]["sha256"])
        selected.append((project,option,pair,visual,audio))
    read_db.close();args.output.mkdir(parents=True);refs=args.output/"11-second-selected-references";refs.mkdir()
    now=datetime.now(timezone.utc).isoformat();items=[]
    for project,option,pair,visual,audio in selected:
        reference=refs/f"HPR_{NAMES[project]}_11s.mp4";shutil.copyfile(pair["media"]["path"],reference)
        delivery=render_three_passes(visual,audio,args.output/f"HPR_{NAMES[project]}_33s.mp4")
        pair_id=_stable_id("PAIR",visual["id"],audio["id"])
        manifest=args.output/f"HPR_{NAMES[project]}_33s.json"
        item={"project":project,"projectLabel":LABELS[project],"option":option,
              "pairId":pair_id,"masterId":_stable_id("MASTER",pair_id,"33-second-application"),
              "portraitId":visual["portraitId"],"revisionId":visual["revisionId"],"visualId":visual["id"],"audioId":audio["id"],
              "creativeApproval":"user confirmed selection","audioLoopApproval":"pending",
              "nativeCycleDurationSec":11,"deliveryDurationSec":33,"repeatCount":3,
              "durationFamilyPolicy":"Three passes for AV delivery; no 33-second audio-bank family is created",
              "visualSource":visual,"audioSource":audio,"priorElevenSecondReview":pair,
              "elevenSecondReference":checked_file(reference,pair["media"]["sha256"]),"delivery":delivery,
              "manifestPath":str(manifest.resolve()),"createdAt":now}
        manifest.write_text(json.dumps(item,indent=2)+"\n");items.append(item)
        print(f"Verified {LABELS[project]}: option {option}, 33 seconds",flush=True)
    report={"status":"creative_complete_audio_loop_pending","createdAt":now,"componentLock":lock,
            "assemblyTool":checked_file(__file__),"assemblyHelpers":checked_file(Path(__file__).with_name("build_review.py")),
            "ffmpegVersion":subprocess.check_output(["ffmpeg","-version"],text=True).splitlines()[0],
            "selections":items}
    (args.output/"selections.json").write_text(json.dumps(report,indent=2)+"\n")
    write_page(args.output,items)
    status="# HPR — selected Radcliffe Yard prototypes\n\n**Creative selections complete. Audio loop verification pending.**\n\n"
    status+="\n".join(f"- {i['projectLabel']}: option {i['option']} — 33 seconds, three exact eleven-second passes." for i in items)
    status+="\n\nBoth generators and all original media remain unchanged. The 33-second delivery repeats each approved visual stream exactly three times and encodes the unaltered, repeated source WAV in one continuous AAC pass. This removes player restarts and separate-clip encoder boundaries at 11 and 22 seconds. Human listening approval is still required.\n\nThe selected eleven-second review files are preserved in the reference subfolder. These prototypes are not marked approved for release.\n"
    (args.output/"STATUS.md").write_text(status)
    if not args.no_register:
        db=sqlite3.connect(args.db);db.row_factory=sqlite3.Row;db.execute("PRAGMA foreign_keys=ON")
        backup=sqlite3.connect(args.output/"registry-before-selections.sqlite3");db.backup(backup);backup.close()
        register_pending(db,items,now);db.close()
        print("Recorded creative selections; reserved soundtracks; all three masters remain loop_pending.")


if __name__=="__main__":main()
