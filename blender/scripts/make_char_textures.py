"""blender -b --factory-startup -P make_char_textures.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_tex_char  # noqa: E402

lib_tex_char.generate_characters()
