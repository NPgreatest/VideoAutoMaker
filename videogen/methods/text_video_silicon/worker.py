# from __future__ import annotations
# import json, time, threading
# from pathlib import Path
# from typing import Dict
#
# from videogen.methods.text_video_silicon.constants import (
#     POLL_INTERVAL_SEC, MAX_POLLS_PER_TASK,
#     STATUS_SUCCEED, STATUS_ERROR, NON_TERMINAL, TERMINAL, ERRORS,
# )
# from videogen.methods.text_video_silicon.sf_api import check_status, download_to
# from videogen.dao import TaskMySQL
# from videogen.methods.text_video_silicon.utils import resize_video_duration
#
# _worker_started: Dict[str, bool] = {}
# _worker_guard = threading.Lock()
#
#
#
#
# # =====================================================
# # 🔧 Repair utility: detect raw-only videos and resize
# # =====================================================
#
# def check_and_resize_missing_final_videos(store: TaskMySQL) -> None:
#     """
#     Detects videos that only have *_raw.mp4 but no final .mp4,
#     and resizes them to the proper duration using resize_video_duration().
#     Never deletes the raw file.
#     """
#     print("\n[Repair] Checking for missing final videos...")
#     rows = store.get_all()
#     fixed_count = 0
#
#     for row in rows:
#         project = row.get("project")
#         target_name = row.get("target_name")
#
#         workdir = Path(row["workdir"])
#         project_dir = workdir / "project" / project
#         video_dir = project_dir / "video"
#         raw_mp4 = video_dir / f"{target_name}_raw.mp4"
#         final_mp4 = video_dir / f"{target_name}.mp4"
#
#         if raw_mp4.exists() and not final_mp4.exists():
#             target_dur = float(row.get("duration") or 5.0)
#             print(f"[Repair] Found raw-only video: {raw_mp4.name} → resizing to {target_dur:.2f}s")
#
#             new_dur = resize_video_duration(raw_mp4, final_mp4, target_dur)
#             if new_dur > 0:
#                 # row["duration"] = f"{new_dur:.3f}"
#                 row["output_path"] = str(final_mp4)
#                 row["status"] = STATUS_SUCCEED
#                 store.upsert(row)
#
#                 meta = {
#                     "request_id": row.get("request_id"),
#                     "model": row.get("model"),
#                     "prompt": row.get("prompt"),
#                     "source_url": row.get("source_url"),
#                     "duration": row.get("duration"),
#                     "fixed_by": "repair_script",
#                     "fixed_at": time.time(),
#                 }
#                 meta_path = final_mp4.with_suffix(".meta.json")
#                 with open(meta_path, "w", encoding="utf-8") as f:
#                     json.dump(meta, f, ensure_ascii=False, indent=2)
#                 print(f"[Repair] ✅ Repaired and saved {final_mp4.name}")
#                 fixed_count += 1
#             else:
#                 print(f"[Repair] ⚠️ Failed to resize {raw_mp4.name}, skipping.")
#
#     if fixed_count == 0:
#         print("[Repair] No missing videos detected.")
#     else:
#         print(f"[Repair] ✅ Completed. Fixed {fixed_count} videos.\n")
#
#
# # =====================================================
# # 🔁 Main worker loop
# # =====================================================
#
# def _loop(store: TaskMySQL) -> None:
#     print(f"[Worker] Polling loop started for {store.db_path}")
#     idle_rounds = 0
#
#     while True:
#         rows = store.get_all()
#         now = time.time()
#
#         if not rows:
#             print("[Worker] No tasks in CSV. Sleeping...")
#             time.sleep(POLL_INTERVAL_SEC)
#             continue
#
#         total = len(rows)
#         done = sum(1 for r in rows if r.get("status") in TERMINAL)
#         print(f"[Worker] Checking {total} tasks ({done} done, {total - done} active)...")
#
#         if done == total:
#             idle_rounds += 1
#             print(f"[Worker] All tasks complete ({idle_rounds}/3)...")
#             if idle_rounds >= 3:
#                 print("[Worker] ✅ All tasks finished. Checking for repairs before exit...")
#                 check_and_resize_missing_final_videos(store)
#                 break
#             time.sleep(POLL_INTERVAL_SEC)
#             continue
#         else:
#             idle_rounds = 0
#
#         for row in rows:
#             status = row.get("status", "")
#             rid = row.get("request_id", "?")
#             poll_cnt = int(row.get("poll_count") or "0")
#
#             if status in TERMINAL:
#                 continue
#
#             print(f"  → [Task {rid}] status={status} poll={poll_cnt}")
#
#             if poll_cnt >= MAX_POLLS_PER_TASK:
#                 print(f"  [!] Task {rid} timed out")
#                 row.update({
#                     "status": STATUS_ERROR,
#                     "error": "Timeout",
#                     "updated_ts": str(now),
#                     "poll_count": str(poll_cnt),
#                 })
#                 store.upsert(row)
#                 continue
#
#             try:
#                 resp = check_status(rid)
#             except Exception as e:
#                 print(f"  [x] check_status failed: {e}")
#                 continue
#
#             new_status = resp.get("status") or STATUS_ERROR
#
#             # === 成功 ===
#             if new_status == STATUS_SUCCEED:
#                 videos = (resp.get("results") or {}).get("videos") or []
#                 url = videos[0].get("url") if videos else None
#                 if not url:
#                     row.update({
#                         "status": STATUS_ERROR,
#                         "error": "Succeed but no video url",
#                         "updated_ts": str(now),
#                         "poll_count": str(poll_cnt + 1),
#                     })
#                     store.upsert(row)
#                     continue
#
#                 print(f"  [✓] Task {rid} succeeded, downloading video from {url}")
#                 workdir = Path(row["workdir"])
#                 project_dir = workdir / "project" / row["project"]
#                 video_dir = project_dir / "video"
#                 video_dir.mkdir(parents=True, exist_ok=True)
#                 final_mp4 = video_dir / f"{row['target_name']}.mp4"
#                 raw_mp4 = video_dir / f"{row['target_name']}_raw.mp4"
#
#                 try:
#                     # Download raw (always keep this)
#                     download_to(url, raw_mp4)
#                     print(f"      → Saved raw file: {raw_mp4}")
#
#                     # Resize to target duration, but keep raw
#                     target_dur = float(row.get("duration") or 5.0)
#                     new_dur = resize_video_duration(raw_mp4, final_mp4, target_dur)
#
#                     if new_dur > 0:
#                         # row["duration"] = f"{new_dur:.3f}"
#                         print(f"      → Resized to {new_dur:.2f}s → {final_mp4.name}")
#                     else:
#                         print(f"      ⚠️ Resize failed, keeping raw as source only (no deletion).")
#
#                     row.update({
#                         "status": STATUS_SUCCEED,
#                         "source_url": url,
#                         "output_path": str(final_mp4 if final_mp4.exists() else raw_mp4),
#                         "updated_ts": str(now),
#                         "error": "",
#                         "poll_count": str(poll_cnt + 1),
#                     })
#                     store.upsert(row)
#
#                     meta = {
#                         "request_id": rid,
#                         "model": row.get("model"),
#                         "prompt": row.get("prompt"),
#                         "source_url": url,
#                         "created": float(row.get("created_ts") or now),
#                         "finished": now,
#                         "duration": row.get("duration"),
#                     }
#                     meta_path = final_mp4.with_suffix(".meta.json")
#                     with open(meta_path, "w", encoding="utf-8") as f:
#                         json.dump(meta, f, ensure_ascii=False, indent=2)
#                     print(f"      → Meta saved: {meta_path}")
#
#                 except Exception as e:
#                     print(f"  [x] Download or resize error for {rid}: {e}")
#                     row.update({
#                         "status": STATUS_ERROR,
#                         "error": f"Download/Resize error: {e}",
#                         "updated_ts": str(now),
#                         "poll_count": str(poll_cnt + 1),
#                     })
#                     store.upsert(row)
#
#             elif new_status in NON_TERMINAL:
#                 row.update({
#                     "status": new_status,
#                     "updated_ts": str(now),
#                     "poll_count": str(poll_cnt + 1),
#                 })
#                 store.upsert(row)
#
#             else:
#                 row.update({
#                     "status": new_status,
#                     "error": resp.get("error", ""),
#                     "updated_ts": str(now),
#                     "poll_count": str(poll_cnt + 1),
#                 })
#                 store.upsert(row)
#
#         print(f"[Worker] Sleep {POLL_INTERVAL_SEC}s...\n")
#         time.sleep(POLL_INTERVAL_SEC)
#
#
# # =====================================================
# # 🚀 Worker startup function
# # =====================================================
#
# def start_worker_loop(store: TaskMySQL) -> None:
#     """Start the worker loop for the given store."""
#     print(f"[Worker] Starting worker loop for {store.db_path}")
#     try:
#         _loop(store)
#     except KeyboardInterrupt:
#         print("\n[Worker] Stopped manually.")
#
#
# # =====================================================
# # 🧠 Manual entry
# # =====================================================
#
# def main() -> None:
#     # Initialize MySQL store instead of CSV
#     store = TaskMySQL()
#
#     import sys
#     if len(sys.argv) > 1 and sys.argv[1] == "--repair":
#         check_and_resize_missing_final_videos(store)
#     else:
#         print(f"[Worker] Starting polling loop for MySQL database")
#         try:
#             _loop(store)
#         except KeyboardInterrupt:
#             print("\n[Worker] Stopped manually.")
#
#
#
#
# if __name__ == "__main__":
#     main()
