# -*- coding: utf-8 -*-
"""Regenerate shot_*.mp4 clips from freshly-baked scene MP4s using shot_plan.
trim->target: take first `target` secs.  pad-freeze: baked clip + freeze last frame to `target`."""
import subprocess, json, os, sys
ROOT=r"D:\Danny\projects\animation\my_open_montage"
TMP=os.path.join(ROOT,"projects","junzheng-gaza-pursuit","renders",".compose_tmp")
VID=os.path.join(ROOT,"projects","junzheng-gaza-pursuit","assets","video")
plan=json.load(open(os.path.join(TMP,"shot_plan.json"),encoding="utf-8"))

def ff(args):
    return subprocess.run(["ffmpeg","-y","-loglevel","error",*args],capture_output=True,text=True,errors="replace")

def vfpad(base,fps=30):
    # pad-duration strategy: take full baked, then extend with frozen last frame to target
    return base

def makeshot(p):
    sid=p["scene_id"]; tgt=p["target"]; baked=p["baked"]
    src=os.path.join(VID,sid+".mp4"); out=os.path.join(TMP,f"shot_{sid}.mp4")
    if not os.path.exists(src):
        print("MISSING",src); return False
    if baked>=tgt-0.001:
        # trim to first tgt seconds
        r=ff(["-ss","0","-i",src,"-t",f"{tgt:.6f}","-an","-c","copy",out])
        ok=r.returncode==0 and r.stderr or ""
        # fast copy; if stream/re-encode needed fallback silently handled by caller check
    else:
        # pad: replay baked twice + freeze (baked<target<=2*baked typically). Use concat to reach target.
        # Simpler: tpad -1 = freeze last frame (Video Delay). Use fps filter.
        need=tgt-baked
        r=ff(["-i",src,"-vf",f"tpad=stop_mode=clone:stop_duration={need:.6f}","-r","30","-pix_fmt","yuv420p","-an",out])
        ok=r.returncode==0
    d=float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",out],capture_output=True,text=True).stdout.strip())
    hit=abs(d-tgt)<0.1
    print(f"  {sid:26s} baked={baked:7.3f} target={tgt:7.3f} mode={'trim' if baked>=tgt-0.001 else 'pad'} -> shot={d:7.3f} {'OK' if hit else 'MISMATCH'}")
    return ok and hit

if __name__=="__main__":
    only=set(sys.argv[1:]) if len(sys.argv)>1 else None
    allok=True
    for p in plan:
        if only and p["scene_id"] not in only: continue
        if not makeshot(p): allok=False
    print("ALL_OK" if allok else "SOME_FAILED")
