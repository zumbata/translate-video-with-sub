import os
from uuid import uuid4

import moviepy.editor as mp
from openai import OpenAI
import srt
from dotenv import load_dotenv
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import TextClip
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, filters, ApplicationBuilder

load_dotenv()


async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        'Welcome! Please send me a video or audio file and I will embed translated English subtitles.')
    await update.message.reply_text('Allowed media extentions: | .mp3 | .mp4 | .mpeg | .mpga | .m4a | .wav | .webm |')


async def handle_document(update: Update, context: CallbackContext):
    document = update.message.effective_attachment
    file_extension = os.path.splitext(document.file_name)[1].lower()
    if file_extension in ['.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm']:
        file_id = document.file_id
        new_file = await context.bot.get_file(file_id)
        media_path = f"{uuid4()}{file_extension}"
        srt_path = f"{uuid4()}.srt"
        await new_file.download_to_drive(media_path)
        output_file = f"output_{uuid4()}.mp4"
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        with open(media_path, "rb") as media_file:
            transcript = client.audio.translations.create(
                model="whisper-1",
                file=media_file,
                response_format="srt"
            )
            with open(srt_path, "w") as subsitles_file:
                subsitles_file.write(transcript)
        create_video_with_subtitles(media_path, srt_path, output_file)
        with open(output_file, 'rb') as video:
            await update.message.reply_video(
                video, caption="Here is your video with embedded subtitles: ")
        with open(srt_path, 'r') as subtitles:
            await update.message.reply_document(subtitles, caption="Here is also the .srt file: ")
        os.remove(media_path)
        os.remove(srt_path)
        os.remove(output_file)
    else:
        await update.message.reply_text(
            "Unsupported format. Try again with other format.")


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
            clip.size[0], int(clip.size[1]/8)), method='caption', bg_color='black')
        text_clip = text_clip.set_start(subtitle.start.total_seconds()).set_duration(
            (subtitle.end - subtitle.start).total_seconds())
        text_clip = text_clip.set_position(('center', 'bottom'))
        subtitle_clips.append(text_clip)
    video = mp.CompositeVideoClip(subtitle_clips + [clip])
    video.write_videofile(output_file, codec='libx264', audio_codec='aac')


if __name__ == '__main__':
    application = ApplicationBuilder().token(
        os.environ.get("TELEGRAM_TOKEN")).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(
        filters.VIDEO | filters.AUDIO, handle_document))
    application.run_polling()
