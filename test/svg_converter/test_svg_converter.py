from pathlib import Path
from wiki2video.llm_agent.agents.utils.svg_converter import ensure_non_svg
import os

def test_svg_conversion():
    assets_dir = Path("./assets")
    if not assets_dir.exists():
        print("❌ assets directory does not exist.")
        return

    svg_files = list(assets_dir.glob("*.svg"))

    if not svg_files:
        print("⚠️ No SVG files found in ./assets/")
        return

    print(f"🔍 Found {len(svg_files)} SVG files in ./assets/")
    print("============================================")

    success_count = 0
    fail_count = 0

    for svg_file in svg_files:
        print(f"\n➡️ Processing: {svg_file}")

        try:
            png_path = ensure_non_svg(svg_file)

            # 检查 PNG 是否存在
            if not png_path.exists():
                print(f"❌ PNG not created: {png_path}")
                fail_count += 1
                continue

            # 检查文件大小是否大于 0
            size = os.path.getsize(png_path)
            if size == 0:
                print(f"❌ PNG output is empty (0 bytes): {png_path}")
                fail_count += 1
                continue

            print(f"✅ PNG created: {png_path} ({size} bytes)")
            success_count += 1

        except Exception as e:
            print(f"❌ Conversion error: {e}")
            fail_count += 1

    print("\n============================================")
    print(f"🏁 Test complete: {success_count} success, {fail_count} failed.")
    print("============================================")


if __name__ == "__main__":
    test_svg_conversion()
