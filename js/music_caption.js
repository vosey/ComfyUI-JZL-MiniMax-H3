import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// ============================================================
// JZL_MiniMaxMusicCaption — 一键配方 / 人声子项锁定 / 性别过滤
//   配方：切换后把各参数切到该配方的预设值（不锁定，可继续微调）
//   锁定用单值收敛，下拉过滤用 options.values
// ============================================================

const NODE_TYPE = "JZL_MiniMaxMusicCaption";
const DUET_NODE_TYPE = "JZL_MiniMaxMusicCaptionDuet";
const CONFIG = "人声配置";
const RECIPE = "配方";
const RECIPE_CUSTOM = "自定义 / Custom";
const NO_VOCALS = "无人声 / Instrumental (No Vocals)";
const FOLLOW = "跟随风格 / Follow Style";
const FEMALE = "女声 / Female Vocal";
const MALE = "男声 / Male Vocal";
// 合唱团（无人声时锁定）
const CHOIR = "合唱团";
// 合唱团关闭值（必须是 _CHOIR_HINTS 的合法键）
const CHOIR_OFF = "无 / None";
// 人声子控件（跟随风格/无人声时锁定）
const VOCAL_SUB = ["声部音区", "人声音色", "人声唱法", "和声伴唱", "人声效果"];
// 需要做「非法值自检」的下拉（历史工作流里可能残留旧版占位符 "—"）
const SANITIZE_WIDGETS = ["声部音区", "人声音色", "人声唱法", "和声伴唱", "人声效果",
    "合唱团", "主奏乐器", "辅助乐器"];
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

// 锁定：把下拉候选收敛为单一值（同时置 disabled 做半透明提示）。
// ⚠️ label 必须是该下拉的合法选项 —— 写成 "—" 之类的占位符会让 ComfyUI 后端
//    组合校验报 "Value not in list: 主奏乐器: '—' not in (list of length 25)"，
//    整个 prompt 会被拒（旧版就是这个 bug）。
function grayLock(w, label) {
    if (!w) return;
    if (!w.__jzlMusicLocked) {
        w.__jzlMusicLocked = true;
        w.__jzlMusicOrigValues = w.options ? w.options.values : undefined;
        w.__jzlMusicOrigValue = w.value;
    }
    if (w.options) w.options.values = [label];
    if (w.value !== label) w.value = label;
    w.disabled = true;
    if (w.options) w.options.disabled = true;
    if (w._state) w._state.disabled = true;
}

function unlock(w) {
    if (!w || !w.__jzlMusicLocked) return;
    w.__jzlMusicLocked = false;
    w.disabled = false;
    if (w.options) w.options.disabled = false;
    if (w._state) w._state.disabled = false;
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

// 自检修复：值不在当前选项中时回退到 fallback（或首个选项）。
// 用于清除历史工作流里被旧版占位符写坏的非法下拉值，否则后端会拒整个 prompt。
function sanitizeCombo(w, fallback) {
    if (!w || !w.options || !Array.isArray(w.options.values)) return;
    if (w.options.values.length <= 1) return;   // 已收敛锁定，跳过
    if (w.options.values.includes(w.value)) return;
    w.value = (fallback && w.options.values.includes(fallback)) ? fallback : w.options.values[0];
    if (w._state) w._state.value = w.value;
}

function sanitizeAll(node, extraNames) {
    for (const name of SANITIZE_WIDGETS.concat(extraNames || [])) {
        sanitizeCombo(getWidget(node, name), FOLLOW);
    }
}

function setComboValues(w, values, fallback) {
    if (!w) return;
    w.options = w.options || {};
    w.options.values = values;
    if (!values.includes(w.value)) {
        w.value = values.includes(fallback) ? fallback : values[0];
    }
}

// Nodes 2.0：改 widget 状态后，触发内部事件让 Vue 侧重新抽取节点数据，UI 才会刷新。
function refreshWidgets(node) {
    try { if (node && Array.isArray(node.widgets)) node.widgets = node.widgets.slice(); } catch (_) {}
    try { node?.graph?.trigger?.("node:slot-label:changed", { nodeId: node.id, slotType: 2 }); } catch (_) {}
    try { node?.setDirtyCanvas?.(true, true); } catch (_) {}
}

// ── 一键配方 ──
// 配方表来自后端（与 nodes_music._RECIPES 同一数据源），避免前后端两份表不同步
let _recipeCache = null;
let _recipeFetch = null;

function loadRecipes() {
    if (_recipeCache) return Promise.resolve(_recipeCache);
    if (!_recipeFetch) {
        _recipeFetch = api.fetchApi("/jzl/music_recipes")
            .then(r => r.json())
            .then(d => { _recipeCache = d || {}; return _recipeCache; })
            .catch(() => { _recipeCache = { single: {}, duet: {} }; return _recipeCache; });
    }
    return _recipeFetch;
}

// 切换配方：把预设值写入各 widget（不锁定，用户之后仍可手动微调）。
// 注意：直接写 value（不调 callback），避免填值过程中触发 sync 把后续项提前置灰。
function applyRecipe(node, which) {
    const table = _recipeCache ? _recipeCache[which] : null;
    const rw = getWidget(node, RECIPE);
    const label = rw ? rw.value : RECIPE_CUSTOM;
    if (!table || !label || label === RECIPE_CUSTOM) return;
    const values = table[label];
    if (!values) return;
    for (const name of Object.keys(values)) {
        const w = getWidget(node, name);
        if (!w) continue;
        unlock(w);                       // 先解除「跟随风格 / 无人声」的占位锁定
        if (w.value !== values[name]) {
            w.value = values[name];
            if (w._state) w._state.value = values[name];
        }
    }
}

function prepRecipes(node, which, resync) {
    loadRecipes().then(() => {
        applyRecipe(node, which);
        resync(node);
    });
}

// 配方切换后 sync，保持占位锁定/性别过滤与新参数一致
function syncAfterRecipe(node, which, resync) {
    applyRecipe(node, which);
    resync(node);
}

function sync(node) {
    const cfg = getWidget(node, CONFIG);
    const cfgValue = cfg ? cfg.value : "";
    const noVocals = cfgValue === NO_VOCALS;
    const follow = cfgValue === FOLLOW;

    sanitizeAll(node);

    for (const name of VOCAL_SUB) {
        const w = getWidget(node, name);
        if (!w) continue;
        if (noVocals) {
            grayLock(w, FOLLOW);
        } else if (follow && name !== "人声效果") {
            grayLock(w, FOLLOW);
        } else {
            unlock(w);
        }
    }
    // 无人声时锁定合唱团（人声配置=纯人声时仍可选：无伴奏合唱有效）
    const choirW = getWidget(node, CHOIR);
    if (choirW) {
        if (noVocals) grayLock(choirW, CHOIR_OFF);
        else unlock(choirW);
    }
    // 纯人声时锁定主奏/辅助乐器（vocal_only 时这两个值不会被使用）
    const acappella = cfgValue === A_CAPPELLA;
    for (const name of INSTRUMENT_WIDGETS) {
        const w = getWidget(node, name);
        if (!w) continue;
        if (acappella) grayLock(w, FOLLOW);
        else unlock(w);
    }
    // 声部音区性别过滤（仅未锁定时）
    const reg = getWidget(node, "声部音区");
    if (reg && !reg.__jzlMusicLocked) {
        if (cfgValue === MALE) setComboValues(reg, REGISTER_MALE, FOLLOW);
        else if (cfgValue === FEMALE) setComboValues(reg, REGISTER_FEMALE, FOLLOW);
        else setComboValues(reg, REGISTER_ALL, FOLLOW);
    }
    refreshWidgets(node);

    node.setDirtyCanvas?.(true, true);
    node.graph?.setDirtyCanvas?.(true, true);
}

function syncDuet(node) {
    sanitizeAll(node, DUET_PAIRS.flatMap(p => [p.config, p.register]));
    const acapW = getWidget(node, DUET_ACAPPELLA);
    const acappella = acapW ? asBoolean(acapW.value) : false;
    for (const name of INSTRUMENT_WIDGETS) {
        const w = getWidget(node, name);
        if (!w) continue;
        if (acappella) grayLock(w, FOLLOW);
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
    }    refreshWidgets(node);
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

            requestAnimationFrame(() => prepRecipes(self, "single", sync));

            for (const key of [CONFIG, RECIPE]) {
                const w = getWidget(self, key);
                if (!w) continue;
                const origCb = w.callback;
                w.callback = function (v) {
                    if (origCb) origCb.apply(this, arguments);
                    if (w.name === RECIPE) { syncAfterRecipe(self, "single", sync); return; }
                    sync(self);
                };
            }

            const onConfigure = self.onConfigure;
            self.onConfigure = function (info) {
                const r = onConfigure?.apply(this, arguments);
                requestAnimationFrame(() => { applyRecipe(self, "single"); sync(self); });
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

            requestAnimationFrame(() => prepRecipes(self, "duet", syncDuet));

            for (const key of [RECIPE, DUET_ACAPPELLA, ...DUET_PAIRS.map(p => p.config)]) {
                const w = getWidget(self, key);
                if (!w) continue;
                const origCb = w.callback;
                w.callback = function (v) {
                    if (origCb) origCb.apply(this, arguments);
                    if (w.name === RECIPE) { syncAfterRecipe(self, "duet", syncDuet); return; }
                    syncDuet(self);
                };
            }

            const onConfigure = self.onConfigure;
            self.onConfigure = function (info) {
                const r = onConfigure?.apply(this, arguments);
                requestAnimationFrame(() => { applyRecipe(self, "duet"); syncDuet(self); });
                return r;
            };

            return result;
        };
    },
});
