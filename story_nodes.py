"""JZL MiniMax 一键漫剧创作 — 节点定义（V1 经典 API）

总线信号链: 剧本编剧 → 分段词生成器 → 分段处理中心
调度分支: 分段处理中心 → 场景元素调度 / 视频调度 / 音频调度

本文件包含 4 个纯逻辑节点（不依赖 llama-cpp）：
  1. JZL_MiniMax_ShotFormatter    分段处理中心
  2. JZL_MiniMax_SceneDispatcher  场景元素调度
  3. JZL_MiniMax_VideoDispatcher  视频调度
  4. JZL_MiniMax_AudioDispatcher  音频调度

输出目录: {ComfyUI output}/jzl/{story_name}/{子目录}/
"""

import os
import re
import json

import torch


# ═══════════════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════════════

class _FlexibleInputType(dict):
    """任意数量的指定类型输入槽（配合 JS 动态端口）"""
    def __init__(self, type_):
        self.type_ = type_

    def __getitem__(self, key):
        return (self.type_,)

    def __contains__(self, key):
        return True


def _get_output_dir(story_name="", subfolder=""):
    try:
        import folder_paths
        base = folder_paths.get_output_directory()
    except ImportError:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "output")
    safe_name = re.sub(r'[<>:"/\\|?*\s]', '_', (story_name or "untitled").strip())
    out_dir = os.path.join(base, "jzl", safe_name, subfolder)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def _find_latest_version(base_dir):
    """找到最新版本文件夹(第NNN次分段词), 返回路径和下一个编号"""
    if not os.path.isdir(base_dir):
        return os.path.join(base_dir, "第001次分段词"), 1
    pat = re.compile(r'第(\d{3})次分段词')
    versions = []
    for f in os.listdir(base_dir):
        m = pat.match(f)
        if m and os.path.isdir(os.path.join(base_dir, f)):
            versions.append((int(m.group(1)), f))
    if versions:
        versions.sort(reverse=True)
        return os.path.join(base_dir, versions[0][1]), versions[0][0] + 1
    return os.path.join(base_dir, "第001次分段词"), 1


def _parse_four_in_one(content):
    """解析四段格式, 返回 (h3_prompt, scene_info, video_info, audio_info)"""
    h3, scene, video, audio = "", "{}", "{}", "{}"
    for section in re.split(r'\n(?====)', content):
        section = section.strip()
        if section.startswith("===H3_PROMPT==="):
            h3 = section[len("===H3_PROMPT===\n"):].strip()
        elif section.startswith("===SCENE_INSTRUCTION==="):
            scene = section[len("===SCENE_INSTRUCTION===\n"):].strip()
        elif section.startswith("===VIDEO_INSTRUCTION==="):
            video = section[len("===VIDEO_INSTRUCTION===\n"):].strip()
        elif section.startswith("===AUDIO_INSTRUCTION==="):
            audio = section[len("===AUDIO_INSTRUCTION===\n"):].strip()
    return h3, scene, video, audio


# 资产名里的通用词（图片2 / 角色 / 场景…）：两边同时出现是常态，不能当作「同一个素材」的依据。
# 否则「图片3 角色 土拨鼠」会错配到池里任意一条「图片N 角色 XXX」，用户拿到无关参考图。
_GENERIC_TOKENS = {"图片", "视频", "音频", "角色", "场景", "道具", "音色", "主体", "其他", "分镜", "资产"}


def _match_name(slot_name, node_name):
    """模糊匹配：slot 素材名与上游节点名互相包含，或分词后有交集（交集须含至少一个非通用词）。"""
    s = (slot_name or "").strip().lower()
    n = (node_name or "").strip().lower()
    if not s or not n:
        return False
    if s in n or n in s:
        return True
    s_tokens = {t for t in re.split(r'[-\s_（(）):：,，、/]+', s) if t}
    n_tokens = {t for t in re.split(r'[-\s_（(）):：,，、/]+', n) if t}
    common = s_tokens & n_tokens
    return any(t not in _GENERIC_TOKENS for t in common)


def _parse_slots(raw):
    """解析调度指令为 slots 数组。

    兼容三种形态（最多递归 3 层）：
    - 字符串 JSON：'{"shot":1,"slots":[...]}'
    - list：分段处理中心输出的 ['{"shot":1,...}', ...] → 取第一项
    - dict：已解析的 {"shot":1,"slots":[...]}
    解析失败返回 []。
    """
    for _ in range(3):
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                return []
        elif isinstance(raw, (list, tuple)):
            if not raw:
                return []
            raw = raw[0]
        elif isinstance(raw, dict):
            return raw.get("slots", [])
        else:
            return []
    return []


def _is_empty_audio(value):
    """判断音频是否为无效空音频（无波形或无采样点），空音频视为未接。"""
    if not isinstance(value, dict):
        return False
    waveform = value.get("waveform")
    if waveform is None or not isinstance(waveform, torch.Tensor):
        return True
    return waveform.numel() == 0 or waveform.shape[-1] == 0


_TYPE_PREFIX = {
    "场景": "场景", "角色": "角色", "道具": "道具", "视频": "视频", "音频": "音频",
    "scene": "场景", "character": "角色", "prop": "道具", "video": "视频", "audio": "音频",
}


def normalize_slots(info_json):
    """规范化调度指令 slots，修复 LLM 输出的小错误（不可解析的输入原样返回）：

    - 「类型:字母」（如「道具:C」）→「类型:类型+字母」（「道具:道具C」）
    - 尾冒号/尾空格自动去除（如「音频:D:」→「音频:音频D」）
    """
    try:
        d = json.loads(info_json) if isinstance(info_json, str) else (info_json or {})
    except Exception:
        return info_json
    if not isinstance(d, dict):
        return info_json
    slots = d.get("slots") or []
    if not isinstance(slots, list):
        return info_json
    changed = False
    normalized = []
    for slot in slots:
        if not isinstance(slot, str) or ":" not in slot:
            normalized.append(slot)
            continue
        typ, name = slot.split(":", 1)
        typ = typ.strip()
        name = name.strip().rstrip(":：")
        prefix = _TYPE_PREFIX.get(typ.lower() if typ.isascii() else typ)
        if prefix and re.fullmatch(r'[A-H]', name, re.IGNORECASE):
            normalized.append(f"{typ}:{prefix}{name}")
            changed = True
            continue
        fixed = f"{typ}:{name}"
        if slot != fixed:
            normalized.append(fixed)
            changed = True
            continue
        normalized.append(slot)
    if changed:
        d["slots"] = normalized
        return json.dumps(d, ensure_ascii=False)
    return info_json


def _get_from_pool(name, kind=None):
    """从全局资产池按名取 tensor（无线传输）。kind 可选过滤 image/audio/video。"""
    try:
        from .nodes_asset_manager import JZL_ASSET_POOL
    except Exception:
        return None
    if not JZL_ASSET_POOL:
        return None
    # 精确匹配
    if name in JZL_ASSET_POOL:
        item = JZL_ASSET_POOL[name]
        if kind is None or item.get("kind") == kind:
            return item.get("data")
    # 模糊匹配（资产名 vs slot 名互相包含）
    for key, item in JZL_ASSET_POOL.items():
        if kind is not None and item.get("kind") != kind:
            continue
        if _match_name(name, key):
            return item.get("data")
    return None


# ═══════════════════════════════════════════════════════════════
#  节点 1: 分段处理中心
# ═══════════════════════════════════════════════════════════════

class JZL_MiniMax_ShotFormatter:
    """本地文件为主数据通道, 重拍模式直接读选中文件"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "reshoot_mode": ("BOOLEAN", {"default": False, "label_on": "重拍", "label_off": "正常"}),
            },
            "optional": {
                "shot_text": ("*", {"force_input": True}),
                "_reshoot_path": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("H3提示词", "场景调度指令", "视频调度", "音频调度")
    OUTPUT_IS_LIST = (True, True, True, True)
    FUNCTION = "execute"
    CATEGORY = "JZL/MiniMax"

    @staticmethod
    def _parse_shots(text):
        return [{"raw": b.strip()} for b in re.findall(r'\[SHOT_START\](.*?)\[SHOT_END\]', text or "", re.DOTALL)]

    @staticmethod
    def _rebuild_scene(block, shot_num):
        """LLM 未输出 SCENE_INSTRUCTION 时的兜底。

        分段信息里的「**场景**/**角色**/**道具**」是描述/素材名，不是槽位名
        （槽位名是 场景A~H/角色A~H/道具A~H），无法可靠反推映射。
        故留空 slots，由调度节点输出空、用户手动补线，避免用错误槽位名导致错配。
        """
        return json.dumps({"slots": []}, ensure_ascii=False)

    def execute(self, reshoot_mode, shot_text=None, _reshoot_path=None):
        # ── 重拍: 只读选中的本地文件 ──
        if reshoot_mode and _reshoot_path and os.path.isfile(_reshoot_path):
            content = open(_reshoot_path, "r", encoding="utf-8").read()
            h, s, vid, aud = _parse_four_in_one(content)
            h3_list = [h or "[未找到H3提示词]"]
            scene_list = [s or "{}"]
            video_list = [vid or "{}"]
            audio_list = [aud or "{}"]
            return {"ui": {"text": h3_list}, "result": (h3_list, scene_list, video_list, audio_list)}

        # ── 正常模式: 从剧本输出（shot_text）解析 [SHOT_START] 块 + 提取四段 ──
        shots = self._parse_shots(shot_text)
        if not shots:
            return {"ui": {"text": [""]}, "result": ([""], ["{}"], ["{}"], ["{}"])}

        h3_list, scene_list, video_list, audio_list = [], [], [], []
        for i, shot in enumerate(shots):
            shot_num = i + 1
            h3, scene, vid, aud = _parse_four_in_one(shot["raw"])
            if not h3:
                h3 = "[未找到H3提示词]"
            if scene in ("", "{}"):
                scene = self._rebuild_scene(shot["raw"], shot_num)
            if vid in ("", "{}"):
                vid = json.dumps({"slots": []}, ensure_ascii=False)
            if aud in ("", "{}"):
                aud = json.dumps({"slots": []}, ensure_ascii=False)
            # 清洗槽位名小错误（缺类型前缀「道具:C」→「道具:道具C」、尾冒号）
            scene = normalize_slots(scene)
            vid = normalize_slots(vid)
            aud = normalize_slots(aud)
            h3_list.append(h3)
            scene_list.append(scene)
            video_list.append(vid)
            audio_list.append(aud)

        return {"ui": {"text": h3_list}, "result": (h3_list, scene_list, video_list, audio_list)}


# ═══════════════════════════════════════════════════════════════
#  节点 2: 场景元素调度（按上游节点名自动分类）
# ═══════════════════════════════════════════════════════════════

class JZL_MiniMax_SceneDispatcher:
    """动态 IMAGE 输入，根据上游节点名称自动分类 角色/背景/道具，分配到 9 个 ref_image 槽位。"""

    _KW_CHARACTER = ["角色", "人物", "主角", "反派", "配角"]
    _KW_BACKGROUND = ["背景", "场景", "环境", "bg"]
    _KW_PROP = ["道具", "物品", "武器", "prop"]

    @staticmethod
    def _classify(name):
        try:
            from .sheding.dispatcher_rules import KW_CHARACTER, KW_BACKGROUND, KW_PROP
        except ImportError:
            KW_CHARACTER = JZL_MiniMax_SceneDispatcher._KW_CHARACTER
            KW_BACKGROUND = JZL_MiniMax_SceneDispatcher._KW_BACKGROUND
            KW_PROP = JZL_MiniMax_SceneDispatcher._KW_PROP
        n = name.lower()
        for kw in KW_CHARACTER:
            if kw.lower() in n:
                return "character"
        for kw in KW_BACKGROUND:
            if kw.lower() in n:
                return "background"
        for kw in KW_PROP:
            if kw.lower() in n:
                return "prop"
        return "character"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"scene_instruction": ("*", {"force_input": True})}, "optional": _FlexibleInputType("IMAGE")}

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE")
    RETURN_NAMES = ("ref_image_0", "ref_image_1", "ref_image_2", "ref_image_3", "ref_image_4", "ref_image_5", "ref_image_6", "ref_image_7", "ref_image_8")
    FUNCTION = "execute"
    CATEGORY = "JZL/MiniMax"

    def execute(self, scene_instruction, **kwargs):
        # 解析 slots 有序槽位数组（兼容 str JSON / list / dict）
        slots = _parse_slots(scene_instruction)

        # 收集所有 IMAGE 输入（key = 上游节点名）
        images = {}
        seen = {}
        for name, tensor in kwargs.items():
            if tensor is None or not isinstance(tensor, torch.Tensor):
                continue
            seen[name] = seen.get(name, -1) + 1
            uname = f"{name}_{seen[name]}" if seen[name] else name
            images[uname] = tensor

        used = set()
        out = [None] * 9

        # 严格按 slots 顺序匹配（slot[i] → out[i]），匹配不到留空（None = 没接，不编码不采样）
        for i, slot in enumerate(slots):
            if i >= 9:
                break
            if isinstance(slot, str) and ":" in slot:
                _, name = slot.split(":", 1)
                name = name.strip()
            else:
                name = str(slot).strip()
            for uname, tensor in images.items():
                if uname in used:
                    continue
                if _match_name(name, uname):
                    out[i] = tensor
                    used.add(uname)
                    break

        # 无调度指令（slots 为空）时保持 None（不兜底全收）
        return tuple(out)


# ═══════════════════════════════════════════════════════════════
#  节点 3: 视频调度 (动态端口 + 配对音频)
# ═══════════════════════════════════════════════════════════════

class JZL_MiniMax_VideoDispatcher:
    """动态视频端口（IMAGE），接入视频后自动配对一个「上游名（音频）」音频端口。
    交叉输出 3 组 ref_video / ref_video_audio。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"va_instruction": ("*", {"force_input": True})}, "optional": _FlexibleInputType("IMAGE")}

    RETURN_TYPES = ("IMAGE", "*", "IMAGE", "*", "IMAGE", "*")
    RETURN_NAMES = ("ref_video_0", "ref_video_audio_0", "ref_video_1", "ref_video_audio_1", "ref_video_2", "ref_video_audio_2")
    FUNCTION = "execute"
    CATEGORY = "JZL/MiniMax"

    def execute(self, va_instruction, **kwargs):
        # 解析 slots 有序槽位数组（兼容 str JSON / list / dict）
        slots = _parse_slots(va_instruction)

        videos, video_audios = {}, {}
        seen = {}
        for name, value in kwargs.items():
            if value is None:
                continue
            seen[name] = seen.get(name, -1) + 1
            uname = f"{name}_{seen[name]}" if seen[name] else name
            if "（音频）" in name:
                if _is_empty_audio(value):
                    continue
                video_audios[uname] = value
            elif isinstance(value, torch.Tensor):
                videos[uname] = value

        vid_slots = [None] * 3
        va_slots = [None] * 3
        used = set()

        # 严格按 slots 顺序匹配视频（slot[i] → vid_slots[i]），匹配不到留空（None）
        for i, slot in enumerate(slots):
            if i >= 3:
                break
            if isinstance(slot, str) and ":" in slot:
                _, name = slot.split(":", 1)
                name = name.strip()
            else:
                name = str(slot).strip()
            for uname, tensor in videos.items():
                if uname in used:
                    continue
                if _match_name(name, uname):
                    vid_slots[i] = tensor
                    used.add(uname)
                    break

        # 配对音频：仅在有调度指令（slots 非空）时按收集顺序放，否则保持 None
        if slots:
            vai = 0
            for name in video_audios:
                if vai >= 3:
                    break
                va_slots[vai] = video_audios[name]
                vai += 1

        return (vid_slots[0], va_slots[0], vid_slots[1], va_slots[1], vid_slots[2], va_slots[2])


# ═══════════════════════════════════════════════════════════════
#  节点 4: 音频调度 (动态)
# ═══════════════════════════════════════════════════════════════

class JZL_MiniMax_AudioDispatcher:
    """动态音频接入, 仅接受 AUDIO 类型, 最多 3 条 ref_audio"""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"va_instruction": ("*", {"force_input": True})}, "optional": _FlexibleInputType("AUDIO")}

    RETURN_TYPES = ("*", "*", "*")
    RETURN_NAMES = ("ref_audio_0", "ref_audio_1", "ref_audio_2")
    FUNCTION = "execute"
    CATEGORY = "JZL/MiniMax"

    def execute(self, va_instruction, **kwargs):
        # 解析 slots 有序槽位数组（兼容 str JSON / list / dict）
        slots = _parse_slots(va_instruction)

        audios = {}
        seen = {}
        for name, value in kwargs.items():
            if value is None or _is_empty_audio(value):
                continue
            seen[name] = seen.get(name, -1) + 1
            audios[f"{name}_{seen[name]}" if seen[name] else name] = value

        out = [None] * 3
        used = set()

        # 严格按 slots 顺序匹配音频（slot[i] → out[i]）
        for i, slot in enumerate(slots):
            if i >= 3:
                break
            if isinstance(slot, str) and ":" in slot:
                _, name = slot.split(":", 1)
                name = name.strip()
            else:
                name = str(slot).strip()
            for uname, value in audios.items():
                if uname in used:
                    continue
                if _match_name(name, uname):
                    out[i] = value
                    used.add(uname)
                    break

        # 无调度指令（slots 为空）时保持 None（不兜底全收）
        return tuple(out)


# ═══════════════════════════════════════════════════════════════
#  节点 5: 场景元素调度2（固定接口：8角色+8场景+8道具，A~H）
# ═══════════════════════════════════════════════════════════════

class JZL_MiniMax_SceneDispatcher2:
    """固定接口场景调度：角色A~H / 场景A~H / 道具A~H 共 24 个固定 IMAGE 输入。

    不识别上游节点名，按固定接口名匹配：slots 里写「角色A」就取「角色A」接口的图。
    """

    @classmethod
    def INPUT_TYPES(cls):
        optional = {}
        for prefix in ("角色", "场景", "道具"):
            for ch in "ABCDEFGH":
                optional[f"{prefix}{ch}"] = ("IMAGE",)
        return {
            "required": {"scene_instruction": ("*", {"force_input": True})},
            "optional": optional,
        }

    RETURN_TYPES = ("IMAGE",) * 9
    RETURN_NAMES = tuple(f"ref_image_{i}" for i in range(9))
    FUNCTION = "execute"
    CATEGORY = "JZL/MiniMax"

    def execute(self, scene_instruction, **kwargs):
        slots = _parse_slots(scene_instruction)
        out = [None] * 9
        used = set()
        for i, slot in enumerate(slots):
            if i >= 9:
                break
            name = slot.split(":", 1)[-1].strip() if isinstance(slot, str) and ":" in slot else str(slot).strip()
            # 优先从全局资产池取（无线传输）
            tensor = _get_from_pool(name, kind="image")
            if tensor is not None:
                out[i] = tensor
                continue
            # 回退：固定接口 kwargs（旧工作流兼容）
            for key, tensor in kwargs.items():
                if key in used or tensor is None or not isinstance(tensor, torch.Tensor):
                    continue
                if key == name or _match_name(name, key):
                    out[i] = tensor
                    used.add(key)
                    break
        return tuple(out)


# ═══════════════════════════════════════════════════════════════
#  节点 6: 音频调度2（固定接口：音频A~H）
# ═══════════════════════════════════════════════════════════════

class JZL_MiniMax_AudioDispatcher2:
    """固定接口音频调度：音频A~H 共 8 个固定 AUDIO 输入。

    不识别上游节点名，按固定接口名匹配：slots 里写「音频A」就取「音频A」接口的音频。
    """

    @classmethod
    def INPUT_TYPES(cls):
        optional = {f"音频{ch}": ("AUDIO",) for ch in "ABCDEFGH"}
        return {
            "required": {"va_instruction": ("*", {"force_input": True})},
            "optional": optional,
        }

    RETURN_TYPES = ("*", "*", "*")
    RETURN_NAMES = ("ref_audio_0", "ref_audio_1", "ref_audio_2")
    FUNCTION = "execute"
    CATEGORY = "JZL/MiniMax"

    def execute(self, va_instruction, **kwargs):
        slots = _parse_slots(va_instruction)
        out = [None] * 3
        used = set()
        for i, slot in enumerate(slots):
            if i >= 3:
                break
            name = slot.split(":", 1)[-1].strip() if isinstance(slot, str) and ":" in slot else str(slot).strip()
            # 优先从全局资产池取（无线传输）
            value = _get_from_pool(name, kind="audio")
            if value is not None:
                out[i] = value
                continue
            # 回退：固定接口 kwargs（旧工作流兼容）
            for key, value in kwargs.items():
                if key in used or value is None or _is_empty_audio(value):
                    continue
                if key == name or _match_name(name, key):
                    out[i] = value
                    used.add(key)
                    break
        return tuple(out)


# ═══════════════════════════════════════════════════════════════
#  节点 7: 视频调度2（固定接口：8 组视频+音轨，A~H）
# ═══════════════════════════════════════════════════════════════

class JZL_MiniMax_VideoDispatcher2:
    """固定接口视频调度：视频A~H + 视频A~H（音频）共 16 个固定输入。

    不识别上游节点名，按固定接口名匹配：slots 里写「视频A」就取「视频A」接口的视频，
    并自动配对同名的「视频A（音频）」音轨。
    """

    @classmethod
    def INPUT_TYPES(cls):
        optional = {}
        for ch in "ABCDEFGH":
            optional[f"视频{ch}"] = ("IMAGE",)
            optional[f"视频{ch}（音频）"] = ("AUDIO",)
        return {
            "required": {"va_instruction": ("*", {"force_input": True})},
            "optional": optional,
        }

    RETURN_TYPES = ("IMAGE", "*", "IMAGE", "*", "IMAGE", "*")
    RETURN_NAMES = ("ref_video_0", "ref_video_audio_0", "ref_video_1", "ref_video_audio_1", "ref_video_2", "ref_video_audio_2")
    FUNCTION = "execute"
    CATEGORY = "JZL/MiniMax"

    def execute(self, va_instruction, **kwargs):
        slots = _parse_slots(va_instruction)
        vid_slots = [None] * 3
        va_slots = [None] * 3
        used = set()
        for i, slot in enumerate(slots):
            if i >= 3:
                break
            name = slot.split(":", 1)[-1].strip() if isinstance(slot, str) and ":" in slot else str(slot).strip()
            # 优先从全局资产池取视频（IMAGE 序列，无线传输）
            value = _get_from_pool(name, kind="video")
            if value is not None:
                vid_slots[i] = value
                continue
            # 回退：固定接口 kwargs（旧工作流兼容，含同名音轨配对）
            for key, value in kwargs.items():
                if key in used or value is None or "（音频）" in key:
                    continue
                if isinstance(value, torch.Tensor) and (key == name or _match_name(name, key)):
                    vid_slots[i] = value
                    used.add(key)
                    audio_key = key + "（音频）"
                    audio_val = kwargs.get(audio_key)
                    if audio_val is not None and not _is_empty_audio(audio_val):
                        va_slots[i] = audio_val
                    break
        return (vid_slots[0], va_slots[0], vid_slots[1], va_slots[1], vid_slots[2], va_slots[2])
