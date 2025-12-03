---
title: "Test prompt template"
type: "test_prompt"
description: "This is a test prompt"
---
# LLM Engine Diagnostic Test

Your task is to demonstrate that the LLM Engine is functioning correctly.

## Instructions
Using the provided input variables, produce a structured system report.

## Required Output Format (JSON)
Return **strict JSON** with **NO extra commentary**:

```json
{
    "topic": "{{ topic }}",
    "summary": "A 2-3 sentence explanation about the topic.",
    "bullet_points": [
        "3 key facts about the topic, written as short bullet points."
    ],
    "confidence": "A number between 0 and 1 describing confidence."
}
```