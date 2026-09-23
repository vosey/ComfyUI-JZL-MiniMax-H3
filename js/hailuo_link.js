/**
 * JZL 海螺H3视频参数 ↔ 剧本与镜头处理器 — 时长联动（XB 同款稳健版）
 * ====================================================================
 * 复刻 XB_ToolBox 的 xb_minimax_hailuo_link.js 机制：
 *   1) 300ms 轮询，首轮即对齐（last 缓存初始 null）
 *   2) 值相等才写（!== 判断）——阻止来回跳的第一道闸
 *   3) 100ms 防抖窗口（_jzl_linked_sync + setTimeout）——覆盖反射期
 *   4) w.element 优先派发（新版 ComfyUI DOM 入口），兼容 inputEl
 * 只同步时长：duration（海螺）↔ segment_duration（剧本与镜头处理器）。
 */

import { app } from "../../scripts/app.js";

const PROCESSOR_TYPE = "JZL_MiniMax_ScriptProcessor";
const HAILUO_TYPES = new Set(["JZL_HailuoH3VideoParams", "JZL_HailuoH3VideoParamsPro"]);

function dispatch(w, val) {
    if (!w) return;
    const el = w.element || w.inputEl;
    // Nodes 2.0：combo/number 是 Vue 组件，没有 element 可直接派发 → 写 value + 走 callback
    if (!el) {
        if (w.value !== val) w.value = val;
        try { w.callback?.(val); } catch (_) {}
        return;
    }
    el.value = val;
    // 只触发原生事件让 ComfyUI 统一更新 value 和 callback；不手动调 callback，避免双重触发
    const evt = el.tagName === "SELECT" ? "change" : "input";
    el.dispatchEvent(new Event(evt, { bubbles: true }));
}

function syncProcessorToHailuo(graph) {
    const procNodes = graph._nodes.filter(n => n.type === PROCESSOR_TYPE);
    const haiNodes = graph._nodes.filter(n => HAILUO_TYPES.has(n.type));
    if (!procNodes.length || !haiNodes.length) return;

    const wDur = procNodes[0].widgets?.find(w => w.name === "segment_duration");
    if (!wDur) return;
    const val = Math.max(4, Math.min(15, Math.round(Number(wDur.value)) || 8));

    for (const h of haiNodes) {
        if (h._jzl_linked_sync) continue;
        h._jzl_linked_sync = true;
        const wHai = h.widgets?.find(w => w.name === "duration");
        if (wHai && Number(wHai.value) !== val) {
            wHai.value = val;
            dispatch(wHai, val);
        }
        setTimeout(() => { h._jzl_linked_sync = false; }, 100);
    }
}

function syncHailuoToProcessor(graph) {
    const procNodes = graph._nodes.filter(n => n.type === PROCESSOR_TYPE);
    const haiNodes = graph._nodes.filter(n => HAILUO_TYPES.has(n.type));
    if (!procNodes.length || !haiNodes.length) return;

    const wHai = haiNodes[0].widgets?.find(w => w.name === "duration");
    if (!wHai) return;
    const val = Math.max(4, Math.min(15, Math.round(Number(wHai.value)) || 8));

    for (const p of procNodes) {
        if (p._jzl_linked_sync) continue;
        p._jzl_linked_sync = true;
        const wProc = p.widgets?.find(w => w.name === "segment_duration");
        if (wProc && Number(wProc.value) !== val) {
            wProc.value = val;
            dispatch(wProc, val);
        }
        setTimeout(() => { p._jzl_linked_sync = false; }, 100);
    }
}

app.registerExtension({
    name: "JZL.MiniMax.HailuoLink",

    init() {
        let lastProcDur = null;
        let lastHaiDur = null;

        setInterval(() => {
            if (!app.graph || !app.graph._nodes) return;

            // 检测剧本处理器 segment_duration 变化
            for (const node of app.graph._nodes) {
                if (node.type !== PROCESSOR_TYPE || !node.widgets) continue;
                const wDur = node.widgets.find(w => w.name === "segment_duration");
                if (!wDur) continue;
                const v = Number(wDur.value) || 8;
                if (lastProcDur !== v) {
                    lastProcDur = v;
                    syncProcessorToHailuo(app.graph);
                }
            }

            // 检测海螺 duration 变化
            for (const node of app.graph._nodes) {
                if (!HAILUO_TYPES.has(node.type) || !node.widgets) continue;
                const wDur = node.widgets.find(w => w.name === "duration");
                if (!wDur) continue;
                const v = Math.round(Number(wDur.value)) || 8;
                if (lastHaiDur !== v) {
                    lastHaiDur = v;
                    syncHailuoToProcessor(app.graph);
                }
            }
        }, 300);
    },
});
