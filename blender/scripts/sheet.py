"""blender -b -P sheet.py -- out.png cell_w cols img1 img2 ...   (contact sheet, labels omitted)"""
import sys, numpy as np, bpy
a = sys.argv[sys.argv.index("--") + 1:]
out, cw, cols, files = a[0], int(a[1]), int(a[2]), a[3:]
ch = cw * 3 // 4
rows = (len(files) + cols - 1) // cols
sheet = np.zeros((rows * ch, cols * cw, 4), np.float32); sheet[..., 3] = 1
for k, f in enumerate(files):
    img = bpy.data.images.load(f); w, h = img.size
    px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)
    ys = (np.arange(ch) * h / ch).astype(int); xs = (np.arange(cw) * w / cw).astype(int)
    r, c = divmod(k, cols)
    sheet[(rows - 1 - r) * ch:(rows - r) * ch, c * cw:(c + 1) * cw] = px[ys][:, xs]
o = bpy.data.images.new("s", cols * cw, rows * ch, alpha=True); o.pixels.foreach_set(sheet.ravel())
o.filepath_raw = out; o.file_format = "PNG"; o.save()
