import { app } from "../../scripts/app.js";

// ============================================================
// JZL_MiniMaxMusicCaption — 高级参数折叠 + 人声子项锁定/性别过滤
//   折叠用 widget.type="hidden" + computeSize 方案（实测生效）；
//   锁定用单值收敛，下拉过滤用 options.values
// ============================================================

const NODE_TYPE = "JZL_MiniMaxMusicCaption";
const DUET_NODE_TYPE = "JZL_MiniMaxMusicCaptionDuet";
const ADVANCED = "高级参数";
const CONFIG = "人声配置";
const NO_VOCALS = "无人声 / Instrumental (No Vocals)";
const FOLLOW = "跟随风格 / Follow Style";
const FEMALE = "女声 / Female Vocal";
const MALE = "男声 / Male Vocal";
const LOCK_PLACEHOLDER = "—";
// 高级参数折叠的 widget
const ADVANCED_WIDGETS = ["风格融合", "拍号", "情绪演变", "段落结构"];
// 人声子控件（跟随风格/无人声时置灰锁定）
const VOCAL_SUB = ["声部音区", "人声音色", "人声唱法", "和声伴唱", "人声效果"];
// 声部音区候选（用于性别过滤）
const REGISTER_ALL = [
    "跟随风格 / Follow Style",
    "女高音 / Soprano", "女中音 / Mezzo-Soprano", "女低音 / Alto",
    "男高音 / Tenor", "男中音 / Baritone", "男中高音 / Baritenor", "男低音 / Bass",
];
const REGISTER_FEMALE = ["跟随风格 / Follow Style", "女高音 / Soprano", "女中音 / Mezzo-Soprano", "女低音 / Alto"];
const REGISTER_MALE = ["跟随风格 / Follow Style", "男高音 / Tenor", "男中音 / Baritone", "男中高音 / Baritenor", "男低音 / Bass"];
// 双人版：角色配置 → 音区 的性别过滤
const DUET_PAIRS = [
    { config: "角色A配置", register: "角色A音区" },
    { config: "角色B配置", register: "角色B音区" },
];
// 纯人声（无伴奏）
const A_CAPPELLA = "纯人声 / Acappella (Vocals Only)";
const DUET_ACAPPELLA = "纯人声无伴奏";
const INSTRUMENT_WIDGETS = ["主奏乐器", "辅助乐器"];

function asBoolean(v) { return v === true || v === "true" || Number(v) === 1; }

function getWidget(node, name) {
    return (node.widgets || []).find(w => w.name === name) || null;
}

// 折叠：把 widget.type 改为 "hidden" 并覆写 computeSize，走 litegraph 传统隐藏路径。
// （新版 Vue 前端直接改 options.hidden 不触发重渲染，type 折叠才是实际生效的。）
function rowHeight(node, w) {
    if (!w) return 0;
    if (w.__jzlMusicRowH > 0) return w.__jzlMusicRowH;
    const fn = w.computeSize;
    try {
        const width = Math.max(80, Number(node?.size?.[0]) || 220);
        const sz = fn?.call(w, width);
        const h = Number(sz?.[1]);
        if (h > 0) { w.__jzlMusicRowH = h; return h; }
    } catch (_) {}
    w.__jzlMusicRowH = 26;
    return 26;
}

function hideWidget(node, w) {
    if (!w || w.type === "hidden") return 0;
    const h = rowHeight(node, w);
    w.__jzlMusicOrigType = w.type;
    w.__jzlMusicOrigComputeSize = w.computeSize;
    w.hidden = true;
    // Nodes 2.0：可见性看 options.hidden（只改 type/hidden 在 DOM 渲染下不生效）
    if (!w.options) w.options = {};
    w.options.hidden = true;
    if (w.inputEl) w.inputEl.style.display = "none";
    if (w.element) w.element.style.display = "none";
    w.type = "hidden";
    w.computeSize = () => [0, -4];
    w.computedHeight = 0;
    if (w._state) {
        w._state.hidden = true; w._state.type = "hidden"; w._state.computedHeight = 0;
        if (w._state.options) w._state.options.hidden = true;
    }
    return -h;
}

function showWidget(w) {
    if (!w || w.type !== "hidden" || !Object.prototype.hasOwnProperty.call(w, "__jzlMusicOrigType")) return 0;
    w.hidden = false;
    if (!w.options) w.options = {};
    w.options.hidden = false;
    if (w.inputEl) w.inputEl.style.display = "";
    if (w.element) w.element.style.display = "";
    w.type = w.__jzlMusicOrigType;
    if (w.__jzlMusicOrigComputeSize) w.computeSize = w.__jzlMusicOrigComputeSize;
    else delete w.computeSize;
    delete w.computedHeight;
    const h = w.__jzlMusicRowH || 26;
    if (w._state) {
        w._state.hidden = false; w._state.type = w.type; delete w._state.computedHeight;
        if (w._state.options) w._state.options.hidden = false;
    }
    delete w.__jzlMusicOrigType;
    delete w.__jzlMusicOrigComputeSize;
    return h;
}

function adjustHeight(node, delta) {
    if (!delta || !node?.size) return;
    const w = Number(node.size[0]) || 0;
    const h = Math.max(0, Number(node.size[1]) + delta);
    node.setSize?.([w, h]);
}

// 锁定：把下拉候选收敛为单一值，视觉上只显示 "—" / "跟随风格"
function grayLock(w, label) {
    if (!w) return;
    if (!w.__jzlMusicLocked) {
        w.__jzlMusicLocked = true;
        w.__jzlMusicOrigValues = w.options ? w.options.values : undefined;
        w.__jzlMusicOrigValue = w.value;
    }
    if (w.options) w.options.values = [label];
    if (w.value !== label) w.value = label;
}

function unlock(w) {
    if (!w || !w.__jzlMusicLocked) return;
    w.__jzlMusicLocked = false;
    if (w.options && Array.isArray(w.__jzlMusicOrigValues)) {
        w.options.values = w.__jzlMusicOrigValues;
    }
    const vals = w.options?.values || [];
    if (w.__jzlMusicOrigValue !== undefined && vals.includes(w.__jzlMusicOrigValue)) {
        w.value = w.__jzlMusicOrigValue;
    } else if (vals.length) {
        w.value = vals[0];
    }
    delete w.__jzlMusicOrigValues;
    delete w.__jzlMusicOrigValue;
}

function setComboValues(w, values, fallback) {
    if (!w) return;
    w.options = w.options || {};
    w.options.values = values;
    if (!values.includes(w.value)) {
        w.value = values.includes(fallback) ? fallback : values[0];
    }
}

function syncFold(node) {
    const adv = getWidget(node, ADVANCED);
    const advanced = adv ? asBoolean(adv.value) : false;
    let delta = 0;
    for (const name of ADVANCED_WIDGETS) {
        const w = getWidget(node, name);
        delta += advanced ? showWidget(w) : hideWidget(node, w);
    }
    if (delta !== 0) adjustHeight(node, delta);
    refreshWidgets(node);
}

// Nodes 2.0：在 onNodeCreated 阶段改可见性时，只改 type/hidden/options.hidden 不会让 DOM 重渲染。
// 实测：触发 node:slot-label:changed（内部事件）会让 Vue 侧重新抽取节点数据，可见性立刻生效。
function refreshWidgets(node) {
    try { if (node && Array.isArray(node.widgets)) node.widgets = node.widgets.slice(); } catch (_) {}
    try { node?.graph?.trigger?.("node:slot-label:changed", { nodeId: node.id, slotType: 2 }); } catch (_) {}
    try { node?.setDirtyCanvas?.(true, true); } catch (_) {}
}

function sync(node) {
    const cfg = getWidget(node, CONFIG);
    const cfgValue = cfg ? cfg.value : "";
    const noVocals = cfgValue === NO_VOCALS;
    const follow = cfgValue === FOLLOW;

    syncFold(node);

    for (const name of VOCAL_SUB) {
        const w = getWidget(node, name);
        if (!w) continue;
        if (noVocals) {
            grayLock(w, LOCK_PLACEHOLDER);
        } else if (follow && name !== "人声效果") {
            grayLock(w, FOLLOW);
        } else {
            unlock(w);
        }
    }
    // 纯人声时锁定主奏/辅助乐器
    const acappella = cfgValue === A_CAPPELLA;
    for (const name of INSTRUMENT_WIDGETS) {
        const w = getWidget(node, name);
        if (acappella) grayLock(w, LOCK_PLACEHOLDER);
        else unlock(w);
    }
    // 声部音区性别过滤（仅未锁定时）
    const reg = getWidget(node, "声部音区");
    if (reg && !reg.__jzlMusicLocked) {
        if (cfgValue === MALE) setComboValues(reg, REGISTER_MALE, FOLLOW);
        else if (cfgValue === FEMALE) setComboValues(reg, REGISTER_FEMALE, FOLLOW);
        else setComboValues(reg, REGISTER_ALL, FOLLOW);
    }
    node.setDirtyCanvas?.(true, true);
    node.graph?.setDirtyCanvas?.(true, true);
}

function syncDuet(node) {
    syncFold(node);
    const acapW = getWidget(node, DUET_ACAPPELLA);
    const acappella = acapW ? asBoolean(acapW.value) : false;
    for (const name of INSTRUMENT_WIDGETS) {
        const w = getWidget(node, name);
        if (acappella) grayLock(w, LOCK_PLACEHOLDER);
        else unlock(w);
    }
    for (const pair of DUET_PAIRS) {
        const cfgW = getWidget(node, pair.config);
        const regW = getWidget(node, pair.register);
        if (!cfgW || !regW) continue;
        const cfgValue = cfgW.value;
        if (cfgValue === MALE) setComboValues(regW, REGISTER_MALE, FOLLOW);
        else if (cfgValue === FEMALE) setComboValues(regW, REGISTER_FEMALE, FOLLOW);
        else setComboValues(regW, REGISTER_ALL, FOLLOW);
    }
    node.setDirtyCanvas?.(true, true);
    node.graph?.setDirtyCanvas?.(true, true);
}

app.registerExtension({
    name: "JZL.MusicCaption",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== NODE_TYPE) return;
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            const self = this;
            const cfg = getWidget(self, CONFIG);
            if (!cfg) return result;

            requestAnimationFrame(() => sync(self));

            for (const key of [ADVANCED, CONFIG]) {
                const w = getWidget(self, key);
                if (!w) continue;
                const origCb = w.callback;
                w.callback = function (v) {
                    if (origCb) origCb.apply(this, arguments);
                    sync(self);
                };
            }

            const onConfigure = self.onConfigure;
            self.onConfigure = function (info) {
                const r = onConfigure?.apply(this, arguments);
                requestAnimationFrame(() => sync(self));
                return r;
            };

            return result;
        };
    },
});

app.registerExtension({
    name: "JZL.MusicCaptionDuet",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== DUET_NODE_TYPE) return;
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            const self = this;

            requestAnimationFrame(() => syncDuet(self));

            for (const key of [ADVANCED, DUET_ACAPPELLA, ...DUET_PAIRS.map(p => p.config)]) {
                const w = getWidget(self, key);
                if (!w) continue;
                const origCb = w.callback;
                w.callback = function (v) {
                    if (origCb) origCb.apply(this, arguments);
                    syncDuet(self);
                };
            }

            const onConfigure = self.onConfigure;
            self.onConfigure = function (info) {
                const r = onConfigure?.apply(this, arguments);
                requestAnimationFrame(() => syncDuet(self));
                return r;
            };

            return result;
        };
    },
});
