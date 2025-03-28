import os
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips

def compose_final_video(processed_json, project_folder, output_path):
    video_clips = []

    for i, block in enumerate(processed_json["script"]):
        video_path = os.path.join(project_folder, block.get("video", ""))
        audio_path = os.path.join(project_folder, block.get("audio", ""))

        if not os.path.exists(video_path) or not os.path.exists(audio_path):
            print(f"⚠️ Skipping clip {i + 1} due to missing video or audio.")
            continue

        try:
            video_clip = VideoFileClip(video_path)
            audio_clip = AudioFileClip(audio_path)

            # Repeat video if it's shorter than audio
            if video_clip.duration < audio_clip.duration:
                repeat_count = int(audio_clip.duration // video_clip.duration) + 1
                repeated_clip = concatenate_videoclips([video_clip] * repeat_count)
                video_clip = repeated_clip.subclip(0, audio_clip.duration)
            else:
                video_clip = video_clip.subclip(0, audio_clip.duration)

            # Attach audio
            final_clip = video_clip.set_audio(audio_clip)
            video_clips.append(final_clip)

            print(f"✅ Processed clip {i + 1}")

        except Exception as e:
            print(f"❌ Error processing clip {i + 1}: {e}")

    if not video_clips:
        print("❌ No valid clips to compose.")
        return

    try:
        final_video = concatenate_videoclips(video_clips, method="compose")

        # Ensure output folder exists
        final_folder = os.path.dirname(output_path)
        os.makedirs(final_folder, exist_ok=True)

        # final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")

        final_video.write_videofile(
            output_path,
            codec="h264_videotoolbox",  # macOS GPU encoder
            audio_codec="aac",
            ffmpeg_params=["-pix_fmt", "yuv420p"]
        )

        print(f"🎬 Final video saved to: {output_path}")
    except Exception as e:
        print(f"❌ Error during final video composition: {e}")
