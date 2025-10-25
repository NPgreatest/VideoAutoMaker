import gradio as gr
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import shutil
from datetime import datetime

class ProjectBrowser:
    def __init__(self, project_root: str = "./project"):
        self.project_root = Path(project_root)
        self.current_project = None
        self.current_data = None
        self.current_block_index = 0
        
    def get_available_projects(self) -> List[str]:
        """Get list of available projects"""
        if not self.project_root.exists():
            return []
        
        projects = []
        for item in self.project_root.iterdir():
            if item.is_dir() and (item / f"{item.name}.json").exists():
                projects.append(item.name)
        return sorted(projects)
    
    def load_project(self, project_name: str) -> Tuple[bool, str]:
        """Load a project JSON file"""
        try:
            json_path = self.project_root / project_name / f"{project_name}.json"
            if not json_path.exists():
                return False, f"Project file not found: {json_path}"
            
            with open(json_path, 'r', encoding='utf-8') as f:
                self.current_data = json.load(f)
            
            self.current_project = project_name
            return True, f"Successfully loaded project: {project_name}"
        except Exception as e:
            return False, f"Error loading project: {str(e)}"
    
    def get_block_info(self, block_index: int) -> Dict:
        """Get information about a specific block"""
        if not self.current_data or block_index >= len(self.current_data.get('script', [])):
            return {}
        
        block = self.current_data['script'][block_index]
        return {
            'id': block.get('id', ''),
            'text': block.get('text', ''),
            'prompt': block.get('prompt', ''),
            'context': block.get('context', ''),
            'decision_method': block.get('decision', {}).get('method', ''),
            'decision_confidence': block.get('decision', {}).get('confidence', 0),
            'status': block.get('status', ''),
            'generation_ok': block.get('generation', {}).get('ok', False),
            'audio_generation_ok': block.get('audioGeneration', {}).get('ok', False),
            'video_path': self._get_video_path(block),
            'audio_path': self._get_audio_path(block),
            'srt_path': self._get_srt_path(block)
        }
    
    def _get_video_path(self, block: Dict) -> Optional[str]:
        """Get video file path for a block"""
        generation = block.get('generation', {})
        if generation.get('ok') and generation.get('meta', {}).get('output_path'):
            video_path = self.project_root / self.current_project / generation['meta']['output_path']
            if video_path.exists():
                return str(video_path)
        return None
    
    def _get_audio_path(self, block: Dict) -> Optional[str]:
        """Get merged audio file path for a block"""
        audio_gen = block.get('audioGeneration', {})
        if audio_gen.get('ok') and audio_gen.get('meta', {}).get('merged'):
            audio_path = self.project_root / self.current_project / audio_gen['meta']['merged']
            if audio_path.exists():
                return str(audio_path)
        return None
    
    def _get_srt_path(self, block: Dict) -> Optional[str]:
        """Get subtitle file path for a block"""
        audio_gen = block.get('audioGeneration', {})
        if audio_gen.get('ok') and audio_gen.get('meta', {}).get('srt'):
            srt_path = self.project_root / self.current_project / audio_gen['meta']['srt']
            if srt_path.exists():
                return str(srt_path)
        return None
    
    def update_block(self, block_index: int, text: str, prompt: str, context: str) -> Tuple[bool, str]:
        """Update a block's text, prompt, and context"""
        if not self.current_data or block_index >= len(self.current_data.get('script', [])):
            return False, "Invalid block index"
        
        try:
            # Update the block
            self.current_data['script'][block_index]['text'] = text
            self.current_data['script'][block_index]['prompt'] = prompt
            self.current_data['script'][block_index]['context'] = context
            
            # Update timestamp
            self.current_data['updated_at'] = datetime.now().isoformat() + "+00:00"
            
            return True, "Block updated successfully"
        except Exception as e:
            return False, f"Error updating block: {str(e)}"
    
    def delete_generation(self, block_index: int) -> Tuple[bool, str]:
        """Delete generation data for a block"""
        if not self.current_data or block_index >= len(self.current_data.get('script', [])):
            return False, "Invalid block index"
        
        try:
            # Remove generation data
            if 'generation' in self.current_data['script'][block_index]:
                del self.current_data['script'][block_index]['generation']
            
            # Update timestamp
            self.current_data['updated_at'] = datetime.now().isoformat() + "+00:00"
            
            return True, "Generation data deleted successfully"
        except Exception as e:
            return False, f"Error deleting generation: {str(e)}"
    
    def delete_audio_generation(self, block_index: int) -> Tuple[bool, str]:
        """Delete audio generation data for a block"""
        if not self.current_data or block_index >= len(self.current_data.get('script', [])):
            return False, "Invalid block index"
        
        try:
            # Remove audio generation data
            if 'audioGeneration' in self.current_data['script'][block_index]:
                del self.current_data['script'][block_index]['audioGeneration']
            
            # Update timestamp
            self.current_data['updated_at'] = datetime.now().isoformat() + "+00:00"
            
            return True, "Audio generation data deleted successfully"
        except Exception as e:
            return False, f"Error deleting audio generation: {str(e)}"
    
    def save_project(self) -> Tuple[bool, str]:
        """Save the current project to file"""
        if not self.current_data or not self.current_project:
            return False, "No project loaded"
        
        try:
            json_path = self.project_root / self.current_project / f"{self.current_project}.json"
            
            # Create backup
            backup_path = json_path.with_suffix('.json.backup')
            if json_path.exists():
                shutil.copy2(json_path, backup_path)
            
            # Save updated data
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.current_data, f, ensure_ascii=False, indent=2)
            
            return True, f"Project saved successfully. Backup created at {backup_path}"
        except Exception as e:
            return False, f"Error saving project: {str(e)}"

# Initialize the browser
browser = ProjectBrowser()

def create_interface():
    with gr.Blocks(title="VideoGen Project Browser", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# VideoGen Project Browser")
        gr.Markdown("Browse and edit your video generation projects")
        
        with gr.Row():
            with gr.Column(scale=1):
                # Project selection
                project_dropdown = gr.Dropdown(
                    choices=browser.get_available_projects(),
                    label="Select Project",
                    interactive=True
                )
                
                load_btn = gr.Button("Load Project", variant="primary")
                load_status = gr.Textbox(label="Status", interactive=False)
                
                # Block navigation
                gr.Markdown("### Block Navigation")
                block_slider = gr.Slider(
                    minimum=0,
                    maximum=0,
                    step=1,
                    value=0,
                    label="Block Index",
                    interactive=True
                )
                
                block_info = gr.Textbox(
                    label="Block Info",
                    lines=3,
                    interactive=False
                )
            
            with gr.Column(scale=2):
                # Block content display
                gr.Markdown("### Block Content")
                
                # Quick summary for decision making
                summary_text = gr.Textbox(
                    label="Quick Summary",
                    lines=2,
                    interactive=False,
                    value="Select a project and block to view content"
                )
                
                # Integrated view with media and info together
                with gr.Row():
                    with gr.Column(scale=1):
                        # Text and editing section
                        gr.Markdown("#### Text & Editing")
                        text_input = gr.Textbox(
                            label="Text",
                            lines=3,
                            interactive=True
                        )
                        prompt_input = gr.Textbox(
                            label="Prompt",
                            lines=6,
                            interactive=True
                        )
                        context_input = gr.Textbox(
                            label="Context",
                            lines=3,
                            interactive=True
                        )
                        
                        # Decision info
                        gr.Markdown("#### Decision Info")
                        decision_method = gr.Textbox(
                            label="Decision Method",
                            interactive=False
                        )
                        decision_confidence = gr.Number(
                            label="Confidence",
                            interactive=False
                        )
                        block_status = gr.Textbox(
                            label="Status",
                            interactive=False
                        )
                    
                    with gr.Column(scale=1):
                        # Media section
                        gr.Markdown("#### Generated Media")
                        video_output = gr.Video(
                            label="Generated Video",
                            interactive=False,
                            height=300
                        )
                        audio_output = gr.Audio(
                            label="Generated Audio",
                            interactive=False
                        )
                        srt_output = gr.File(
                            label="Subtitle File",
                            interactive=False
                        )
                
                # Action buttons
                with gr.Row():
                    update_btn = gr.Button("Update Block", variant="primary")
                    delete_gen_btn = gr.Button("Delete Generation", variant="stop")
                    delete_audio_btn = gr.Button("Delete Audio Generation", variant="stop")
                    save_btn = gr.Button("Save Project", variant="secondary")
                
                action_status = gr.Textbox(
                    label="Action Status",
                    interactive=False
                )
        
        # Event handlers
        def load_project_handler(project_name):
            if not project_name:
                return gr.update(), "Please select a project", gr.update(maximum=0), "", "", "", "", "", "", "", "", "", "", "", ""
            
            success, message = browser.load_project(project_name)
            if success:
                max_blocks = len(browser.current_data.get('script', []))
                block_data = get_block_display_data(0)
                summary = f"Project: {project_name} | Blocks: {max_blocks} | Current: Block 0"
                return (
                    gr.update(value=message),
                    gr.update(maximum=max_blocks-1 if max_blocks > 0 else 0, value=0),
                    gr.update(value=summary),
                    *block_data
                )
            else:
                return gr.update(value=message), gr.update(maximum=0), gr.update(value="Error loading project"), "", "", "", "", "", "", "", "", "", "", "", ""
        
        def get_block_display_data(block_index):
            """Get all display data for a specific block"""
            if not browser.current_data or block_index >= len(browser.current_data.get('script', [])):
                return "", "", "", "", "", "", "", "", "", "", "", "", ""
            
            block_info_data = browser.get_block_info(block_index)
            
            # Create enhanced block info text with more details
            info_text = f"Block ID: {block_info_data.get('id', 'N/A')}\n"
            info_text += f"Status: {block_info_data.get('status', 'N/A')}\n"
            info_text += f"Decision Method: {block_info_data.get('decision_method', 'N/A')}\n"
            info_text += f"Confidence: {block_info_data.get('decision_confidence', 0):.2f}\n"
            info_text += f"Video Generated: {'✅' if block_info_data.get('generation_ok', False) else '❌'}\n"
            info_text += f"Audio Generated: {'✅' if block_info_data.get('audio_generation_ok', False) else '❌'}\n"
            
            # Add file status info
            video_status = "Available" if block_info_data.get('video_path') else "Not Found"
            audio_status = "Available" if block_info_data.get('audio_path') else "Not Found"
            srt_status = "Available" if block_info_data.get('srt_path') else "Not Found"
            
            info_text += f"Video File: {video_status}\n"
            info_text += f"Audio File: {audio_status}\n"
            info_text += f"Subtitle File: {srt_status}"
            
            # Create summary for quick decision making
            summary = f"Block {block_index + 1}: {block_info_data.get('id', 'N/A')} | "
            summary += f"Method: {block_info_data.get('decision_method', 'N/A')} | "
            summary += f"Video: {'✅' if block_info_data.get('generation_ok', False) else '❌'} | "
            summary += f"Audio: {'✅' if block_info_data.get('audio_generation_ok', False) else '❌'}"
            
            return (
                summary,
                info_text,
                block_info_data.get('text', ''),
                block_info_data.get('prompt', ''),
                block_info_data.get('context', ''),
                block_info_data.get('decision_method', ''),
                block_info_data.get('decision_confidence', 0),
                block_info_data.get('status', ''),
                block_info_data.get('video_path'),
                block_info_data.get('audio_path'),
                block_info_data.get('srt_path'),
                "",
                ""
            )
        
        def update_block_handler(block_index, text, prompt, context):
            success, message = browser.update_block(block_index, text, prompt, context)
            return message
        
        def delete_generation_handler(block_index):
            success, message = browser.delete_generation(block_index)
            return message
        
        def delete_audio_handler(block_index):
            success, message = browser.delete_audio_generation(block_index)
            return message
        
        def save_project_handler():
            success, message = browser.save_project()
            return message
        
        # Connect events
        load_btn.click(
            load_project_handler,
            inputs=[project_dropdown],
            outputs=[
                load_status, block_slider, summary_text, block_info, text_input, prompt_input,
                context_input, decision_method, decision_confidence, block_status,
                video_output, audio_output, srt_output, action_status
            ]
        )
        
        block_slider.change(
            get_block_display_data,
            inputs=[block_slider],
            outputs=[
                summary_text, block_info, text_input, prompt_input, context_input,
                decision_method, decision_confidence, block_status,
                video_output, audio_output, srt_output, action_status, action_status
            ]
        )
        
        update_btn.click(
            update_block_handler,
            inputs=[block_slider, text_input, prompt_input, context_input],
            outputs=[action_status]
        )
        
        delete_gen_btn.click(
            delete_generation_handler,
            inputs=[block_slider],
            outputs=[action_status]
        )
        
        delete_audio_btn.click(
            delete_audio_handler,
            inputs=[block_slider],
            outputs=[action_status]
        )
        
        save_btn.click(
            save_project_handler,
            outputs=[action_status]
        )
    
    return interface

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
