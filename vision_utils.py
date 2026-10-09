"""JZL MiniMax-H3 — 识图（vision）工具：参考素材同名图片 → LLM 多模态消息。

设计：本模块**独立无依赖**（只 import os/PIL/base64/folder_paths），供 nodes_asset_manager 与
nodes_llama 共同使用，避免两者相互 import 产生循环依赖。

用途：
- 「开启拆解识图」/「开启扩写识图」时，把「参考素材管理」里**已启用**且**素材名与故事正文同名**的
  图片（角色/场景/道具）连同故事一起交给 LLM（本地 llama-cpp / llama-server 需 mmproj + chat_handler；
  在线 API 需选择视觉模型，如 deepseek-v4-flash-vision-exp），让拆解/扩写内容贴合参考图外观。
- 无同名图片 → 自动跳过（返回空列表），不影响原有纯文本流程。
"""

import base64
import io as _io
import os
import re

# 送 LLM 的图片最长边（控制 token 与请求体积；XB 的在线 API 用 1568，本地 1024 已足够描述外观）
VISION_MAX_SIDE = 1024
# 单次最多送图数量（超出按 角色 → 场景 → 道具 顺序截断）
VISION_MAX_IMAGES = 6
# 参与识图的素材类型（与「参考素材管理」的类型下拉一致）
VISION_TYPES = ("角色", "场景", "道具")


def resolve_image_path(path):
    """素材路径 → 绝对路径（兼容绝对路径 / LoadImage 式相对路径 / 旧 jzl_assets）。"""
    p = str(path or "").strip()
    if not p:
        return ""
    if os.path.isfile(p):
        return p
    try:
        import folder_paths
        in_dir = folder_paths.get_input_directory()
        out_dir = folder_paths.get_output_directory()
        for c in (os.path.join(in_dir, p), os.path.join(out_dir, p),
                  os.path.join(in_dir, "jzl", p), os.path.join(in_dir, "jzl_assets", p)):
            if os.path.isfile(c):
                return c
    except Exception:
        pass
    return ""


def image_to_data_uri(path, max_side=VISION_MAX_SIDE):
    """图片文件 → JPEG base64 data URI（最长边缩放到 max_side）。失败返回 ""。"""
    p = str(path or "")
    if not p or not os.path.isfile(p):
        return ""
    from PIL import Image
    with Image.open(p) as im:
        im = im.convert("RGB")
        w, h = im.size
        _m = max(w, h)
        if _m > max_side:
            _r = max_side / float(_m)
            im = im.resize((max(1, int(w * _r)), max(1, int(h * _r))), Image.LANCZOS)
        buf = _io.BytesIO()
        im.save(buf, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")


def vision_local_ready(llm_backend, llm_cfg, tag="识图"):
    """本地 LLM 是否具备识图能力（需 mmproj + chat_handler）；未配置 → 警告并返回 False（调用方跳过图片）。

    API 后端：不检查（由用户在 API 配置里选择视觉模型，如 deepseek-v4-flash-vision-exp）。
    """
    if "api" in str(llm_backend or ""):
        return True
    c = llm_cfg or {}
    mm = str(c.get("mmproj") or "None").strip()
    ch = str(c.get("chat_handler") or "None").strip()
    if mm in ("", "None") or ch in ("", "None"):
        print(f"[JZL-{tag}] ⚠️ 已开启识图，但本地 LLM 未配置「视觉模块 mmproj」或「Chat Handler」→ "
              f"本次跳过识图、按纯文本继续（可在「大语言模型配置」里补选这两项）")
        return False
    return True


def collect_vision_images(assets_cfg, story_text, tag="识图"):
    """按素材名与故事正文**同名**匹配「参考素材管理」中已启用的图片
    → [(类型, 素材名, 素材详细描述, data_uri)]。

    只取 角色/场景/道具 三类（用户明确：参考图分角色/道具/场景）；无同名图片自动跳过。
    图片统一转 JPEG base64（最长边 1024）；最多 VISION_MAX_IMAGES 张。
    """
    text = str(story_text or "")
    if not text.strip():
        return []
    cands = []
    seen = set()
    for it in ((assets_cfg or {}).get("images") or []):
        if not isinstance(it, dict) or not it.get("enabled", True):
            continue
        typ = str(it.get("type") or "").strip()
        name = str(it.get("name") or "").strip()
        if typ not in VISION_TYPES or not name or name in seen:
            continue
        if name not in text:          # 同名匹配：素材名在故事正文里出现
            continue
        seen.add(name)
        cands.append((VISION_TYPES.index(typ), typ, name, it))
    if not cands:
        return []
    cands.sort(key=lambda x: x[0])
    picked = []
    for _o, typ, name, it in cands:
        if len(picked) >= VISION_MAX_IMAGES:
            print(f"[JZL-{tag}] 同名参考图超过 {VISION_MAX_IMAGES} 张 → 已按 角色→场景→道具 顺序截断")
            break
        try:
            uri = image_to_data_uri(resolve_image_path(it.get("path")))
        except Exception as e:
            print(f"[JZL-{tag}] 参考图「{name}」读取失败，已跳过：{e}")
            continue
        if uri:
            picked.append((typ, name, str(it.get("description") or "").strip(), uri))
        else:
            print(f"[JZL-{tag}] 参考图「{name}」文件缺失（{it.get('path')}），已跳过")
    if picked:
        print(f"[JZL-{tag}] 命中 {len(picked)} 张同名参考图："
              + "、".join(f"{t}:{n}{'（带描述）' if d else '（无描述，仅图）'}" for t, n, d, _u in picked))
    return picked


def vision_note(images):
    """外观**权威设定**（识图强约束）：每张图对应哪个素材 + 素材的详细描述 + 严格执行规则。

    用户需求（2026-09-26）：识图时**优先读取参考图的详细描述**；描述与图不符 → 以图为准校准；
    描述与图一致 → **就照描述写，不需要自由发挥**（禁止把「淡蓝色牛仔连衣裤」改写成「天蓝色背带裤」）。
    """
    if not images:
        return ""
    lines = []
    for i, (typ, name, desc, _u) in enumerate(images):
        lines.append(f"- 第 {i + 1} 张参考图 = {typ}「{name}」")
        if desc:
            lines.append(f"  权威外观描述（用户填写的设定，必须逐字沿用）：{desc}")
        else:
            lines.append("  权威外观描述：未填写 → 请直接以图中的实际外观为准"
                         "（发型与发饰/服装款式与配色/材质与纹样/体型气质/道具造型/场景环境与光线）")
    return ("\n\n【参考素材外观设定（最高优先级，识图模式必须严格执行）】\n" + "\n".join(lines) + "\n"
            "执行规则（逐条遵守）：\n"
            "1) 上述「权威外观描述」是外观的唯一准确来源：服装/道具名称、配色、材质、造型等术语必须**原样沿用**，"
            "严禁同义改写或自由发挥（例：描述写「淡蓝色牛仔连衣裤」→ 不得写成「天蓝色背带裤」；"
            "写「米色围脖」→ 不得写成「米色围巾」）。\n"
            "2) 若故事正文里的外观用词与上述描述/参考图**不一致**，一律以「参考图 + 权威外观描述」为准，并在本次扩写中纠正过来。\n"
            "3) 若参考图与文字描述**明显冲突**（颜色/款式/结构不同），**以图片为准**，按图中实际外观书写，用词仍要具体准确。\n"
            "4) 图片只用于校准外观：**不要新增加**图中和描述里都没有的配饰、图案、道具；场景照同理（环境/光线/陈设按参考图与描述）。\n"
            "5) 看图不得改变剧情、人物关系与对白内容（延续原故事）。")


def vision_user_content(user_msg, images):
    """构造多模态 user content（OpenAI 兼容）：文字 + 每张图（附「类型:素材名」标注）。"""
    parts = [{"type": "text", "text": str(user_msg or "")}]
    for typ, name, _desc, uri in (images or []):
        parts.append({"type": "image_url", "image_url": {"url": uri}})
        parts.append({"type": "text", "text": f"（上图 = {typ}「{name}」）"})
    return parts


def flatten_user_content(content):
    """多模态 content → 纯文本（供不支持识图的供应商降级使用）。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content
                       if isinstance(p, dict) and p.get("type") == "text")
    return str(content or "")


def has_images(content):
    """判断 content 是否含图片（多模态）。"""
    if isinstance(content, list):
        return any(isinstance(p, dict) and p.get("type") == "image_url" for p in content)
    return False
