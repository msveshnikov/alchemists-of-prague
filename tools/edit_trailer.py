"""Cut the Movie Maker recording of scripts/cinematic.gd into the trailer and lay in the music.

usage: python tools/edit_trailer.py <recording.avi> <recording.log> <out.mp4>

The log holds the "CINE cut <name> frame <n> drawn <d> t <s>" lines; the recording starts at drawn frame 0,
so every cut is at drawn/30 seconds in the AVI. Game audio (steps, swords, glass, crowd, crickets) comes
from the recording; the music bus was muted while recording and the score is mixed here.
"""
import re
import subprocess
import sys

FPS = 30.0
rec, log, out = sys.argv[1], sys.argv[2], sys.argv[3]
cuts = {}
end = None
for line in open(log, encoding="utf-8", errors="replace"):
    m = re.search(r"CINE cut (\w+) frame \d+ drawn (\d+)", line)
    if m:
        cuts[m.group(1)] = int(m.group(2)) / FPS
    m = re.search(r"CINE end", line)
    if m:
        end = True
probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", rec],
                       capture_output=True, text=True)
rec_len = float(probe.stdout.strip())
t0 = cuts.get("establish", min(cuts.values()))
t_end = rec_len - 0.1
dur = t_end - t0
# shots shorter than MIN_SHOT (e.g. an orbit whose foes all fell at once) would only flash by: drop them
MIN_SHOT = 1.0
order = sorted(cuts.items(), key=lambda kv: kv[1])
keep = []
for i, (name, st) in enumerate(order):
    en = order[i + 1][1] if i + 1 < len(order) else t_end
    if st < t0:
        continue
    if en - st < MIN_SHOT and i + 1 < len(order):
        print("dropping short shot", name, round(en - st, 2))
        continue
    if keep and abs(keep[-1][1] - st) < 1e-6:
        keep[-1] = (keep[-1][0], en)
    else:
        keep.append((st, en))


def out_time(t):
    """recording time -> time in the edited trailer"""
    acc = 0.0
    for a, b in keep:
        if t < b:
            return acc + max(0.0, t - a)
        acc += b - a
    return acc


dur = sum(b - a for a, b in keep)
rel = {k: out_time(v) for k, v in cuts.items()}
print("cuts (s in trailer):", {k: round(v, 2) for k, v in rel.items()}, "total", round(dur, 2))

tl = rel.get("timelapse", 0.0)
fight = rel["fight_wide"]
fin = rel["finale"]
town = "assets/audio/music/town_theme.mp3"
battle = "assets/audio/music/battle_theme.mp3"

# music: town theme -> (time-lapse) -> battle theme -> (finale) -> town theme ending, then fade out
town_out = tl + 3.0           # town theme fades during the sunset
battle_in = tl + 2.0
battle_out = fin + 1.5
fin_in = fin - 0.5
fade_end = 2.5

af = []
af.append(f"[1:a]atrim=0:{town_out + 0.1},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1.5,"
          f"afade=t=out:st={town_out - 3.0}:d=3.0,volume=0.55[m1]")
af.append(f"[2:a]atrim=12:{12 + battle_out - battle_in + 0.1},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=2.5,"
          f"afade=t=out:st={battle_out - battle_in - 2.0}:d=2.0,volume=0.5,adelay={int(battle_in * 1000)}:all=1[m2]")
fin_len = dur - fin_in
af.append(f"[3:a]atrim=74:{74 + fin_len + 0.1},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=2.0,"
          f"afade=t=out:st={fin_len - fade_end - 0.5}:d={fade_end},volume=0.6,adelay={int(fin_in * 1000)}:all=1[m3]")
n = len(keep)
segs = "".join(f"[vs{i}]trim={a}:{b},setpts=PTS-STARTPTS[v{i}];[as{i}]atrim={a}:{b},asetpts=PTS-STARTPTS[a{i}];"
               for i, (a, b) in enumerate(keep))
pre = (f"[0:v]split={n}" + "".join(f"[vs{i}]" for i in range(n)) + ";" +
       f"[0:a]asplit={n}" + "".join(f"[as{i}]" for i in range(n)) + ";" + segs +
       "".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vcat][acat]")
af.append(f"[acat]volume=3.0,"
          f"acompressor=threshold=0.12:ratio=4:attack=5:release=180:makeup=1.5,afade=t=in:st=0:d=0.8,"
          f"afade=t=out:st={dur - fade_end}:d={fade_end}[g]")
af.append("[g][m1][m2][m3]amix=inputs=4:duration=first:normalize=0,alimiter=limit=0.95,"
          "loudnorm=I=-15:TP=-1.5:LRA=11[a]")
vf = (f"[vcat]fade=t=in:st=0:d=1.0,"
      f"fade=t=out:st={dur - fade_end}:d={fade_end},format=yuv420p[v]")
cmd = ["ffmpeg", "-y", "-v", "error", "-i", rec, "-i", town, "-i", battle, "-i", town,
       "-filter_complex", ";".join([pre, vf] + af), "-map", "[v]", "-map", "[a]",
       "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high", "-r", "30",
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out]
print(" ".join(cmd))
subprocess.run(cmd, check=True)
