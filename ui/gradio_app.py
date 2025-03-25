import os

import gradio as gr

from engine.audio_generator import generate_tts_audio
from engine.video_generator import generate_video_clip
from engine.composer import compose_final_video
from engine.project_manager import create_project, save_json, load_json
from engine.text_parser import split_script_to_chunks

projects_dir = "projects"

with gr.Blocks() as demo:
    with gr.Tab("Stage 1: Create Project"):
        project_name = gr.Textbox(label="Project Name")
        script_input = gr.Textbox(label="Paste Script", lines=10)
        create_btn = gr.Button("Create Project")
        output = gr.Textbox(label="Status")

        def create_fn(name, script):
            path = create_project(name)
            chunks = split_script_to_chunks(script)
            json_data = {"title": name, "script": [ {"text": c} for c in chunks ]}
            save_json(json_data, os.path.join(path, "input.json"))
            return f"Created project '{name}' with {len(chunks)} chunks."

        create_btn.click(create_fn, inputs=[project_name, script_input], outputs=[output])

    with gr.Tab("Stage 2: Generate Media"):
        project_selector = gr.Dropdown(label="Select Project", choices=os.listdir(projects_dir))
        reGen_checkbox = gr.Checkbox(label="Regenerate Media (audio/video)", value=True)
        generate_btn = gr.Button("Generate Audio & Video")
        gen_status = gr.Textbox(label="Generation Status")


        def generate_media(project_name, reGen):
            project_path = os.path.join(projects_dir, project_name)
            input_path = os.path.join(project_path, "input.json")
            data = load_json(input_path)
            generate_video_clip(data, project_path, reGen=reGen)
            generate_tts_audio(data, project_path, reGen=reGen)
            save_json(data, os.path.join(project_path, "processed.json"))
            return f"Media generated for project: {project_name} (Regenerate: {reGen})"


        generate_btn.click(generate_media, inputs=[project_selector, reGen_checkbox], outputs=[gen_status])

    with gr.Tab("Stage 3: Compose Video"):
        final_selector = gr.Dropdown(label="Select Project", choices=os.listdir(projects_dir))
        compose_btn = gr.Button("Compose Final Video")
        compose_output = gr.Textbox(label="Compose Status")

        def compose(project_name):
            project_path = os.path.join(projects_dir, project_name)
            data = load_json(os.path.join(project_path, "processed.json"))
            output_path = os.path.join(project_path, "final", "output.mp4")
            compose_final_video(data, project_path, output_path)
            return f"Final video created at: {output_path}"

        compose_btn.click(compose, inputs=[final_selector], outputs=[compose_output])



def launch_app():
    demo.launch()