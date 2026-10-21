"""JZL H3 二采空间分块（自研实现，不参考任何第三方分块代码）。

思路
────────────────────────────────────────────────────────────────────────
把一次「整画布」的模型前向，沿长边切成若干块 → 逐块前向 → 按重叠窗加权融合回整画布。

采样器每一步只调用一次前向、拿到的是**融合后**的结果，因此等价于
「每步先融合全部块、再推进」= 逐步同步融合；且天然对任意采样器
（euler / res_multistep / dpmpp / …）成立，不必复刻采样循环的推进逻辑。

为什么挂在「前向级」而不是手写采样循环
────────────────────────────────────────────────────────────────────────
· 采样器无关：手写循环只能覆盖 euler 系，其它采样器只能退回「每块各跑完整轨迹再拼」
  （轨迹不同 → 接缝不一致，是更粗的近似）
· 与全画布行为天然一致：sigmas / denoise_mask / callback / 调度推进全由 ComfyUI 原逻辑负责，
  本模块只替换「一次前向内部怎么算」，不碰任何采样状态
· 与 ComfyUI 显存规划对接：PREPARE_SAMPLING 扩展点按「最大块 + 完整音频」上报显存需求，
  让模型按块尺寸而非整画布驻留

H3 特有的两个坑（不处理会让接缝处 RoPE 错位）
────────────────────────────────────────────────────────────────────────
① DiT 用 PackedLayout 组装序列，位置编码来自 layout.position_ids。分块后画布变小 →
   必须把「整画布 layout 中对应本块的那段位置」回填进块 layout，否则块会以为自己在小画布原点。
② 空间轴切片必须**偶数对齐**：DiT 的 2x2 patch 会把 h/w 向上补齐，
   奇数起点会让补齐后的网格与整画布错位一格。
另外 fl2va 的 keyframe 条件 latent 与目标同空间分辨率，也要按块裁剪并重新补齐。

音频
────────────────────────────────────────────────────────────────────────
音频 latent 不参与空间分块（每块都喂完整音频），各块都会给出「整条音频」的预测，
故按等权平均融合（每块是同一音频在不同画面区域下的一个视角）。
"""

from functools import partial
import math

import torch

import comfy.ldm.common_dit
import comfy.model_management
import comfy.patcher_extension
import comfy.sampler_helpers
from comfy.ldm.minimax.model import PackedLayout

_WRAPPER_KEY = "jzl_h3_spatial_tiling"

_AXIS_H, _AXIS_W = 3, 4            # video latent (B,C,T,H,W) 的 H/W 轴
_PATCH = (1, 2, 2)                 # DiT patch：时间不切、空间 2x2
_PX_PER_GRID_CELL = 32             # 1 latent 格 = 16px；2x2 patch ⇒ 1 个网格格 = 32px
_MAX_TILES = 8
_AUTO_FALLBACK_TILES = 2           # 显存测不出来时的保守块数


# ── 基础工具 ────────────────────────────────────────────────────────────

def _even(v):
    return (int(v) + 1) // 2 * 2


def _prod(shape):
    n = 1
    for v in shape:
        n *= int(v)
    return n


def _long_axis(video_shape):
    """空间长边所在轴（切两块以上才有意义）。"""
    return _AXIS_H if _even(video_shape[_AXIS_H]) >= _even(video_shape[_AXIS_W]) else _AXIS_W


def _split_av(x):
    if isinstance(x, (list, tuple)):
        return x[0], (x[1] if len(x) > 1 else None)
    if hasattr(x, "unbind"):
        parts = x.unbind()
        return parts[0], (parts[1] if len(parts) > 1 else None)
    return x, None


def _plan_regions(length, count, overlap_cells):
    """把空间 latent 长度切成 count 块，返回 [(start, end)]（偶数对齐、完整覆盖）。

    偶数对齐是硬约束，见模块注释 ②。overlap_cells = 每侧重叠的网格格数。
    """
    cells = (length + 1) // 2
    count = max(1, min(int(count or 1), _MAX_TILES, max(1, cells // 2)))
    if count <= 1 or cells < 4:
        return [(0, int(length))]
    ov = max(0, min(int(overlap_cells or 0), cells // (count + 1)))
    spans = []
    for i in range(count):
        spans.append([max(0, i * cells // count - ov), min(cells, (i + 1) * cells // count + ov)])
    spans[0][0] = 0
    spans[-1][1] = cells
    return [(lo * 2, min(hi * 2, int(length))) for lo, hi in spans]


def _cosine_window(n, fade_lo, fade_hi, axis, ndim):
    """1D 升余弦窗（两端各 fade 格渐变、中段为 1），形状已按 axis 广播到 ndim 维。

    用升余弦而非线性三角：权重在交接处一阶连续，避免融合边出现亮度棱线。
    """
    w = torch.ones(int(n), dtype=torch.float32)
    if fade_lo > 0:
        t = (torch.arange(int(fade_lo), dtype=torch.float32) + 0.5) / float(fade_lo)
        w[:int(fade_lo)] *= 0.5 - 0.5 * torch.cos(math.pi * t)
    if fade_hi > 0:
        t = (torch.arange(int(fade_hi), dtype=torch.float32) + 0.5) / float(fade_hi)
        w[int(n) - int(fade_hi):] *= 0.5 + 0.5 * torch.cos(math.pi * t)
    shape = [1] * int(ndim)
    shape[axis] = int(n)
    return w.view(shape)


# ── H3 layout / payload 分块 ───────────────────────────────────────────

def _make_layout(signature, payload):
    """按 signature 构造 PackedLayout（keyframes / refs 会改变行数，必须一并带上）。"""
    return PackedLayout(*signature, keyframes=payload.get("keyframes"), refs=payload.get("refs"))


def _carry_positions(full_layout, tile_layout, axis, start, end, padded_h, padded_w):
    """把整画布 layout 的 position_ids 按块回填（只有 cond / video 段需要空间裁剪）。"""
    cells = (end - start + 1) // 2
    for (src_a, src_b, kind), (dst_a, dst_b, _) in zip(full_layout.segments, tile_layout.segments):
        pos = full_layout.position_ids[src_a:src_b]
        if kind in ("cond", "video"):
            # position_ids 是 (t,h,w)；重排成 (t*h*w, 3) 后按空间轴切出本块
            pos = pos.reshape(-1, padded_h // 2, padded_w // 2, 3).narrow(axis - 2, start // 2, cells).reshape(-1, 3)
        tile_layout.position_ids[dst_a:dst_b].copy_(pos)


def _tile_payload(payload, context, video, audio, axis, start, end):
    """把整画布的 minimax_payload 改写成「本块画布」版本。

    · keyframe 条件 latent（与目标同空间分辨率）按块裁剪 + 重新补齐
    · 重建块 layout，并回填整画布对应位置（模块注释 ①）
    · refs（身份参考，与目标画布解耦）原样保留
    """
    if not payload:
        return payload
    h, w = int(video.shape[_AXIS_H]), int(video.shape[_AXIS_W])
    padded_h, padded_w = _even(h), _even(w)
    signature = (int(context.shape[1]), int(video.shape[2]), padded_h, padded_w, int(audio.shape[-1]))
    full_layout = payload.get("layout")
    if full_layout is None or getattr(full_layout, "signature", None) != signature:
        full_layout = _make_layout(signature, payload)

    tiled = dict(payload)
    keyframes = payload.get("keyframes")
    if keyframes:
        cropped = []
        for kf in keyframes:
            latent = kf.get("latent")
            if latent is not None and tuple(latent.shape[-2:]) == (h, w):
                region = latent.narrow(axis, start, end - start).contiguous()
                cropped.append({**kf, "latent": comfy.ldm.common_dit.pad_to_patch_size(region, _PATCH).contiguous()})
            else:
                cropped.append(kf)
        tiled["keyframes"] = cropped
        # cond_video_latents 的顺序与 model_base 一致：先 keyframes、再 refs。
        # 有 refs 时也必须替换 keyframe 项（refs 与画布解耦，原样保留），否则条件行仍是整画布宽度 →
        # 块画布与条件行数不匹配。
        kf_rows = [kf["latent"] for kf in cropped if kf.get("latent") is not None]
        ref_rows = [r["latent"] for r in (payload.get("refs") or []) if r.get("latent") is not None]
        tiled["cond_video_latents"] = kf_rows + ref_rows

    tile_h = end - start if axis == _AXIS_H else h
    tile_w = end - start if axis == _AXIS_W else w
    tile_layout = _make_layout(
        (int(context.shape[1]), int(video.shape[2]), _even(tile_h), _even(tile_w), int(audio.shape[-1])), tiled)
    tiled["layout"] = tile_layout
    _carry_positions(full_layout, tile_layout, axis, start, end, padded_h, padded_w)
    return tiled


# ── DIFFUSION_MODEL wrapper：一次前向内切块 + 融合 ──────────────────────

def _tiled_forward(executor, x, timestep, context, transformer_options,
                   minimax_payload=None, denoise_mask=None, audio_denoise_mask=None,
                   cfg=None, **kwargs):
    cfg = cfg or {}

    def _plain():
        return executor(x, timestep, context, transformer_options, minimax_payload=minimax_payload,
                        denoise_mask=denoise_mask, audio_denoise_mask=audio_denoise_mask, **kwargs)

    if not cfg.get("enabled"):
        return _plain()

    video, audio = _split_av(x)
    if video is None or audio is None or video.dim() != 5:
        return _plain()
    if denoise_mask is not None or audio_denoise_mask is not None:
        # 蒙版按整画布布局生成，分块会与块画布错配 → 本次退回整画布（并记一次提示）
        cfg["mask_hits"] = int(cfg.get("mask_hits") or 0) + 1
        return _plain()

    axis = int(cfg.get("axis") or _long_axis(video.shape))
    regions = _plan_regions(int(video.shape[axis]), cfg.get("tiles") or 1, cfg.get("overlap_cells") or 0)
    if len(regions) == 1:
        return _plain()

    length = int(video.shape[axis])
    ndim = int(video.dim())

    def _tiled():
        acc = torch.zeros_like(video, dtype=torch.float32, device="cpu")
        wsum = torch.zeros(length, dtype=torch.float32)
        audio_acc = None
        max_fade = max(1, length // 2)

        for idx, (start, end) in enumerate(regions):
            span = end - start
            tile = video.narrow(axis, start, span).contiguous()
            tile_payload = _tile_payload(minimax_payload, context, video, audio, axis, start, end)
            pred_video, pred_audio = executor(
                [tile, audio], timestep, context, transformer_options.copy(),
                minimax_payload=tile_payload, denoise_mask=None, audio_denoise_mask=None, **kwargs)

            # 重叠侧各让出一半：左端与前块重叠则淡入、右端与后块重叠则淡出
            fade_lo = min(span, max(0, regions[idx - 1][1] - start)) if idx > 0 else 0
            fade_hi = min(span, max(0, end - regions[idx + 1][0])) if idx + 1 < len(regions) else 0
            win = _cosine_window(span, min(fade_lo, max_fade), min(fade_hi, max_fade), axis, ndim)

            if tuple(pred_video.shape) != tuple(tile.shape):
                sl = [slice(None)] * pred_video.dim()
                sl[axis] = slice(0, span)
                pred_video = pred_video[tuple(sl)]
            acc.narrow(axis, start, span).add_(pred_video.detach().to(torch.float32).cpu() * win)
            wsum.narrow(0, start, span).add_(win.reshape(-1))
            del win, pred_video

            if pred_audio is not None:
                a = pred_audio.detach().to(torch.float32).cpu()
                audio_acc = a if audio_acc is None else audio_acc + a
            del tile, tile_payload, pred_audio

        wsum.clamp_min_(1e-6)
        shape = [1] * ndim
        shape[axis] = length
        video_out = acc.div_(wsum.view(shape)).to(device=video.device, dtype=video.dtype)
        audio_out = audio if audio_acc is None else (audio_acc / float(len(regions))).to(device=audio.device, dtype=audio.dtype)
        return [video_out, audio_out]

    try:
        return _tiled()
    except Exception as e:
        # 分块失败不拖垮整次渲染：本次退回整画布，并关掉后续步骤的分块（避免每步都重试）
        cfg["enabled"] = False
        cfg["failed"] = f"{type(e).__name__}: {e}"
        print(f"[JZL-{cfg.get('tag') or '二采'}] ⚠️ 空间分块执行失败 → 本次及后续步骤退回整画布：{type(e).__name__}: {e}")
        return _plain()


# ── PREPARE_SAMPLING wrapper：块数决策 + 按块上报显存需求 ───────────────

def _condition_elements(condition, tile_h, tile_w, channels):
    """估算该条 conditioning 在本块画布下占用的元素数（仅用于显存预算）。"""
    n = 0
    text = condition.get("cross_attn")
    if text is not None:
        n += int(text.shape[-2]) * int(channels) * 4
    for kf in condition.get("minimax_keyframes") or []:
        z = kf.get("latent")
        if z is not None and z.dim() >= 5:
            n += int(z.shape[1]) * int(z.shape[2]) * int(tile_h) * int(tile_w)
    for ref in condition.get("minimax_refs") or []:
        z = ref.get("latent")
        if z is not None:
            s = tuple(int(v) for v in z.shape)
            if len(s) >= 5:
                n += s[1] * s[2] * _even(s[3]) * _even(s[4])
            elif len(s) == 4:
                n += s[1] * _even(s[2]) * _even(s[3])
        a = ref.get("audio_latent")
        if a is not None:
            n += _prod(a.shape[1:])
    return n


def _tile_budget(model, noise_shape, conds, latent_shapes, regions, axis):
    """返回 (最小显存需求, 最大块形状)。状态缓冲按整画布估算（那部分不随分块变小）。"""
    video_shape, audio_shape = latent_shapes
    tile_shape = list(video_shape)
    tile_shape[axis] = max(e - s for s, e in regions)
    tile_shape[_AXIS_H] = _even(tile_shape[_AXIS_H])
    tile_shape[_AXIS_W] = _even(tile_shape[_AXIS_W])
    tile_elems = _prod(tile_shape[1:]) + _prod(audio_shape[1:])
    cond_elems = 0
    for group in (conds or {}).values():
        for cond in (group or []):
            cond_elems = max(cond_elems, _condition_elements(cond, tile_shape[_AXIS_H], tile_shape[_AXIS_W], video_shape[1]))
    buffer_bytes = (_prod(video_shape[1:]) + _prod(audio_shape[1:])) * 4 * 8
    try:
        per_elem = float(model.model.memory_required((1, 1, 1))) or 1.0
    except Exception:
        per_elem = 1.0
    budget_elems = tile_elems + cond_elems + int(math.ceil(buffer_bytes / per_elem))
    _, minimum = comfy.sampler_helpers.estimate_memory(model, (int(noise_shape[0]), 1, budget_elems), conds)
    return float(minimum), tuple(tile_shape)


def _available_workspace(model):
    """粗估可用工作显存：空闲 + 可回收权重（按 ComfyUI 比例折扣）− 最低保留。"""
    mm = comfy.model_management
    try:
        pool = float(mm.get_free_memory(model.load_device))
    except Exception:
        return 0.0
    seen = set()
    try:
        for loaded in mm.loaded_models():
            real = getattr(loaded, "model", loaded)
            if id(real) in seen:
                continue
            seen.add(id(real))
            if getattr(real, "load_device", None) != model.load_device:
                continue
            for p in real.parameters():
                if getattr(p, "device", None) == model.load_device:
                    pool += p.numel() * p.element_size()
    except Exception:
        pass
    try:
        weights = min(float(model.model_size()), pool * mm.MIN_WEIGHT_MEMORY_RATIO)
    except Exception:
        weights = 0.0
    try:
        reserve = float(mm.minimum_inference_memory())
    except Exception:
        reserve = 0.0
    return max(0.0, pool - weights - reserve)


def _prepare_wrapper(executor, model, noise_shape, conds, model_options=None,
                     force_full_load=False, force_offload=False, cfg=None, **kwargs):
    """决定块数（自动模式按显存预算），并把「按块尺寸」的显存需求上报给 ComfyUI。"""
    cfg = cfg or {}

    def _plain():
        return executor(model, noise_shape, conds, model_options=model_options,
                        force_full_load=force_full_load, force_offload=force_offload)

    latent_shapes = tuple(cfg.get("latent_shapes") or ())
    if not cfg.get("enabled") or len(latent_shapes) < 2:
        return _plain()

    try:
        video_shape, audio_shape = latent_shapes
        axis = int(cfg.get("axis") or _long_axis(video_shape))
        overlap_cells = int(cfg.get("overlap_cells") or 0)
        want = int(cfg.get("tiles") or 0)

        if want > 1:
            chosen, auto = want, False
        else:
            auto = True
            available = _available_workspace(model)
            chosen = _AUTO_FALLBACK_TILES if available <= 0 else 1
            if available > 0:
                for n in range(1, _MAX_TILES + 1):
                    trial = _plan_regions(int(video_shape[axis]), n, overlap_cells)
                    minimum, _ = _tile_budget(model, noise_shape, conds, latent_shapes, trial, axis)
                    chosen = n
                    if len(trial) > 1 and minimum <= available:
                        break

        regions = _plan_regions(int(video_shape[axis]), chosen, overlap_cells)
        cfg["axis"] = axis
        cfg["tiles"] = len(regions)
        cfg["auto"] = auto
        if len(regions) == 1 or force_offload:
            cfg["enabled"] = False
            why = "强制卸载模式" if force_offload else "该轴上只切出 1 块（无需分块）"
            print(f"[JZL-{cfg.get('tag') or '二采'}] 空间分块：未启用（{why}），本次按整画布二采")
            cfg["skip_reason"] = "force_offload" if force_offload else "single_tile"
            return _plain()

        minimum, tile_shape = _tile_budget(model, noise_shape, conds, latent_shapes, regions, axis)
    except Exception as e:
        # 块数决策失败不拖垮整次渲染：退回整画布
        cfg["enabled"] = False
        cfg["failed"] = f"{type(e).__name__}: {e}"
        print(f"[JZL-{cfg.get('tag') or '二采'}] ⚠️ 空间分块规划失败 → 本次按整画布二采：{type(e).__name__}: {e}")
        return _plain()

    cfg["tile_shape"] = tile_shape
    print(f"[JZL-{cfg.get('tag') or '二采'}] 空间分块：{'自动' if auto else '手动'} {len(regions)} 块"
          f"（沿 {'H' if axis == _AXIS_H else 'W'} 轴，重叠 {overlap_cells} 格，升余弦融合）"
          f"｜最大块 {tuple(int(v) for v in tile_shape)}｜预估最低 {minimum / 2**20:.0f} MiB"
          f"｜音频不分块（等权平均）")
    budget = (int(noise_shape[0]), 1, _prod(tile_shape[1:]) + _prod(audio_shape[1:]))
    return executor(model, budget, conds, model_options=model_options,
                    force_full_load=force_full_load, force_offload=force_offload)


# ── 对外入口 ───────────────────────────────────────────────────────────

def wrap_model(model, latent_shapes, *, tiles=0, overlap_px=128, tag="二采"):
    """返回挂了「二采空间分块」wrapper 的 ModelPatcher 克隆。

    model        : 原 ModelPatcher
    latent_shapes: (video_shape, audio_shape)（放大后的目标形状）
    tiles        : 0 = 按显存预算自动选块数；>=2 = 手动块数
    overlap_px   : 相邻块重叠像素（内部换算成网格格；1 格 = 32px）
    """
    try:
        video_shape, audio_shape = latent_shapes
    except Exception:
        return model
    cfg = {
        "enabled": True,
        "tiles": int(tiles or 0),
        "axis": _long_axis(video_shape),
        "overlap_cells": max(0, int(round(float(overlap_px or 0) / _PX_PER_GRID_CELL))),
        "latent_shapes": (tuple(int(v) for v in video_shape), tuple(int(v) for v in audio_shape)),
        "tag": tag,
        "mask_hits": 0,
    }
    patched = model.clone()
    patched.add_wrapper_with_key(comfy.patcher_extension.WrappersMP.DIFFUSION_MODEL,
                                 _WRAPPER_KEY, partial(_tiled_forward, cfg=cfg))
    patched.add_wrapper_with_key(comfy.patcher_extension.WrappersMP.PREPARE_SAMPLING,
                                 _WRAPPER_KEY, partial(_prepare_wrapper, cfg=cfg))
    patched.__jzl_tiling_cfg = cfg
    return patched


def mask_skipped(model):
    """本次是否因为检测到 denoise mask 而退回整画布（供调用方补一行提示）。"""
    cfg = getattr(model, "__jzl_tiling_cfg", None)
    return bool(cfg and cfg.get("mask_hits"))
