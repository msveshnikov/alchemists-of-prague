"""Character textures (Task 2). Same painted style and helpers as lib_tex.

blender -b --factory-startup -P make_char_textures.py
"""
import numpy as np

from lib_tex import (_seg_dist, tex_metal, colorize, crown_mask, fbm, lerp, lion_mask, save, save_pair, smoothstep,
                     value_noise, voronoi)


def tex_chainmail(name, base, size=512, seed=301, rust=0.0):
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    n = 32

    def rings(row_shift):
        v = ys * n
        row = np.floor(v) + row_shift
        u = xs * n + 0.5 * (row % 2)
        lu = u - np.floor(u) - 0.5
        lv = v - np.floor(v) - 0.5 - row_shift
        d = np.sqrt(lu ** 2 + (lv * 1.15) ** 2)
        return 1 - smoothstep(0.06, 0.12, np.abs(d - 0.36))

    m = np.maximum(rings(0), rings(-1) * 0.8)
    metal = colorize(fbm(size, 8, 4, seed), base) * (0.75 + 0.45 * m[..., None])
    alb = lerp(np.array([0.05, 0.05, 0.05]), metal, m[..., None])
    if rust:
        r = smoothstep(0.5, 0.8, fbm(size, 6, 5, seed + 1)) * rust
        rc = colorize(fbm(size, 20, 3, seed + 2), ["#4a2412", "#7a3e1c"]) * (0.4 + 0.6 * m[..., None])
        alb = lerp(alb, rc, r[..., None])
    save_pair(name, alb, m, 4.0)


def tex_leather(name, stops, size=512, seed=311):
    f = fbm(size, 6, 6, seed)
    crease = value_noise(size, 30, seed + 1, 8)
    t = np.clip(f * 0.8 + 0.2 * crease, 0, 1)
    alb = colorize(t, stops)
    worn = smoothstep(0.6, 0.85, fbm(size, 10, 4, seed + 2))
    alb = lerp(alb, alb * 1.35, worn[..., None] * 0.6)
    save_pair(name, alb, t, 2.0)


def tex_skin(name, stops, size=256, seed=321):
    f = fbm(size, 4, 5, seed)
    alb = colorize(f, stops)
    red = smoothstep(0.55, 0.8, fbm(size, 3, 3, seed + 1))
    alb = lerp(alb, alb * np.array([1.08, 0.9, 0.88]), red[..., None] * 0.6)
    alb *= (0.94 + 0.08 * fbm(size, 64, 2, seed + 2))[..., None]
    save(name, alb)


def tex_hair(name, stops, size=256, seed=331):
    s = value_noise(size, 96, seed, 2) * 0.6 + value_noise(size, 40, seed + 1, 3) * 0.4
    save_pair(name, colorize(s, stops), s, 3.0)


def tex_fur(name, stops, size=256, seed=341):
    s = fbm(size, 48, 3, seed, 0.6, cells_y=16)
    save_pair(name, colorize(s, stops), s, 4.0)


def tex_clay(size=1024, seed=351):
    f1, f2, idv = voronoi(size, 9, seed, 0.9)
    crack = 1 - smoothstep(0.0, 0.035, f2 - f1)
    slab = np.clip(1 - f1 / 0.8, 0, 1)
    base = colorize(np.clip(idv * 0.5 + fbm(size, 6, 5, seed + 1) * 0.6 - 0.05, 0, 1),
                    ["#4e3a28", "#6a5038", "#7f6246", "#8f7254", "#9a7c5c"])
    base *= (0.75 + 0.35 * slab)[..., None]
    pits = smoothstep(0.7, 0.8, fbm(size, 40, 3, seed + 2))
    alb = lerp(base, base * 0.6, pits[..., None])
    alb = lerp(alb, np.array([0.12, 0.08, 0.05]), crack[..., None] * 0.9)
    h = slab * 0.6 - crack + fbm(size, 24, 4, seed + 3) * 0.3
    save_pair("clay_golem", alb, h, 6.0)


def tex_bone(size=512, seed=361):
    f = fbm(size, 4, 5, seed, 0.5, cells_y=12)
    alb = colorize(f, ["#8a7650", "#ab9468", "#c4ad80", "#d2bc90"])
    cr = smoothstep(0.62, 0.75, value_noise(size, 60, seed + 1, 4))
    alb = lerp(alb, np.array([0.3, 0.24, 0.15]), cr[..., None] * 0.5)
    dirt = smoothstep(0.55, 0.85, fbm(size, 5, 4, seed + 2))
    alb = lerp(alb, alb * 0.55, dirt[..., None])
    save_pair("bone", alb, f, 3.0)


def tex_robe(name, stops, size=512, seed=371, burns=0.4, blood=0.0):
    folds = fbm(size, 3, 5, seed, 0.5, cells_y=1)
    alb = colorize(np.clip(0.5 + (folds - 0.5) * 1.3, 0, 1), stops)
    gy, gx = np.mgrid[0:size, 0:size]
    w = 0.5 + 0.25 * np.sin(gx * 1.4) + 0.25 * np.sin(gy * 1.4)
    alb *= (0.92 + 0.1 * w)[..., None]
    if burns:
        bf = fbm(size, 7, 5, seed + 1)
        b = smoothstep(0.66, 0.8, bf) * burns
        rim = smoothstep(0.62, 0.66, bf) * (1 - smoothstep(0.66, 0.7, bf))
        alb = lerp(alb, np.array([0.35, 0.18, 0.08]), rim[..., None] * burns)
        alb = lerp(alb, np.array([0.05, 0.035, 0.025]), b[..., None])
    if blood:
        bl = smoothstep(0.6, 0.72, fbm(size, 9, 5, seed + 2)) * blood
        alb = lerp(alb, np.array([0.38, 0.08, 0.05]), bl[..., None])
    save_pair(name, alb, folds * 0.6, 2.0)


def tex_horse(size=512, seed=381):
    f = fbm(size, 5, 6, seed)
    alb = colorize(f, ["#3e1e0e", "#5a2e16", "#70391c", "#844626"])
    dapple = smoothstep(0.55, 0.75, fbm(size, 14, 3, seed + 1))
    alb = lerp(alb, alb * 1.18, dapple[..., None] * 0.5)
    hair = value_noise(size, 120, seed + 2, 12)
    alb *= (0.9 + 0.15 * hair)[..., None]
    save_pair("horse_coat", alb, hair * 0.3, 1.5)


def tex_golem_letters(size=512, seed=391):
    """Forehead decal: clay with the glowing word emet (Hebrew, right-to-left: alef, mem, tav)."""
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    clay = colorize(fbm(size, 6, 5, seed), ["#5e4630", "#7a5c40", "#8f7052"])
    m = np.zeros((size, size), bool)

    def seg(a, b, w=0.035):
        return _seg_dist(xs, ys, a, b) < w

    def cell(i):
        return 0.06 + i * 0.31, 0.25, 0.27, 0.5

    x0, y0, w, h = cell(0)  # tav (leftmost)
    m |= seg((x0 + .1 * w, y0 + .1 * h), (x0 + .92 * w, y0 + .1 * h))
    m |= seg((x0 + .85 * w, y0 + .1 * h), (x0 + .85 * w, y0 + .95 * h))
    m |= seg((x0 + .28 * w, y0 + .1 * h), (x0 + .28 * w, y0 + .85 * h))
    m |= seg((x0 + .28 * w, y0 + .85 * h), (x0 + .1 * w, y0 + .95 * h))
    x0, y0, w, h = cell(1)  # mem
    m |= seg((x0 + .08 * w, y0 + .02 * h), (x0 + .22 * w, y0 + .14 * h))
    m |= seg((x0 + .22 * w, y0 + .12 * h), (x0 + .86 * w, y0 + .12 * h))
    m |= seg((x0 + .86 * w, y0 + .12 * h), (x0 + .86 * w, y0 + .95 * h))
    m |= seg((x0 + .86 * w, y0 + .95 * h), (x0 + .4 * w, y0 + .95 * h))
    m |= seg((x0 + .3 * w, y0 + .2 * h), (x0 + .14 * w, y0 + .95 * h))
    x0, y0, w, h = cell(2)  # alef (rightmost)
    m |= seg((x0 + .1 * w, y0 + .05 * h), (x0 + .9 * w, y0 + .95 * h))
    m |= seg((x0 + .85 * w, y0 + .05 * h), (x0 + .72 * w, y0 + .45 * h))
    m |= seg((x0 + .3 * w, y0 + .55 * h), (x0 + .14 * w, y0 + .95 * h))
    mf = m.astype(np.float32)
    halo = mf.copy()
    for _ in range(8):
        halo = (halo + np.roll(halo, 3, 0) + np.roll(halo, -3, 0) + np.roll(halo, 3, 1) + np.roll(halo, -3, 1)) / 5
    halo = np.clip(halo * 2.5, 0, 1)
    gold = np.array([1.0, 0.62, 0.18])
    k = np.maximum(mf, halo * 0.5)[..., None]
    save("golem_letters", lerp(clay * 0.6, gold, k))
    save("golem_letters_emit", gold[None, None, :] * np.maximum(mf, halo * 0.6)[..., None])


def tex_tabard(size=512, seed=401):
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    red = colorize(fbm(size, 4, 5, seed), ["#4e1410", "#6c1c16", "#84281e"])
    lx, ly = (xs - 0.12) / 0.76, (ys - 0.1) / 0.8
    white = colorize(fbm(size, 8, 3, seed + 1), ["#c9bda0", "#e2d8c0"])
    gold = colorize(fbm(size, 8, 3, seed + 3), ["#9a7428", "#d2a84a"])
    alb = np.where(lion_mask(lx, ly)[..., None], white, red)
    alb = np.where(crown_mask(lx, ly)[..., None], gold, alb)
    stains = smoothstep(0.62, 0.8, fbm(size, 6, 5, seed + 2))
    save("tabard_lion", lerp(alb, alb * 0.65, stains[..., None]))


def generate_characters():
    print("Generating character textures")
    tex_chainmail("chainmail", ["#3a3c3e", "#5a5c5e", "#7a7c7e"], seed=301)
    tex_chainmail("chainmail_rust", ["#4a3a2e", "#5e4a38", "#6e5a46"], seed=302, rust=0.8)
    tex_leather("leather", ["#2e1c10", "#45291a", "#5a3822", "#6e4a2e"])
    tex_leather("leather_dark", ["#1c120c", "#2a1c12", "#3a281a"], seed=312)
    tex_skin("skin", ["#9a6a4e", "#b47e5e", "#c69070", "#d0a07e"])
    tex_skin("skin_pale", ["#8e7466", "#a68a7a", "#b89c8a", "#c4ab98"], seed=322)
    tex_skin("skin_child", ["#b07e62", "#c8967a", "#d6a88a"], seed=323)
    tex_hair("hair_dark", ["#120c08", "#22160e", "#352418", "#4a3424"])
    tex_hair("hair_brown", ["#2a1a0e", "#4a3018", "#6a4826", "#7e5a32"], seed=332)
    tex_hair("hair_grey", ["#3e3a36", "#5e5852", "#7e7870", "#9a948a"], seed=333)
    tex_hair("horse_hair", ["#0c0806", "#18100a", "#261a10", "#30200e"], seed=334)
    tex_fur("fur", ["#2e2014", "#4a3420", "#6a4e30", "#8a6a44", "#a88a62"])
    tex_clay()
    tex_bone()
    tex_robe("robe_dark", ["#16110e", "#221a14", "#30241a", "#3e2e22"], seed=371, burns=0.6)
    tex_robe("robe_brown", ["#2e2216", "#45321f", "#5a4228", "#6a5032"], seed=372, burns=0.3)
    tex_robe("rags", ["#3a3024", "#524430", "#6a5a42", "#7a6a50"], seed=373, burns=0.8)
    tex_robe("linen", ["#9e8e70", "#b8a684", "#cbb996", "#d8c8a6"], seed=374, burns=0.0)
    tex_robe("apron_bloody", ["#a89878", "#c0ae8c", "#d0c09e"], seed=375, burns=0.0, blood=0.8)
    tex_robe("wool_blue", ["#2a3440", "#3a4654", "#4a5868"], seed=376, burns=0.1)
    tex_robe("wool_brown", ["#3a2a1c", "#4e3824", "#62482e"], seed=377, burns=0.1)
    tex_robe("mantle_red", ["#3e120e", "#561a14", "#6c241a", "#7e2e20"], seed=378, burns=0.35)
    tex_robe("merchant_coat", ["#4a1410", "#661c16", "#7e2a1c", "#94402a"], seed=379, burns=0.0)
    tex_metal("iron_rust", ["#4a3a30", "#5e4a3a", "#6e5844"], ["#5a2e16", "#8a4a22", "#a8642e"], seed=411, rust_amt=0.95)
    tex_horse()
    tex_golem_letters()
    tex_tabard()
    print("Character textures done")
