"""blender -b --factory-startup -P make_textures_locations.py  -> run-2 textures (+ redrawn lion) in blender/textures/"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_tex2  # noqa: E402

lib_tex2.generate_locations()
