#!/usr/bin/env python3
from wiki2video.router.decider import decide_generation_method

def main():
    topic = "MH370 失踪事件解析"
    samples = [
        "机型是波音 777-200ER，机上共有 239 人：227 名乘客、12 名机组人员，其中超过一半是华人。",
        "马来西亚军方雷达后来披露：MH370 在失联后疑似折返，跨过马来半岛，向西飞去。轨迹曲折，像是在规避雷达。",
        "“晚安，马航三七零（MH370）。” 对，这句平静到不能再平静的告别，是飞机在雷达上消失前，机长留给世界的最后话语。",
    ]

    print("🎬 Testing decision module for 3 sample lines\n")

    for i, line in enumerate(samples, 1):
        method = decide_generation_method(text=line, topic=topic)
        print(f"[{i}] {line}")
        print(f" → LLM decided: {method}\n")

if __name__ == "__main__":
    main()
