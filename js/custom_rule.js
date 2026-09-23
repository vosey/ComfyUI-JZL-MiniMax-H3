import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// ============================================================
// JZL_MiniMax_ScriptProcessor — 自定义规则开关 +「📂 浏览」文件选择
//   复用后端 /jzl/choose_txt_file（tkinter 文件选择器）
//   「默认规则/自定义规则」开关控制 custom_rule_path 与浏览按钮显隐
//   custom_rule_path 与浏览按钮位于节点最下面（optional 区域）
// ============================================================

const NODE_TYPE = "JZL_MiniMax_ScriptProcessor";

function getWidget(node, name) { return node.widgets?.find((w) => w.name === name); }
function asBoolean(v) { return v === true || v === "true" || Number(v) === 1; }

function setHidden(widget, hidden) {
    if (!widget) return;
    if (!Object.prototype.hasOwnProperty.call(widget, "__origComputeSize")) {
        widget.__origComputeSize = widget.computeSize;
    }
    widget.hidden = hidden;
    // Nodes 2.0：可见性看 options.hidden（只看 widget.hidden / type="hidden" 是藏不住的）
    if (!widget.options) widget.options = {};
    widget.options.hidden = hidden;
    if (hidden) {
        widget.computeSize = () => [0, -4];
        if (widget.inputEl) widget.inputEl.style.display = "none";
        if (widget.element) widget.element.style.display = "none";
    } else {
        widget.computeSize = widget.__origComputeSize;
        if (widget.inputEl) widget.inputEl.style.display = "";
        if (widget.element) widget.element.style.display = "";
    }
    if (widget._state) {
        widget._state.hidden = hidden;
        if (widget._state.options) widget._state.options.hidden = hidden;
    }
}

function syncCustomRuleVisibility(node) {
    const toggle = getWidget(node, "use_custom_rule");
    const on = toggle ? asBoolean(toggle.value) : false;
    setHidden(getWidget(node, "custom_rule_path"), !on);
    setHidden(getWidget(node, "选择自定义规则文件"), !on);
    // Nodes 2.0：改完可见性要触发一次前端重渲染（只改 type/hidden/options.hidden 不会立刻生效）
    try { if (Array.isArray(node.widgets)) node.widgets = node.widgets.slice(); } catch (_) {}
    try { node.graph?.trigger?.("node:slot-label:changed", { nodeId: node.id, slotType: 2 }); } catch (_) {}
    node.setDirtyCanvas?.(true, true);
}

app.registerExtension({
    name: "jzl.customRulePath",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_TYPE) return;
        const orig = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = orig?.apply(this, arguments);
            const self = this;

            setTimeout(() => {
                const btn = self.addWidget("button", "选择自定义规则文件", "📂 浏览", async () => {
                    try {
                        const resp = await api.fetchApi("/jzl/choose_txt_file", {
                            method: "POST",
                            body: JSON.stringify({ default_dir: "" }),
                            headers: { "Content-Type": "application/json" },
                        });
                        const data = await resp.json();
                        if (data.path) {
                            const w = getWidget(self, "custom_rule_path");
                            if (w) {
                                w.value = data.path;
                                if (w.inputEl) w.inputEl.value = data.path;
                            }
                            self.setDirtyCanvas?.(true, true);
                            app.graph?.change?.();
                        }
                    } catch (_) {}
                }, { serialize: false });

                const toggle = getWidget(self, "use_custom_rule");
                if (toggle) {
                    const origCb = toggle.callback;
                    toggle.callback = function (value) {
                        origCb?.apply?.(this, arguments);
                        syncCustomRuleVisibility(self);
                    };
                }
                syncCustomRuleVisibility(self);
            }, 200);

            return r;
        };
    },
});
