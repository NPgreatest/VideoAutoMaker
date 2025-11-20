#!/usr/bin/env python3
from __future__ import annotations

import gradio as gr

from videogen.ui.audio_page import build_audio_page
from videogen.ui.config_page import build_config_page
from videogen.ui.create_project_page import build_create_project_page
from videogen.ui.video_page import build_video_page


def build_interface() -> gr.Blocks:
    with gr.Blocks(title="Videogen Console") as demo:
        with gr.Tab("Create Project"):
            build_create_project_page()

        with gr.Tab("Audio Pipeline"):
            build_audio_page()

        with gr.Tab("Video Pipeline"):
            build_video_page()

        with gr.Tab("Config"):
            build_config_page()

    return demo


def main() -> None:
    demo = build_interface()
    demo.queue().launch()


if __name__ == "__main__":
    main()

