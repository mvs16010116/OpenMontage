# -*- coding: utf-8 -*-
"""Recompose final.mp4: concat new shot clips -> silent base -> burn subtitles (force_style ASS white)
-> mux narration_mix.m4a. Order from static concat list (shots regenerated in place)."""
import subprocess, os, glob
ROOT=r"D:\Danny\projects\animation\my_open_montage"
PROJ=os.path.join(ROOT,"projects","junzheng-gaza-pursuit")
HF=os.path.join(PROJ,"hyperframes")
TMP=os.path.join(PROJ,"renders",".compose_tmp")
REND=os.path.join(PROJ,"renders")
SUB=os.path.join(PROJ,"assets","subtitles.ass")
AUD=os.path.join(TMP,"narration_mix.m4a")

def ff(args):
    r=subprocess.run(["ffmpeg","-y","-loglevel","error",*args],capture_output=True,text=True,errors="replace")
    return r

concat_list=os.path.join(TMP,"concat.txt")
base=os.path.join(TMP,"_base_silent.mp4")
master=os.path.join(TMP,"_video_master.mp4")

# 1) concat shots -> silent base (use -c copy since all shots are h264 yuv420p)
r=ff(["-f","concat","-safe","0","-i",concat_list,"-c","copy",base]); print("concat:",r.returncode,r.stderr[-200:] if r.returncode else "OK")

SUBWIN=SUB.replace("\\","/").replace(":","\\:")
force=(f"subtitles='{SUBWIN}':force_style='FontName=MS YaHei,FontSize=42,Bold=0,"
       f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=0,MarginV=288,Alignment=2'")
# 2) burn subtitles (re-encode h264, crf ~20) -> master
r=ff(["-i",base,"-vf",force,"-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p","-an",master])
print("burn:",r.returncode, r.stderr[-400:] if r.returncode else "OK")

# 3) mux narration -> final.mp4
r=ff(["-i",master,"-i",AUD,"-c:v","copy","-c:a","aac","-shortest",os.path.join(REND,"final.mp4")])
print("mux:",r.returncode, r.stderr[-300:] if r.returncode else "OK")

# also update video_master.mp4 (silent subtitled master)
r=ff(["-y","-i",master,"-c","copy",os.path.join(REND,"video_master.mp4")])
print("master_copy:",r.returncode, r.stderr[-200:] if r.returncode else "OK")

# probe final
for f in ["final.mp4","video_master.mp4"]:
    d=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",os.path.join(REND,f)],capture_output=True,text=True).stdout.strip()
    sz=os.path.getsize(os.path.join(REND,f))
    print(f"  {f}: dur={d} size={sz}")
