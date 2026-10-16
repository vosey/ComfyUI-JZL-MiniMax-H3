# ═══════════════════════════════════════════════════════════════════════════
# 【第三方代码副本 · vendored】本目录整体搬自 comfyui-SelfLift，请勿直接改业务逻辑。
#
# 原插件：comfyui-SelfLift（ComfyUI/custom_nodes/comfyui-SelfLift）
# 文件：  diagnostics.py
# 校验：  SHA-256 a4a81b2ddc6a2f8b4cf6be040c184e0b0b848513ed21a332a7169215f5f55641
# 论文：  SelfLift arXiv:2609.02036 ；TST arXiv:2609.08505
#         可选 H3 latent upscaler 权重：LBH-123-AI/Minimax_h3_latent_Upscaler
#
# 用途：JZL 导演台「采样解码设置 → 采样分类 = SelfLift采样」内部调用
#       SelfLiftH3Sampler，使本插件不再依赖用户另行安装 comfyui-SelfLift。
# 隔离：本目录为本插件私有子包，**不导出** NODE_CLASS_MAPPINGS；
#       用户自装的 comfyui-SelfLift 若存在，其节点与本副本互不影响。
# 升级：用上游新版本覆盖本目录文件（保留顶部注释块），并更新 SHA-256。
# ═══════════════════════════════════════════════════════════════════════════
"""Optional memory snapshots without resetting shared allocator statistics."""

import logging
import os

import psutil
import torch


def log_memory(label, device):
    if os.environ.get("SELFLIFT_MEMORY_LOG", "0") != "1":
        return
    device = torch.device(device)
    fields = []
    try:
        fields.append(f"process_rss={psutil.Process().memory_info().rss / 2**20:.2f} MiB")
        fields.append(f"system_available={psutil.virtual_memory().available / 2**20:.2f} MiB")
    except (psutil.Error, OSError) as error:
        fields.append(f"host_memory_unavailable={error}")
    if device.type == "cuda" and torch.cuda.is_initialized():
        try:
            free, total = torch.cuda.mem_get_info(device)
            fields.extend([
                f"allocated={torch.cuda.memory_allocated(device) / 2**20:.2f} MiB",
                f"reserved={torch.cuda.memory_reserved(device) / 2**20:.2f} MiB",
                f"process_peak_allocated={torch.cuda.max_memory_allocated(device) / 2**20:.2f} MiB",
                f"device_used={((total - free) / 2**20):.2f} MiB",
                f"device_free={free / 2**20:.2f} MiB",
            ])
        except RuntimeError as error:
            fields.append(f"cuda_memory_unavailable={error}")
    logging.info("[SelfLift memory] %s device=%s; %s", label, device, "; ".join(fields))
