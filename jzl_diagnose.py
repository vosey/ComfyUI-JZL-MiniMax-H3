#!/usr/bin/env python
"""一句话给用户：把这份报告发我 —— JZL MiniMax 落盘环境自检。

用法（用你 ComfyUI 自己的 python 跑，路径按你的安装改）：

    "X:\\ComfyUI\\python_embeded\\python.exe" "X:\\ComfyUI\\custom_nodes\\ComfyUI-JZL-MiniMax-H3\\jzl_diagnose.py"

或者在 ComfyUI 目录里：
    python custom_nodes/ComfyUI-JZL-MiniMax-H3/jzl_diagnose.py

脚本会打印一份环境报告（ffmpeg / PyAV / 输出目录权限 / 磁盘空间 / 显卡等），
并同时在 output/jzl/_诊断/ 下写一份 txt —— 把那段 txt 内容发回即可定位落盘失败原因。
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
# 允许从任意位置运行（例如直接把文件拖进 cmd 里执行）
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# ComfyUI 根目录加进 sys.path，便于探测 folder_paths / torch
_COMFY_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if os.path.isfile(os.path.join(_COMFY_ROOT, "folder_paths.py")) and _COMFY_ROOT not in sys.path:
    sys.path.insert(0, _COMFY_ROOT)

from jzl_env_check import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
