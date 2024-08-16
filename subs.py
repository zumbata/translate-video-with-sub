import os
import random
from pathlib import Path

import moviepy.editor as mp
import srt
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import TextClip
from openai import OpenAI


def create_video_with_subtitles(input_file, subtitle_file, output_file):
    file_ext = os.path.splitext(input_file)[1].lower()
    video_formats = ['.mp4', '.mpeg', '.webm']
    audio_formats = ['.mp3', '.mpga', '.m4a', '.wav']
    if file_ext in video_formats:
        clip = VideoFileClip(input_file)
    elif file_ext in audio_formats:
        clip = AudioFileClip(input_file)
        clip = clip.set_duration(clip.duration)
        clip = clip.set_fps(24)
        clip = clip.set_video_clip(mp.ColorClip(size=(1280, 720), color=(
            0, 0, 0), duration=clip.duration).set_audio(clip))
    else:
        raise ValueError(f"Unsupported file format: {file_ext}")
    with open(subtitle_file, "r") as f:
        subtitles = list(srt.parse(f.read()))
    subtitle_clips = []
    for subtitle in subtitles:
        text_clip = TextClip(subtitle.content, fontsize=24, color='white', size=(
            clip.size[0], int(clip.size[1]/8)), method='caption')
        text_clip = text_clip.set_start(subtitle.start.total_seconds()).set_duration(
            (subtitle.end - subtitle.start).total_seconds())
        text_clip = text_clip.set_position(('center', 'bottom'))
        subtitle_clips.append(text_clip)
    video = mp.CompositeVideoClip([clip] + subtitle_clips)
    video.write_videofile(output_file, codec='libx264', audio_codec='aac')


client = OpenAI()

filename = random.choice([f for f in os.listdir('.') if f.endswith(
    ('.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm'))])

with open(filename, "rb") as audio_file:
    transcript = client.audio.translations.create(
        model="whisper-1",
        file=audio_file,
        response_format="srt"
    )
    subsitles_filename = f"{Path(filename).stem}.srt"
    try:
        subsitles_file = open(subsitles_filename, "x")
    except Exception:
        subsitles_file = open(subsitles_filename, "w")
    subsitles_file.write(transcript)
    subsitles_file.close()

create_video_with_subtitles(filename, subsitles_filename,
                            f"{Path(filename).stem}-translated.mp4")
