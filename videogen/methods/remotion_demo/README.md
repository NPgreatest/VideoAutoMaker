# Text-to-Video Generator with Remotion

A powerful demo project that converts user text prompts into engaging videos using AI-generated content and Remotion for video rendering.

## Features

- 🤖 **AI-Powered Content Generation**: Uses OpenAI's GPT models to generate compelling titles and descriptions from text prompts
- 🎬 **Professional Video Rendering**: Creates beautiful animated videos with Remotion
- 🎵 **Text-to-Speech**: Generates audio narration for the videos
- ✨ **Smooth Animations**: Features fade-ins, slide-ins, and spring animations
- 🎨 **Modern Design**: Beautiful gradient backgrounds and professional styling
- 🔧 **Easy to Use**: Simple command-line interface with example prompts
- 📱 **Image-Focused Template**: Displays a styled image placeholder (3/4 screen) with descriptive text (1/4 screen)

## Prerequisites

- Python 3.7+
- Node.js 16+
- npm

## Installation

1. **Clone or download the project**
   ```bash
   cd remotion_demo
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Remotion dependencies**
   ```bash
   cd remotion_project
   npm install
   cd ..
   ```

4. **Set up OpenAI API key (optional)**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```
   *Note: Without an API key, the system will use fallback content instead of AI generation.*

## Usage

### Quick Start

Run the demo script with predefined examples:

```bash
python demo.py
```

### Manual Usage

Generate a video from custom text:

```bash
python generate_video.py
```

Then enter your text prompt when prompted.

### Example Prompts

- "Tell me about artificial intelligence and machine learning"
- "Explain quantum computing technology"
- "Describe renewable energy innovations"
- "Show me information about space exploration"
- "Create content about blockchain technology"

## Project Structure

```
remotion_demo/
├── generate_video.py          # Main video generation script
├── demo.py                    # Demo runner with examples
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── output/                    # Generated videos and audio
│   ├── props.json            # Generated content data
│   ├── output.mp4            # Rendered video
│   └── narration.wav         # Generated audio
└── remotion_project/          # Remotion React project
    ├── package.json
    ├── src/
    │   ├── index.ts          # Entry point
    │   ├── Root.tsx          # Composition definition
    │   └── PictureTextSlide.tsx # Main video component
    └── tsconfig.json
```

## How It Works

1. **Text Processing**: Your input text is sent to an AI model (OpenAI GPT) to generate relevant content
2. **Content Generation**: The AI creates:
   - A compelling title
   - A detailed description of the topic
   - Duration recommendation
3. **Video Rendering**: Remotion renders the content with smooth animations:
   - Image placeholder with gradient background and "AI" branding (3/4 screen)
   - Text content with fade-in and slide animations (1/4 screen)
   - Professional styling with shadows and effects
4. **Audio Generation**: Text-to-speech creates narration from the content
5. **Output**: Both video (.mp4) and audio (.wav) files are generated

## Customization

### Modifying Animations

Edit `remotion_project/src/PictureTextSlide.tsx` to customize:
- Animation timing
- Colors and gradients
- Font sizes and styles
- Image placeholder styling
- Layout proportions

### Changing AI Prompts

Modify the `system_prompt` in `generate_video.py` to change how the AI generates content.

### Audio Settings

Adjust voice properties in the `generate_audio_file` function:
- Speech rate
- Volume
- Voice selection

## Troubleshooting

### Common Issues

1. **"Node.js not found"**
   - Install Node.js from https://nodejs.org/

2. **"Remotion dependencies not installed"**
   - Run: `cd remotion_project && npm install`

3. **"OPENAI_API_KEY not set"**
   - Set your API key: `export OPENAI_API_KEY="your-key"`
   - Or use fallback mode (no AI generation)

4. **"Text-to-speech failed"**
   - Install system TTS dependencies
   - On macOS: Usually works out of the box
   - On Linux: `sudo apt-get install espeak`
   - On Windows: Install pywin32

### Rendering Issues

- Ensure you have sufficient disk space
- Check that the output directory is writable
- Verify Remotion is properly installed

## Technical Details

- **Video Format**: MP4 (H.264)
- **Resolution**: 1920x1080 (Full HD)
- **Frame Rate**: 30 FPS
- **Duration**: 3-8 seconds (configurable)
- **Audio Format**: WAV

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is for demonstration purposes. Please respect OpenAI's terms of service when using their API.
