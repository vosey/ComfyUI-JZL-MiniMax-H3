/**
 * JZL MiniMax 预设 ↔ 海螺H3视频参数 — 时长 + 画幅比例双向联动
 * ============================================================
 * 视频时长（视频时长 ↔ duration）与 画面比例（画面比例 ↔ aspect_ratio）
 * 在 MiniMax-fl2va / MiniMax-ref2va 预设 与 海螺H3视频参数(Pro) 之间双向同步：
 *   改任一方，另一方即时跟着变（widget callback 触发，无轮询延迟）。
 * 全局防抖标志防止双向回环。
 */

import { app } from "../../scripts/app.js";

const MINIMAX_TYPE = "JZL_MiniMaxPreset";
const REF2VA_TYPE = "JZL_MiniMaxRef2vaPreset";
const HAILUO_TYPES = new Set(["JZL_HailuoH3VideoParams", "JZL_HailuoH3VideoParamsPro"]);

// 预设（短格式）↔ 海螺（长格式）
const RATIO_MAP = {
    "16:9": "16:9 (Widescreen)",
    "9:16": "9:16 (Portrait Widescreen)",
    "4:3": "4:3 (Standard)",
    "3:4": "3:4 (Portrait Standard)",
    "1:1": "1:1 (Square)",
    "21:9": "21:9 (Ultrawide)",
    "4:5": "4:5 (Portrait Tall)",
    "5:4": "5:4 (Landscape Tall)",
};
const RATIO_REV = {};
for (const [k, v] of Object.entries(RATIO_MAP)) RATIO_REV[v] = k;

function dispatch(w, val) {
    if (!w) return;
    const el = w.element || w.inputEl;
    if (!el) {
        // Nodes 2.0：combo/number 是 Vue 组件，没有 element 可直接派发 → 写 value + 走 callback
        if (w.value !== val) w.value = val;
        try { w.callback?.(val); } catch (_) {}
        return;
    }
    el.value = val;
    // 只触发原生事件让 ComfyUI 统一更新 value 和 callback；不手动调 callback，避免双重触发/回环
    const evt = el.tagName === "SELECT" ? "change" : "input";
    el.dispatchEvent(new Event(evt, { bubbles: true }));
}

function clampDur(v) {
    return Math.max(4, Math.min(15, Math.round(Number(v)) || 8));
}

function allNodes(graph, pred) {
    return (graph?._nodes || []).filter(pred);
}

// ── 预设 → 海螺 ─────────────────────────────────────────────

function syncPresetToHailuo(graph, srcNode) {
    const wDur = srcNode.widgets?.find(w => w.name === "视频时长");
    const wAsp = srcNode.widgets?.find(w => w.name === "画面比例");
    if (!wDur || !wAsp) return;

    const dur = clampDur(wDur.value);
    const targetAspect = RATIO_MAP[String(wAsp.value || "").trim()] || "";

    for (const h of allNodes(graph, n => HAILUO_TYPES.has(n.type))) {
        const hDur = h.widgets?.find(w => w.name === "duration");
        if (hDur && Number(hDur.value) !== dur) {
            hDur.value = dur;
            dispatch(hDur, dur);
        }
        const hAsp = h.widgets?.find(w => w.name === "aspect_ratio");
        if (hAsp && targetAspect && hAsp.value !== targetAspect) {
            hAsp.value = targetAspect;
            dispatch(hAsp, targetAspect);
        }
    }
}

// ── 海螺 → 预设 ─────────────────────────────────────────────

function syncHailuoToPreset(graph, srcNode) {
    const hDur = srcNode.widgets?.find(w => w.name === "duration");
    const hAsp = srcNode.widgets?.find(w => w.name === "aspect_ratio");
    if (!hDur || !hAsp) return;

    const dur = clampDur(hDur.value);
    const short = RATIO_REV[hAsp.value] || "";

    for (const p of allNodes(graph, n => n.type === MINIMAX_TYPE || n.type === REF2VA_TYPE)) {
        const pDur = p.widgets?.find(w => w.name === "视频时长");
        if (pDur && Number(pDur.value) !== dur) {
            pDur.value = dur;
            dispatch(pDur, dur);
        }
        const pAsp = p.widgets?.find(w => w.name === "画面比例");
        if (pAsp && short && pAsp.value !== short) {
            pAsp.value = short;
            dispatch(pAsp, short);
        }
    }
}

// ── widget callback 挂钩 ─────────────────────────────────────

function hookWidget(self, w, onUserChange) {
    let lastVal = w.value;
    const origCb = w.callback;
    w.callback = function (value) {
        origCb?.apply?.(this, arguments);
        const newVal = value ?? w.value;
        if (String(newVal) === String(lastVal)) return;  // 值未变（含回环反射），跳过
        lastVal = newVal;
        onUserChange(newVal);
    };
}

app.registerExtension({
    name: "JZL.MiniMax.PresetHailuoLink",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        const isPreset = nodeData?.name === MINIMAX_TYPE || nodeData?.name === REF2VA_TYPE;
        const isHailuo = HAILUO_TYPES.has(nodeData?.name);
        if (!isPreset && !isHailuo) return;

        const orig = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = orig?.apply(this, arguments);
            const self = this;

            setTimeout(() => {
                const graph = self.graph ?? app.graph;
                if (!graph) return;

                if (isPreset) {
                    const wDur = self.widgets?.find(w => w.name === "视频时长");
                    const wAsp = self.widgets?.find(w => w.name === "画面比例");
                    if (wDur) hookWidget(self, wDur, () => syncPresetToHailuo(graph, self));
                    if (wAsp) hookWidget(self, wAsp, () => syncPresetToHailuo(graph, self));
                } else {
                    const wDur = self.widgets?.find(w => w.name === "duration");
                    const wAsp = self.widgets?.find(w => w.name === "aspect_ratio");
                    if (wDur) hookWidget(self, wDur, () => syncHailuoToPreset(graph, self));
                    if (wAsp) hookWidget(self, wAsp, () => syncHailuoToPreset(graph, self));
                }
            }, 100);

            return r;
        };
    },
});
