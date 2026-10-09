"""JZL MiniMax Music3 — 歌词编辑节点（V1 经典 API）

纯文本编辑 + 官方段落标签快捷插入。插入逻辑在 js/music_lyrics_editor.js。
输出 STRING，可直接接到官方「MiniMax Music3 Text Encode」的 lyrics 输入。

标签分三组：
  ① 官方段落标签（README 明列的 9 个）
  ② 编号 / 终段变体
  ③ 人声角色（对唱 / 合唱，社区惯例，官方未文档化）
"""


class JZL_MiniMaxMusicLyricsEditor:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "lyrics_text": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": (
                        "歌词文本。点击上方「添加元素」插入标签："
                        "官方段落标签 [Intro]/[Verse]/[Pre-Chorus]/[Chorus]/[Post-Chorus]/[Bridge]/[Instrumental]/[Solo]/[Outro]，"
                        "以及对唱/合唱人声角色标签（如 [Chorus: Duet]、[Singer A]，社区惯例）。"
                        "⚠️ 仅 [方括号] 会被识别为标签，圆括号 (Singer A): 会被当成歌词唱出来"
                    ),
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("lyrics",)
    FUNCTION = "build"
    CATEGORY = "JZL/MiniMax"

    def build(self, lyrics_text):
        return (lyrics_text,)
