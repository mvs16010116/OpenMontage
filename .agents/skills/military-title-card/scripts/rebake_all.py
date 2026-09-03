# -*- coding: utf-8 -*-
"""Re-bake the 19 military-title-card scenes with build_vertical.mjs (glow removed),
popup-free via CREATE_NO_WINDOW + cmd /c npx. Then probe actual durations."""
import subprocess, sys, os, glob, json, time

ROOT=r"D:\Danny\projects\animation\my_open_montage"
BUILD=os.path.join(r"C:\Users\user\AppData\Local\Temp\opencode","build_vertical.mjs")
VID=os.path.join(ROOT,"projects","junzheng-gaza-pursuit","assets","video")
HF=os.path.join(ROOT,"projects","junzheng-gaza-pursuit","hyperframes")

TC = {
 "scene_opener","scene_section_01_1","scene_section_01_2","scene_section_02_1",
 "scene_section_02_2","scene_section_02_3","scene_section_chapter_1","scene_section_03_1",
 "scene_section_04_2","scene_section_04_3","scene_section_chapter_2","scene_section_05_1",
 "scene_section_06_1","scene_section_06_2","scene_section_chapter_3","scene_section_07_2",
 "scene_section_08_1","scene_section_08_2","scene_section_08_3"}
TC = sorted(TC)

def bake(sid):
    enc=dict(capture_output=True,text=True,errors="replace")
    r=subprocess.run(["node",BUILD,"--scene",sid],cwd=ROOT,**enc)
    if r.returncode!=0:
        print("BUILD FAIL",sid,(r.stderr or "")[:500]); return False
    # render popup-free: pass one command string to cmd /c; paths have no spaces so no quotes needed
    flags=0x08000000  # CREATE_NO_WINDOW
    cline=f'npx hyperframes render {HF} -o {os.path.join(VID,sid+".mp4")} --fps 30 -q standard --workers 1 --quiet'
    r=subprocess.run(["cmd","/c",cline],cwd=ROOT,creationflags=flags,capture_output=True,text=True,errors="replace")
    ok = r.returncode==0
    print(f"  [bake] {sid} -> rc={r.returncode}", "OK" if ok else (r.stderr or "")[-400:])
    return ok

def main():
    only=set(x for x in sys.argv[1:]) if len(sys.argv)>1 else None
    for sid in TC:
        if only and sid not in only: continue
        t0=time.time()
        ok=bake(sid)
        print(f"    elapsed {time.time()-t0:.0f}s")
    # probe durations
    for sid in TC:
        p=os.path.join(VID,sid+".mp4")
        if os.path.exists(p):
            d=float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",p],capture_output=True,text=True).stdout.strip())
            print(f"  {sid} {d:.3f}")
if __name__=="__main__":
    main()
