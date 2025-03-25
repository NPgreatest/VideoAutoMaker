import os

def get_next_filename(folder, prefix, ext):
    i = 1
    while True:
        filename = f"{prefix}_{i:03}.{ext}"
        if not os.path.exists(os.path.join(folder, filename)):
            return filename
        i += 1