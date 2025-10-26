#!/usr/bin/env python3
import json
import os

def main():
    project = input("请输入项目名 (例如 mh370_demo): ").strip()
    
    # 询问全局角色设置
    global_character = input("请输入全局角色名 (例如 narrator, host, guest，留空则跳过): ").strip()
    
    # 询问视频尺寸设置
    print("\n请选择视频格式:")
    print("1. landscape (1280x720) - 横屏格式")
    print("2. tiktok (720x1280) - 竖屏格式")
    size_choice = input("请输入选择 (1 或 2，默认为 1): ").strip()
    
    if size_choice == "2":
        size = "tiktok"
        print("✅ 已选择 TikTok 格式 (720x1280)")
    else:
        size = "landscape"
        print("✅ 已选择横屏格式 (1280x720)")
    
    script = []
    line_num = 1

    print("\n开始输入剧本文本，每行一条。输入 --end 结束。")
    if global_character:
        print(f"默认角色: {global_character}")
        print("如需为某行指定不同角色，请在文本前加上 '角色名: ' (例如: 'narrator: 这是旁白')")
    print()

    while True:
        line = input(f"L{line_num}> ").strip()
        if line == "--end":
            break
        if not line:
            continue
        
        # 处理角色分配
        character = global_character  # 默认使用全局角色
        text = line
        
        # 检查是否有角色前缀 (格式: "角色名: 文本")
        if ":" in line and not line.startswith("http"):
            parts = line.split(":", 1)
            if len(parts) == 2 and parts[0].strip():
                character = parts[0].strip()
                text = parts[1].strip()
        
        script.append({
            "id": f"L{line_num}",
            "text": text,
            "voice": text,
            "character": character if character else None
        })
        line_num += 1

    data = {
        "project": project,
        "size": size,
        "script": script
    }

    # 构造保存路径
    save_dir = os.path.join("project", project)
    os.makedirs(save_dir, exist_ok=True)
    out_path = os.path.join(save_dir, f"{project}.json")

    # 保存 JSON 文件
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已生成 JSON 文件: {out_path}")
    print(json.dumps(data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
