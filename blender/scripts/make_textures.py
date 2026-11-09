"""blender -b --factory-startup -P make_textures.py  -> blender/textures/*.png + contact sheet"""
import os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, bpy
import lib_tex

lib_tex.generate_all()

# contact sheet of albedo textures (skip normal maps) for visual review
files = sorted(f for f in glob.glob(os.path.join(lib_tex.OUT, "*.png")) if not f.endswith("_n.png"))
cell, cols = 160, 8
rows = (len(files) + cols - 1) // cols
sheet = np.zeros((rows * cell, cols * cell, 4), np.float32); sheet[..., 3] = 1
for k, f in enumerate(files):
    img = bpy.data.images.load(f)
    w, h = img.size
    px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)
    ys = (np.arange(cell) * h / cell).astype(int); xs = (np.arange(cell) * w / cell).astype(int)
    r, c = divmod(k, cols)
    sheet[(rows - 1 - r) * cell:(rows - r) * cell, c * cell:(c + 1) * cell] = px[ys][:, xs]
    bpy.data.images.remove(img)
out = bpy.data.images.new("sheet", cols * cell, rows * cell, alpha=True)
out.pixels.foreach_set(sheet.ravel())
path = os.path.join(os.path.dirname(lib_tex.ROOT), "renders", "texture_sheet.png")
os.makedirs(os.path.dirname(path), exist_ok=True)
out.filepath_raw = path; out.file_format = "PNG"; out.save()
print("SHEET", path, [os.path.basename(f) for f in files])
