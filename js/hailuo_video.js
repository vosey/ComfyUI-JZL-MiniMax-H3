/**
 * JZL 海螺H3视频参数 — UI 扩展
 * ==============================
 * frames_display 实时显示「分辨率 × 分辨率 | 估算帧数」，
 * 复刻官方 ResolutionSelector 分辨率公式（MP × 1024² → sqrt → round/multiple），
 * 帧数按 MiniMax H3 固定 24fps 吸附 17k+5 网格推算。
 */

import { app } from "../../scripts/app.js";

const NODE_TYPES = new Set(["JZL_HailuoH3VideoParams", "JZL_HailuoH3VideoParamsPro"]);

const isZH = navigator.language.startsWith("zh");

const RATIO_MAP = {
    "1:1 (Square)": [1, 1],
    "2:3 (Portrait Photo)": [2, 3],
    "3:2 (Photo)": [3, 2],
    "3:4 (Portrait Standard)": [3, 4],
    "4:5 (Portrait Tall)": [4, 5],
    "4:3 (Standard)": [4, 3],
    "5:4 (Landscape Tall)": [5, 4],
    "9:16 (Portrait Widescreen)": [9, 16],
    "16:9 (Widescreen)": [16, 9],
    "21:9 (Ultrawide)": [21, 9],
};

app.registerExtension({
    name: "JZL.MiniMax.HailuoVideo",

    init() {
        setInterval(() => {
            if (!app.graph || !app.graph._nodes) return;

            for (const node of app.graph._nodes) {
                if (!NODE_TYPES.has(node.type) || !node.widgets) continue;

                const wDisp = node.widgets.find(w => w.name === "frames_display");
                const wDur = node.widgets.find(w => w.name === "duration");
                const wRatio = node.widgets.find(w => w.name === "aspect_ratio");
                const wMP = node.widgets.find(w => w.name === "megapixels");
                const wMul = node.widgets.find(w => w.name === "multiple");
                if (!wDisp || !wDur) continue;

                // 显示窗样式：只读 + 绿色等宽
                // Nodes 2.0：只读要用 widget.options.read_only；Vue 部件没有 element 可改样式
                try { if (wDisp.options) wDisp.options.read_only = true; } catch (_) {}
                const el = wDisp.inputEl || wDisp.element;
                if (el && el.style && el.style.backgroundColor !== "rgb(34, 34, 34)") {
                    el.readOnly = true;
                    el.style.backgroundColor = "#222222";
                    el.style.color = "#00FF00";
                    el.style.textAlign = "center";
                    el.style.fontWeight = "bold";
                }

                // ── 分辨率：官方 ResolutionSelector 公式 ──
                const [wr, hr] = (wRatio && RATIO_MAP[wRatio.value]) || [16, 9];
                const mp = parseFloat(wMP?.value) || 1.0;
                const mul = parseInt(wMul?.value, 10) || 32;
                const totalPx = mp * 1024 * 1024;
                const sc = Math.sqrt(totalPx / (wr * hr));
                const calcW = Math.round((wr * sc) / mul) * mul;
                const calcH = Math.round((hr * sc) / mul) * mul;

                // ── 帧数：时长(秒) × 24fps，吸附 17k+5 网格 ──
                const dur = Math.max(4, Math.min(15, Math.round(Number(wDur.value)) || 8));
                const base = Math.max(5, Math.round(dur * 24));
                const frames = base + (((5 - (base % 17)) + 17) % 17);

                const resText = `${calcW} × ${calcH}`;
                const framesText = isZH ? `估算帧数: ${frames}` : `Frames: ${frames}`;
                const disp = `${resText}  |  ${framesText}`;

                if (wDisp.value !== disp) {
                    wDisp.value = disp;
                    if (wDisp.inputEl) wDisp.inputEl.value = disp;
                    if (wDisp.element) wDisp.element.value = disp;
                }
            }
        }, 250);
    },
});
