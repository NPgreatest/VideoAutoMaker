# from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
import os

def compose_final_video(processed_json, project_folder, output_path):
    pass
    # clips = []
    # for idx, block in enumerate(processed_json["script"]):
    #     video_path = os.path.join(project_folder, block["video"])
    #     audio_path = os.path.join(project_folder, block["audio"])
    #
    #     video = VideoFileClip(video_path)
    #     audio = AudioFileClip(audio_path)
    #
    #     video = video.set_audio(audio)
    #     clips.append(video)
    #
    # final_clip = concatenate_videoclips(clips)
    # final_clip.write_videofile(output_path, codec="libx264")