# ═══════════════════════════════════════════════════════════════════════════
# 【第三方代码副本 · vendored】本目录整体搬自 comfyui-SelfLift，请勿直接改业务逻辑。
#
# 原插件：comfyui-SelfLift（ComfyUI/custom_nodes/comfyui-SelfLift）
# 文件：  h3_tiling.py
# 校验：  SHA-256 dd285f1af595c945d974de8e734b779bc4dad5bf125bc312895070bfa31a83bd（上游原文件）
# 本地补丁：2026-10-16 _tile_payload 分块时同步裁窄 keyframe 的 cond（标记 JZL_LOCAL_PATCH_TILE_KEYFRAME）
#           —— 上游原文在有 minimax_refs 时会漏掉重建，导致「分段衔接 + 参考素材 + 分块≥2块」行数不匹配崩溃。
#           （补丁后文件 SHA-256 与上游原文不同，属预期；请在函数内按标记核对补丁是否还在。）
#           升级上游时若补丁消失，nodes_asset_manager.py 的 _selflift_tiling_keyframe_patched() 会检测到，
#           并自动关闭本次「高分辨率分块」并在日志告警（不会静默崩）。
# 论文：  SelfLift arXiv:2609.02036 ；TST arXiv:2609.08505
#         可选 H3 latent upscaler 权重：LBH-123-AI/Minimax_h3_latent_Upscaler
#
# 用途：JZL 导演台「采样解码设置 → 采样分类 = SelfLift采样」内部调用
#       SelfLiftH3Sampler，使本插件不再依赖用户另行安装 comfyui-SelfLift。
# 隔离：本目录为本插件私有子包，**不导出** NODE_CLASS_MAPPINGS；
#       用户自装的 comfyui-SelfLift 若存在，其节点与本副本互不影响。
# 升级：用上游新版本覆盖本目录文件（保留顶部注释块），并更新 SHA-256。
# ═══════════════════════════════════════════════════════════════════════════
"""Experimental spatial tiling of H3 high-resolution model evaluations."""

from functools import partial
import inspect
import logging
import math

import torch

import comfy.ldm.common_dit
from comfy.ldm.minimax.model import PackedLayout
import comfy.model_base
import comfy.patcher_extension
import comfy.sampler_helpers


def _regions(length, tile_count=2):
    patches = (length + 1) // 2
    tile_count = max(1, min(tile_count, max(1, patches // 2)))
    if patches < 4 or tile_count <= 1:
        return [(0, length)]
    overlap = min(4, max(1, patches // 8))
    regions = []
    for index in range(tile_count):
        start = max(0, index * patches // tile_count - overlap) * 2
        end = min(patches, (index + 1) * patches // tile_count + overlap) * 2
        end = min(end, length)
        regions.append((start, end))
    regions[-1] = (regions[-1][0], length)
    return regions


def _packed_layout(signature, payload):
    options = {"keyframes": payload.get("keyframes"), "refs": payload.get("refs")}
    if "frame_count" in inspect.signature(PackedLayout).parameters:
        options["frame_count"] = payload.get("frame_count")
    return PackedLayout(*signature, **options)


def _tile_payload(payload, context, video, audio, axis, start, end):
    height, width = video.shape[-2:]
    padded_height, padded_width = (height + 1) // 2 * 2, (width + 1) // 2 * 2
    full_layout = payload.get("layout")
    signature = (context.shape[1], video.shape[2], padded_height, padded_width, audio.shape[-1])
    if full_layout is None or full_layout.signature != signature:
        full_layout = _packed_layout(signature, payload)
    tiled = payload.copy()
    if payload.get("keyframes"):
        keyframes = []
        for keyframe in payload["keyframes"]:
            latent = keyframe["latent"]
            if latent.shape[-2:] != (height, width):
                raise ValueError("SelfLift: tiled H3 keyframes must match the target latent height and width")
            region = latent.narrow(axis, start, end - start)
            keyframes.append({**keyframe, "latent": comfy.ldm.common_dit.pad_to_patch_size(
                region, (1, 2, 2)).contiguous()})
        tiled["keyframes"] = keyframes
        # ── JZL_LOCAL_PATCH_TILE_KEYFRAME ────────────────────────────────────────
        # 上游原文：`if not payload.get("refs"): tiled["cond_video_latents"] = [...]`
        # 缺陷：有 refs 时整个重建被跳过，cond_video_latents 仍指向**未分块的全画布 keyframe latent**
        #       → comfy/ldm/minimax/model.py:_embed_and_pack 里 `all_video_rows[~img_update] = cond_video_rows`
        #         行数不匹配 → RuntimeError: shape mismatch: value tensor of shape [N, 96] cannot be
        #         broadcast to indexing result of shape [M, 96]
        #       触发条件：minimax_keyframes（分段衔接）+ minimax_refs（参考素材）+ 高分辨率分块≥2块
        # 修法：与 comfy/model_base.py:2202 同序重建（keyframe 在前、refs 在后），且始终执行。
        # ─────────────────────────────────────────────────────────────────────────
        tiled["cond_video_latents"] = [keyframe["latent"] for keyframe in keyframes] + \
            [reference["latent"] for reference in (payload.get("refs") or []) if "latent" in reference]
    tile_height = end - start if axis == 3 else height
    tile_width = end - start if axis == 4 else width
    layout = _packed_layout((context.shape[1], video.shape[2], (tile_height + 1) // 2 * 2,
                             (tile_width + 1) // 2 * 2, audio.shape[-1]), tiled)
    for (source_start, source_end, kind), (target_start, target_end, _) in zip(full_layout.segments, layout.segments):
        positions = full_layout.position_ids[source_start:source_end]
        if kind in ("cond", "video"):
            positions = positions.reshape(-1, padded_height // 2, padded_width // 2, 3)
            positions = positions.narrow(axis - 2, start // 2, (end - start + 1) // 2).reshape(-1, 3)
        layout.position_ids[target_start:target_end].copy_(positions)
    tiled["layout"] = layout
    return tiled


def _tiled_forward(executor, streams, timestep, context, transformer_options, minimax_payload=None,
                   n_tiles=2, plan=None, **kwargs):
    video, audio = streams
    axis = 3 if (video.shape[3] + 1) // 2 >= (video.shape[4] + 1) // 2 else 4
    length = video.shape[axis]
    regions = _regions(length, plan['tiles'] if plan is not None else n_tiles)
    if len(regions) == 1:
        return executor(streams, timestep, context, transformer_options, minimax_payload=minimax_payload, **kwargs)
    if kwargs.get("control") is not None:
        raise ValueError("SelfLift: high-resolution H3 tiling does not support ControlNet")
    # Keep the stitched accumulator on CPU so previous tiles do not remain on
    # the accelerator while the next tile is evaluated.
    video_output = torch.zeros(video.shape, dtype=torch.float32, device="cpu")
    audio_output = None
    weights = torch.zeros(length, dtype=torch.float32, device="cpu")
    for index, (start, end) in enumerate(regions):
        tile = video.narrow(axis, start, end - start).contiguous()
        payload = _tile_payload(minimax_payload or {}, context, video, audio, axis, start, end)
        predicted_video, predicted_audio = executor(
            [tile, audio], timestep, context, transformer_options.copy(), minimax_payload=payload, **kwargs)
        window = torch.ones(end - start, device=video.device, dtype=torch.float32)
        if index > 0:
            overlap = min(end, regions[index - 1][1]) - start
            window[:overlap] *= (torch.arange(overlap, device=video.device, dtype=torch.float32) + 0.5) / overlap
        if index + 1 < len(regions):
            overlap = end - regions[index + 1][0]
            window[-overlap:] *= 1.0 - (torch.arange(overlap, device=video.device, dtype=torch.float32) + 0.5) / overlap
        predicted_video = predicted_video.float().cpu()
        window = window.cpu()
        weights[start:end].add_(window)
        window_shape = [1] * video.ndim
        window_shape[axis] = end - start
        video_output.narrow(axis, start, end - start).addcmul_(predicted_video.float(), window.view(window_shape))
        if audio_output is None:
            audio_output = predicted_audio.float().clone()
        del tile, payload, predicted_video, predicted_audio, window
    window_shape[axis] = length
    video_output.div_(weights.view(window_shape))
    return [video_output.to(device=video.device, dtype=video.dtype), audio_output.to(audio.dtype)]


def _condition_elements(condition, tile_height, tile_width, channels):
    text = condition.get("cross_attn")
    elements = text.shape[-2] * channels * 4 if text is not None else 0
    for keyframe in condition.get("minimax_keyframes") or []:
        shape = keyframe["latent"].shape
        elements += shape[1] * shape[2] * tile_height * tile_width
    for reference in condition.get("minimax_refs") or []:
        latent = reference.get("latent")
        if latent is not None:
            shape = latent.shape
            elements += shape[1] * shape[2] * ((shape[3] + 1) // 2 * 2) * ((shape[4] + 1) // 2 * 2)
        audio = reference.get("audio_latent")
        if audio is not None:
            elements += math.prod(audio.shape[1:])
    return elements


def _budget(model, noise_shape, conds, latent_shapes, regions, axis):
    video_shape, audio_shape = latent_shapes
    full_elements = math.prod(video_shape[1:]) + math.prod(audio_shape[1:])
    tile_shape = list(video_shape)
    tile_shape[axis] = max(end - start for start, end in regions)
    tile_shape[3] = (tile_shape[3] + 1) // 2 * 2
    tile_shape[4] = (tile_shape[4] + 1) // 2 * 2
    tile_elements = math.prod(tile_shape[1:]) + math.prod(audio_shape[1:])
    condition_elements = max((_condition_elements(condition, tile_shape[3], tile_shape[4], video_shape[1])
                              for group in conds.values() for condition in (group or [])), default=0)
    buffer_bytes = full_elements * 4 * 8
    bytes_per_element = model.model.memory_required((1, 1, 1))
    budget_elements = tile_elements + condition_elements + math.ceil(buffer_bytes / bytes_per_element)
    budget_shape = (noise_shape[0], 1, budget_elements)
    preferred, minimum = comfy.sampler_helpers.estimate_memory(model, budget_shape, conds)
    return budget_shape, tuple(tile_shape), buffer_bytes, preferred, minimum


def _prepare_tiled_sampling(executor, model, noise_shape, conds, model_options=None,
                            force_full_load=False, force_offload=False, *, latent_shapes, plan=None):
    video_shape, audio_shape = latent_shapes
    axis = 3 if (video_shape[3] + 1) // 2 >= (video_shape[4] + 1) // 2 else 4
    full_elements = math.prod(video_shape[1:]) + math.prod(audio_shape[1:])
    if tuple(noise_shape) != (video_shape[0], 1, full_elements):
        raise ValueError("SelfLift: tiled memory planning received a different latent shape than the sampling input")
    count = 2
    if plan is not None:
        available = _available_workspace(model)
        for count in range(1, 9):
            regions = _regions(video_shape[axis], count)
            _, _, _, _, minimum = _budget(model, noise_shape, conds, latent_shapes, regions, axis)
            if minimum <= available:
                break
        count = len(regions)
        plan['tiles'] = count
        logging.info("[SelfLift tiling plan] axis=%s tiles=%d target=%.2f MiB estimate_fits=%s",
                     'H' if axis == 3 else 'W', plan['tiles'], available / 2**20, minimum <= available)
    regions = _regions(video_shape[axis], count)
    if len(regions) == 1 or force_offload:
        return executor(model, noise_shape, conds, model_options=model_options,
                        force_full_load=force_full_load, force_offload=force_offload)
    budget_shape, tile_shape, buffer_bytes, preferred, minimum = _budget(
        model, noise_shape, conds, latent_shapes, regions, axis)
    logging.info("[SelfLift tiling memory] largest_tile=%s full_audio=%s full_state_buffers=%.2f MiB "
                 "minimum=%.2f MiB preferred=%.2f MiB (ComfyUI estimates; additional models and reserves excluded)",
                 tuple(tile_shape), audio_shape, buffer_bytes * noise_shape[0] / 2**20,
                 minimum / 2**20, preferred / 2**20)
    return executor(model, budget_shape, conds, model_options=model_options,
                    force_full_load=force_full_load, force_offload=force_offload)


def _available_workspace(model):
    manager = comfy.model_management
    free = manager.get_free_memory(model.load_device)
    reclaimable = 0
    seen = set()
    for loaded in manager.loaded_models():
        patcher = loaded if callable(getattr(loaded, "loaded_size", None)) else loaded.model
        load_device = getattr(patcher, "load_device", None)
        identity = id(patcher.model)
        if load_device == model.load_device and identity not in seen:
            seen.add(identity)
            size_fn = getattr(patcher, "loaded_size", None)
            if callable(size_fn):
                reclaimable += size_fn()
    pool = min(manager.get_total_memory(model.load_device), free + reclaimable)
    weights = min(model.model_size(), pool * manager.MIN_WEIGHT_MEMORY_RATIO)
    available = max(0, pool - weights - manager.minimum_inference_memory())
    logging.info("[SelfLift tiling capacity] free=%.2f MiB reclaimable_weights=%.2f MiB "
                 "weight_allowance=%.2f MiB workspace=%.2f MiB",
                 free / 2**20, reclaimable / 2**20, weights / 2**20, available / 2**20)
    return available


def tiled_model(model, latent_shapes):
    if not isinstance(model.model, comfy.model_base.MiniMaxH3):
        raise ValueError("SelfLift: high-resolution tiling requires a MiniMax H3 model")
    if len(latent_shapes) != 2 or len(latent_shapes[0]) != 5 or len(latent_shapes[1]) != 4:
        raise ValueError("SelfLift: high-resolution tiling requires H3 video and audio latent streams")
    plan = {}
    patched = model.clone()
    patched.add_wrapper_with_key(comfy.patcher_extension.WrappersMP.DIFFUSION_MODEL,
                                 "selflift_high_resolution_tiling", partial(_tiled_forward, plan=plan))
    patched.add_wrapper_with_key(comfy.patcher_extension.WrappersMP.PREPARE_SAMPLING,
                                 "selflift_high_resolution_tiling",
                                 partial(_prepare_tiled_sampling, latent_shapes=tuple(tuple(shape) for shape in latent_shapes), plan=plan))
    return patched
