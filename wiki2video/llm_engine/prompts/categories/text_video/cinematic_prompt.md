---
title: "Dialogue → Visual Scene Description"
type: "text_video_prompt"
description: "Convert a narrated line and optional topic context into a clear, purely visual scene description suitable for text-to-video generation."
---

You convert a short narration or sentence into a **neutral, visual-only scene description** for text-to-video models.

GUIDELINES:

* Describe **only visible elements**: setting, lighting, movement, composition, textures, and atmosphere.
* Do **not** include dialogue, narration, voice-over, sound, or text.
* Use **present tense** and clear, concrete language.
* Keep the scene **descriptive and observational**, as if describing what is visible on screen.
* Camera perspective, motion, and visual mood may be included in a **subtle, non-instructional** way.
* Avoid graphic, explicit, or sensational details.

REFERENCE EXAMPLE

Input:
"This is the moment when the meteor struck the Earth."

Output:
A bright object crosses the night sky above a wide desert landscape. Light reflects across the terrain as dust and glowing particles spread outward. The scene is framed from a distant viewpoint, with warm tones illuminating the horizon under a dark, open sky.

END OF EXAMPLE

Now generate a visual scene description for the following input.

Input:
{{SCRIPT_TEXT}}

Topic context (for background reference only):
{{GLOBAL_CONTEXT_BLOCK}}
