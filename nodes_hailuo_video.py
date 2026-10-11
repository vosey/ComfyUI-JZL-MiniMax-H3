"""
JZL MiniMax H3 — 海螺H3视频参数节点
====================================
从 XB_ToolBox 的 XB_HailuoH3VideoParams 搬运，去掉帧率设置与输出端口。
分辨率公式复刻官方 ResolutionSelector（MP×1024² → sqrt → round/multiple）。
时间调节（步长 0.5 秒），帧数按 MiniMax H3 固定 24fps 自动推算。
duration 与「剧本与镜头处理器」的 segment_duration 通过前端 JS 双向联动。
"""

import math
import nodes

ASPECT_RATIOS = {
    "1:1 (Square)":             (1, 1),
    "2:3 (Portrait Photo)":     (2, 3),
    "3:2 (Photo)":              (3, 2),
    "3:4 (Portrait Standard)":  (3, 4),
    "4:5 (Portrait Tall)":      (4, 5),
    "4:3 (Standard)":           (4, 3),
    "5:4 (Landscape Tall)":     (5, 4),
    "9:16 (Portrait Widescreen)": (9, 16),
    "16:9 (Widescreen)":        (16, 9),
    "21:9 (Ultrawide)":         (21, 9),
}


class JZL_HailuoH3VideoParams:
    """海螺H3视频参数 — ResolutionSelector 分辨率公式 + 时长(秒)控制。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "aspect_ratio": (list(ASPECT_RATIOS.keys()), {"default": "16:9 (Widescreen)"}),
                "megapixels": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 16.0, "step": 0.1}),
                "multiple": ("INT", {"default": 32, "min": 8, "max": 128, "step": 4}),
                "frames_display": ("STRING", {"default": "Frames: 0", "multiline": False}),
                "duration": ("INT", {
                    "default": 8, "min": 4, "max": 60, "step": 1,
                    "tooltip": "视频时长 (秒), MiniMax H3 支持 4–60 秒。与「剧本与镜头处理器」的每段视频时长联动"
                }),
                "scale_factor": ("FLOAT", {
                    "default": 1.0, "min": 1.0, "max": 5.0, "step": 0.1,
                    "tooltip": "参考图放大系数 — 接入「MiniMax H3 参考编码」的参考值放大"
                }),
            }
        }

    RETURN_TYPES = ("INT", "INT", "INT", "FLOAT")
    RETURN_NAMES = ("Width", "Height", "Frames", "参考图放大系数")
    FUNCTION = "process"
    CATEGORY = "JZL/MiniMax"

    def process(self, aspect_ratio, megapixels, multiple, frames_display, duration, scale_factor):
        # ── 分辨率：官方 ResolutionSelector 公式 ──
        w_ratio, h_ratio = ASPECT_RATIOS.get(aspect_ratio, (16, 9))
        total_pixels = megapixels * 1024 * 1024
        scale = math.sqrt(total_pixels / (w_ratio * h_ratio))
        safe_w = round(w_ratio * scale / multiple) * multiple
        safe_h = round(h_ratio * scale / multiple) * multiple

        # ── 时长 → 帧数换算（MiniMax H3 固定 24fps，吸附 17k+5 网格） ──
        base = max(5, round(duration * 24))
        safe_len = base + (5 - (base % 17)) % 17

        return (safe_w, safe_h, safe_len, scale_factor)


class JZL_HailuoH3VideoParamsPro:
    """海螺H3视频参数Pro — 在视频参数基础上新增「二采放大倍数」。

    二采放大倍数（upscale_scale）接入 Minimax H3 Latent Upscaler (3D) 的 scale。
    二采条件同步节点自动读放大后 latent 尺寸对齐关键帧，无需接此参数。
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "aspect_ratio": (list(ASPECT_RATIOS.keys()), {"default": "16:9 (Widescreen)"}),
                "megapixels": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 16.0, "step": 0.1}),
                "multiple": ("INT", {"default": 32, "min": 8, "max": 128, "step": 4}),
                "frames_display": ("STRING", {"default": "Frames: 0", "multiline": False}),
                "duration": ("INT", {
                    "default": 8, "min": 4, "max": 60, "step": 1,
                    "tooltip": "视频时长 (秒), MiniMax H3 支持 4–60 秒。与「剧本与镜头处理器」的每段视频时长联动"
                }),
                "scale_factor": ("FLOAT", {
                    "default": 1.0, "min": 1.0, "max": 5.0, "step": 0.1,
                    "tooltip": "参考图放大系数 — 接入「MiniMax H3 参考编码」的参考值放大"
                }),
                "upscale_scale": ("FLOAT", {
                    "default": 1.5, "min": 1.0, "max": 4.0, "step": 0.05,
                    "tooltip": "二采放大倍数 — 接入 Minimax H3 Latent Upscaler (3D) 的 scale。二采条件同步自动读放大后 latent 尺寸，无需接此参数"
                }),
            }
        }

    RETURN_TYPES = ("INT", "INT", "INT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("Width", "Height", "Frames", "参考图放大系数", "二采放大倍数")
    FUNCTION = "process"
    CATEGORY = "JZL/MiniMax"

    def process(self, aspect_ratio, megapixels, multiple, frames_display, duration, scale_factor, upscale_scale):
        # ── 分辨率：官方 ResolutionSelector 公式 ──
        w_ratio, h_ratio = ASPECT_RATIOS.get(aspect_ratio, (16, 9))
        total_pixels = megapixels * 1024 * 1024
        scale = math.sqrt(total_pixels / (w_ratio * h_ratio))
        safe_w = round(w_ratio * scale / multiple) * multiple
        safe_h = round(h_ratio * scale / multiple) * multiple

        # ── 时长 → 帧数换算（MiniMax H3 固定 24fps，吸附 17k+5 网格） ──
        base = max(5, round(duration * 24))
        safe_len = base + (5 - (base % 17)) % 17

        return (safe_w, safe_h, safe_len, scale_factor, upscale_scale)
