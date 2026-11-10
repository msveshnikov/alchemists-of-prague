"""Textures for run 2 (Charles Bridge, Mala Strana, Vysehrad) + the redrawn heraldic lion.

Same painted style and helpers as lib_tex. Called by make_textures_locations.py:
    blender -b --factory-startup -P make_textures_locations.py
"""
import math

import numpy as np

import lib_heraldry as HR
from lib_tex import (colorize, fbm, grime, hexc, lerp, save, save_pair, smoothstep, tex_ashlar, value_noise, voronoi)


# ----------------------------------------------------------------------------- heraldry (replaces the old primitive lion)
def _lion_paint(base, xs, ys, size, seed, white_stops=("#cdc2a6", "#e6dcc6"), outline="#2a120c"):
    L = HR.lion_layers(xs, ys, size)
    white = colorize(fbm(size, 8, 3, seed + 11)[:base.shape[0], :base.shape[1]], list(white_stops))
    gold = colorize(fbm(size, 8, 3, seed + 12)[:base.shape[0], :base.shape[1]], ["#9a7428", "#d6ac4c", "#e8c468"])
    alb = np.where(L["body"][..., None], white, base)
    alb = np.where(L["hatch"][..., None], white * 0.7, alb)
    alb = np.where(L["gold"][..., None], gold, alb)
    alb = np.where(L["outline"][..., None], hexc(outline), alb)
    return alb


def tex_shield(size=1024, seed=171):
    """Round shield face (fit to the disc): planks under worn red paint, crowned white lion, rim shadow."""
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    wood = colorize(fbm(size, 6, 5, seed + 1, cells_y=24), ["#3a2618", "#5a3c26", "#6e4c30"])
    plank = np.abs(((xs * 6) % 1) - 0.5) > 0.485
    red = colorize(fbm(size, 4, 5, seed), ["#561410", "#741c16", "#8c2a20"])
    red *= (0.88 + 0.12 * value_noise(size, 6, seed + 3, 40))[..., None]
    worn = smoothstep(0.66, 0.78, fbm(size, 10, 5, seed + 4))
    alb = lerp(red, wood, worn[..., None])
    alb = np.where(plank[..., None], wood * 0.45, alb)
    alb = _lion_paint(alb, (xs - 0.13) / 0.74, (ys - 0.11) / 0.78, size, seed)
    r = np.sqrt((xs - 0.5) ** 2 + (ys - 0.5) ** 2)
    alb *= (1 - 0.45 * smoothstep(0.42, 0.5, r))[..., None]
    alb *= grime(size, seed + 2, 0.3)[..., None]
    scratches = value_noise(size, 300, seed + 5, 6) > 0.93
    alb = np.where(scratches[..., None], alb * 1.25, alb)
    save("shield_lion", alb)


def tex_tabard(size=1024, seed=401):
    """Surcoat chest decal: deep red wool with the white lion, mud and wear."""
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    red = colorize(fbm(size, 4, 5, seed), ["#4a1410", "#661c16", "#7e281e"])
    weave = 0.94 + 0.06 * np.sin(np.arange(size)[None, :] * 1.7) * np.sin(np.arange(size)[:, None] * 1.7)
    red *= weave[..., None]
    alb = _lion_paint(red, (xs - 0.08) / 0.84, (ys - 0.06) / 0.88, size, seed, white_stops=("#c4b89a", "#ddd2ba"))
    stains = smoothstep(0.62, 0.8, fbm(size, 6, 5, seed + 2))
    save("tabard_lion", lerp(alb, alb * 0.65, stains[..., None]))


def tex_banner(size=1024, seed=161):
    h, w = size, size // 2
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    ys /= h
    xs /= w
    folds = 0.5 + 0.5 * np.sin(xs * math.pi * 5 + fbm(h, 3, 3, seed)[:, :w] * 2)
    red = colorize(fbm(h, 4, 5, seed + 1)[:, :w], ["#5c1612", "#7a1f19", "#8f2a20"])
    red *= (0.8 + 0.25 * folds)[..., None]
    lx = (xs - 0.04) / 0.92
    ly = (ys - 0.2) / 0.46
    alb = _lion_paint(red, lx, ly, h, seed)
    alb = lerp(alb, alb * (0.85 + 0.25 * folds[..., None]), 0.6)
    gold = colorize(fbm(h, 8, 3, seed + 3)[:, :w], ["#9a7428", "#d2a84a"])
    border = (ys < 0.03) | (np.abs(xs - 0.5) > 0.46)
    alb = np.where(border[..., None], gold * 0.8, alb)
    alb *= grime(h, seed + 4, 0.15)[:, :w][..., None]
    save("banner_lion", alb)


# ----------------------------------------------------------------------------- ground & rock
def tex_rock(size=1024, seed=501):
    """Cliff rock of the Vysehrad crag: layered grey-brown slate with cracks, lichen and moss."""
    f1, f2, idv = voronoi(size, 7, seed, 0.9, stretch=(1.0, 2.2))
    crack = 1 - smoothstep(0.0, 0.05, f2 - f1)
    strata = 0.5 + 0.5 * np.sin(np.arange(size)[:, None] / size * 2 * math.pi * 9 + fbm(size, 3, 4, seed + 1) * 6)
    face = fbm(size, 10, 6, seed + 2)
    t = np.clip(idv * 0.45 + face * 0.55 + 0.15 * (strata - 0.5), 0, 1)
    alb = colorize(t, ["#3e3a34", "#56504a", "#6c645a", "#80766a", "#93887a"])
    alb *= (0.8 + 0.25 * strata)[..., None]
    alb = lerp(alb, np.array([0.08, 0.07, 0.06]), crack[..., None] * 0.85)
    moss = smoothstep(0.62, 0.78, fbm(size, 5, 5, seed + 3)) * smoothstep(0.3, 0.7, strata)
    alb = lerp(alb, colorize(fbm(size, 30, 3, seed + 4), ["#3a4424", "#55602e"]), moss[..., None] * 0.7)
    lichen = smoothstep(0.8, 0.86, fbm(size, 40, 3, seed + 5))
    alb = lerp(alb, np.array([0.62, 0.6, 0.42]), lichen[..., None] * 0.5)
    h = (1 - f1) * 0.5 + face * 0.5 - crack * 0.8 + strata * 0.15
    save_pair("rock_cliff", alb * grime(size, seed + 6, 0.2)[..., None], h, 6.0)


def tex_grass(size=1024, seed=511):
    blades = value_noise(size, 260, seed, 60) * 0.5 + value_noise(size, 120, seed + 1, 30) * 0.5
    big = fbm(size, 4, 5, seed + 2)
    alb = colorize(np.clip(big * 0.7 + blades * 0.4 - 0.05, 0, 1), ["#2e3a1a", "#3e4e22", "#52622c", "#66743a", "#7a8448"])
    dry = smoothstep(0.62, 0.8, fbm(size, 6, 4, seed + 3))
    alb = lerp(alb, colorize(blades, ["#6a6236", "#8a7c48"]), dry[..., None] * 0.6)
    dirt = smoothstep(0.72, 0.84, fbm(size, 5, 5, seed + 4))
    alb = lerp(alb, colorize(fbm(size, 30, 3, seed + 5), ["#4a3a28", "#5e4a32"]), dirt[..., None] * 0.8)
    flowers = (value_noise(size, 400, seed + 6, 400) > 0.965) & (dry < 0.5)
    alb = np.where(flowers[..., None], np.array([0.85, 0.82, 0.55]), alb)
    save_pair("grass", alb, blades * 0.6 + big * 0.4, 3.0)


def tex_dirt(size=1024, seed=521):
    f = fbm(size, 8, 6, seed)
    pebbles_f1, _, pid = voronoi(size, 48, seed + 1, 0.9)
    peb = smoothstep(0.22, 0.12, pebbles_f1) * (pid > 0.55)
    alb = colorize(np.clip(f, 0, 1), ["#4a3a2a", "#5e4a34", "#6e583e", "#7e6848"])
    alb = lerp(alb, colorize(pid, ["#6e665a", "#8e8474", "#a09482"]), peb[..., None] * 0.9)
    ruts = smoothstep(0.55, 0.75, value_noise(size, 4, seed + 2, 40))
    alb *= (1 - 0.18 * ruts)[..., None]
    save_pair("dirt", alb * grime(size, seed + 3, 0.2)[..., None], f * 0.5 + peb * 0.5, 3.0)


# ----------------------------------------------------------------------------- decals
def tex_target(size=512, seed=531):
    """Archery target face: painted rings on straw (fit)."""
    ys, xs = (np.mgrid[0:size, 0:size].astype(np.float32) / size - 0.5) * 2
    r = np.sqrt(xs ** 2 + ys ** 2)
    straw = colorize(value_noise(size, 90, seed, 6) * 0.6 + fbm(size, 8, 3, seed + 1) * 0.4, ["#8a7038", "#a88a48", "#c4a462"])
    rings = [(0.18, "#d2a838"), (0.38, "#8a1e16"), (0.58, "#2a3e5e"), (0.78, "#1e1a16"), (0.97, "#d6ccb2")]
    alb = straw.copy()
    for rr, c in reversed(rings):
        alb = np.where((r < rr)[..., None], hexc(c) * (0.85 + 0.2 * straw / straw.max()), alb)
    holes = value_noise(size, 200, seed + 2, 200) > 0.97
    alb = np.where((holes & (r < 0.97))[..., None], alb * 0.3, alb)
    save("target_face", alb)


def tex_tavern_sign(size=512, seed=541):
    """Hanging tavern sign: a foaming tankard painted on a dark board with a gold frame (fit)."""
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    board = colorize(fbm(size, 4, 5, seed, cells_y=16), ["#2a1c12", "#3a2818", "#4a3420"])
    alb = board.copy()
    mug = (np.abs(xs - 0.47) < 0.17) & (ys > 0.34) & (ys < 0.8)
    handle = (np.abs(np.sqrt((xs - 0.66) ** 2 + (ys - 0.55) ** 2) - 0.1) < 0.03) & (xs > 0.64)
    foam = (np.sqrt(((xs - 0.47) / 0.2) ** 2 + ((ys - 0.33) / 0.09) ** 2) < 1) | \
           (np.sqrt(((xs - 0.38) / 0.1) ** 2 + ((ys - 0.3) / 0.08) ** 2) < 1) | \
           (np.sqrt(((xs - 0.57) / 0.1) ** 2 + ((ys - 0.31) / 0.07) ** 2) < 1)
    pewter = colorize(fbm(size, 10, 3, seed + 1), ["#8a6a2a", "#c09040", "#e0b860"])
    alb = np.where((mug | handle)[..., None], pewter, alb)
    hoops = mug & ((np.abs(ys - 0.45) < 0.012) | (np.abs(ys - 0.7) < 0.012))
    alb = np.where(hoops[..., None], np.array([0.25, 0.18, 0.08]), alb)
    alb = np.where(foam[..., None], np.array([0.92, 0.88, 0.76]), alb)
    frame = (xs < 0.05) | (xs > 0.95) | (ys < 0.05) | (ys > 0.95)
    alb = np.where(frame[..., None], pewter * 0.85, alb)
    save("tavern_sign", alb * grime(size, seed + 2, 0.25)[..., None])


def tex_gravestone(size=512, seed=551):
    """Weathered gravestone face with an engraved cross (fit)."""
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    stone = colorize(fbm(size, 6, 5, seed), ["#5a5650", "#6e6a62", "#828074"])
    cross = ((np.abs(xs - 0.5) < 0.04) & (ys > 0.18) & (ys < 0.62)) | ((np.abs(ys - 0.3) < 0.035) & (np.abs(xs - 0.5) < 0.16))
    lines = (np.abs(((ys - 0.7) * 14) % 1 - 0.5) > 0.42) & (ys > 0.68) & (ys < 0.9) & (np.abs(xs - 0.5) < 0.3) & \
            (value_noise(size, 40, seed + 1, 4) > 0.35)
    alb = np.where((cross | lines)[..., None], stone * 0.45, stone)
    moss = smoothstep(0.6, 0.75, fbm(size, 6, 4, seed + 2)) * smoothstep(0.4, 1.0, ys)
    alb = lerp(alb, np.array([0.24, 0.3, 0.14]), moss[..., None] * 0.7)
    save("gravestone", alb)


def generate_locations():
    print("Generating run-2 textures")
    tex_shield()
    tex_tabard()
    tex_banner()
    tex_rock()
    tex_grass()
    tex_dirt()
    tex_target()
    tex_tavern_sign()
    tex_gravestone()
    tex_ashlar("stone_bridge", ["#5e544a", "#6c6156", "#7a6e60", "#857868", "#665b50"], "#3a332c", rows=7, seed=561, soot=0.3)
    print("Run-2 textures done")
