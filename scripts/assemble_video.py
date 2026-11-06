"""Assemble genuine report/runtime-check captures with locally generated narration."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import wave


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenes', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root, output = Path(args.scenes).resolve(), Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    durations = []
    with wave.open(str(root / 'narration.wav'), 'wb') as result:
        for index in range(6):
            with wave.open(str(root / f'voice{index}.wav'), 'rb') as source:
                if index == 0: result.setparams(source.getparams())
                result.writeframes(source.readframes(source.getnframes()))
                silence = int(source.getframerate() * 0.6)
                result.writeframes(b'\x00' * silence * source.getsampwidth() * source.getnchannels())
                durations.append(source.getnframes() / source.getframerate() + 0.6)
    total = sum(durations)
    if total >= 90: raise ValueError(f'Demo exceeds hackathon limit: {total}')
    concat = root / 'scenes.txt'
    lines = []
    for index, seconds in enumerate(durations):
        lines += [f"file 'scene{index}.png'", f'duration {seconds:.3f}']
    lines += ["file 'scene5.png'"]
    concat.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg: raise ValueError('FFmpeg is required for video assembly')
    result = subprocess.run([ffmpeg, '-y', '-hide_banner', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(concat),
        '-i', str(root / 'narration.wav'), '-vf', 'scale=1440:1000,format=yuv420p', '-r', '24', '-c:v', 'libx264',
        '-preset', 'veryfast', '-crf', '22', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', '-t', f'{total:.3f}', str(output)],
        stdin=subprocess.DEVNULL, check=True, timeout=90, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    print(json.dumps({'video': str(output), 'duration_seconds': round(total, 2), 'scenes': 6, 'kind': 'narrated walkthrough of genuine report and recorded runtime-check results'}, indent=2))


if __name__ == '__main__': main()
