# JZL-MiniMax-H3 · ComfyUI「Nodes 2.0」兼容性修复记录

- 环境：ComfyUI 0.37.0 + 前端 `comfyui_frontend_package 1.52.7`
- 开关：设置 `Comfy.VueNodes.Enabled` = **Modern Node Design (Nodes 2.0)**（用户本地为开启状态）
- 起因：用户报「短剧导演台节点，提示词输入栏在 2.0 下没有滚动条」；随后排查到本包还有若干处沿用 1.0 画布假设的代码

---

## 一、Nodes 2.0 的三条硬规则（全部实测得出）

### 规则 1：隐藏 widget 只能靠 `options.hidden`
2.0 的节点是 Vue/DOM 渲染，`LGraphCanvas.drawNode()` 直接 early-return，所以：

| 做法 | 1.0（canvas） | 2.0（Vue DOM） |
| --- | --- | --- |
| `widget.type = "hidden"` | ✅ 生效 | ❌ 不生效 |
| `widget.hidden = true` | ✅ 生效 | ❌ 不生效 |
| `widget.computeSize = () => [0,-4]` | ✅ 生效 | ❌ 不生效 |
| `widget.options.hidden = true` | （无影响） | ✅ **唯一生效方式** |
| DOM 元素 `style.display = "none"` | （不适用） | ⚠️ 仅对 DOM widget 有效，且尺寸仍可能占位 |

> 结论：隐藏必须写 `w.options.hidden = true`（同时保留旧写法以兼容 1.0），DOM 元素额外置 `display:none`。

### 规则 2：改完可见性必须「叫醒」Vue 侧
在 `onNodeCreated` 等早期时机改完 `options.hidden` 后，**DOM 不会立刻重渲染**（数据已对、界面上还看得见）。
逐一试过且**无效**的方式：改 `type` / `hidden` / `options.hidden` / `_state.type` / `_state.hidden` / `_state.options.hidden`、
`node.widgets = node.widgets.slice()`、`setDirtyCanvas`、`graph.incrementVersion()`、`setSize()`、`onResize()`、延时重试。

**有效方式（本包统一采用）**：

```js
function refreshWidgets(node) {                       // 见 js/music_caption.js、js/custom_rule.js、js/llama_pro.js、js/asset_manager.js
    try { if (node && Array.isArray(node.widgets)) node.widgets = node.widgets.slice(); } catch (_) {}
    try { node?.graph?.trigger?.("node:slot-label:changed", { nodeId: node.id, slotType: 2 }); } catch (_) {}
    try { node?.setDirtyCanvas?.(true, true); } catch (_) {}
}
```

`node:slot-label:changed` 是前端内部事件，触发它会让节点数据被重新抽取（`extractVueNodeData`）→ Vue 重渲染 → 可见性立即生效。
前端版本变化时该事件若消失，最坏情况是退回「等某个 widget 值变化才刷新」，不会报错（已 try/catch）。

### 规则 3：DOM 渲染下节点高度由内容决定，`height:100%` 解析不到确定高度
短剧导演台面板是「容器 `height:100%` + 提示词区 `flex:1 1 auto`」的经典满高布局，在 2.0 下：
容器高度不可解析 → `flex:1` 的提示词区跟着文本无限长高（实测：文本框 59 → 972px、节点 1647px）→ **没有滚动条、节点被撑爆**。

修法：给提示词区**确定的像素高度**（默认 280，下限 280，上限 900），并且**只由用户的拖拽动作驱动变化**：

```js
// 变量名见 js/asset_manager.js 的 Nodes 2.0 布局块
默认：applyPromptH2(280)                                   // 首次布局，固定默认值
拖拽中（pointerdown 命中原生尺寸手柄 → pointermove → pointerup）：
      d = (e.clientY − 拖拽起点 clientY) / app.canvas.ds.scale   // 屏幕位移 → 布局位移
      if (手柄在 N 角) d = −d                                     // 拖上边：指针向上 = 节点变高
      h = clamp(拖拽起点的框高 + d, 280, 900)
```

关键点与踩过的坑（均为实测）：

- ✅ **为什么必须实时跟着指针走**：2.0 下节点高度 = DOM 内容高度，**节点不允许小于内容**。
  若不主动缩内容，用户往回拖时节点根本不动（实测卡在内容高度）⇒ 一旦拖大过就再也拖不小（棘轮）。
  用指针位移实时改框高，等于「边拖边缩内容」，两个方向都跟手。
- ⚠️ **不能**用「节点高度 − 面板顶部偏移 − 面板其余内容」反推：容器**下方**还有一片 DOM（原生 widget 行 + 高级输入按钮，实测约 233px）未被计入 → 公式系统性偏大 → 默认值被顶到上限 900（用户反馈「默认太高」）。
- ⚠️ **不能**用「节点高度增量」跟随：写框高会把节点撑高，增量被误当成用户拖拽 → 自激到 900。
- ⚠️ **不能**用 `container.clientHeight − scrollHeight` 当「剩余空白」：内容比容器**矮**时 `scrollHeight` 会被钳到 `clientHeight`，差值恒为 0 → 拖大节点输入框纹丝不动。
- ⚠️ **不能**在拖完之后再「填满剩余空白」：引导阶段/拖拽结束时节点高度会被前端与面板自身代码临时抬高（实测松手 200ms 后节点被顶到 1573），
  一旦去填就被顶到上限，且再也缩不回来 → 用户遇到「拖回去也不变小」。
- ✅ 顺带修掉抬高节点的元凶：`resizeNodeForContent()` 原本用 `widget.y + minDom` 反推节点高度，
  但 2.0 里 `widget.y` 会被前端重算（实测可达 1300+）→ 节点被凭空顶高；2.0 下节点本来就会随 DOM 内容自动掉高，故该 `setSize` 在 2.0 直接跳过。
- ⚠️ 重排**不能**在 `ResizeObserver` 回调里同步执行，否则拖拽节点会刷 `ResizeObserver loop completed with undelivered notifications`；
  丢到下一帧（`requestAnimationFrame` + 同帧去重）后警告完全消失
- 其它触发点：初始 `setTimeout [0,50,150,400,900,1600]`、`ResizeObserver(container)`、包裹 `node.onResize`
- 上限：**已取消**（`PROMPT_H2_MAX = 100000`）。原为 900，用户把节点拉得比 900 还高时输入框就不再跟着长（报障 ①）；
  现在实测可到 1721px 仍在跟随。

### 规则 4：滚轮归属由 `data-capture-wheel` 决定（不是靠 stopPropagation）
前端 `settingStore` 里的判定（源码原文）：

```js
wheelCapturedByFocusedElement = (e) => {
  const t = e.target?.closest('[data-capture-wheel="true"]');
  const n = document.activeElement;
  return !!(t && n && t.contains(n));       // 打标记 + 该控件处于聚焦状态
};
shouldForwardWheelEvent = (e) => !wheelCapturedByFocusedElement(e) || isCanvasGestureWheel(e);
forwardEventToCanvas 内部：e.preventDefault(); e.stopPropagation(); canvas.dispatchEvent(new WheelEvent('wheel', …));
```

- 不满足条件时，前端会把滚轮**转交给画布**（在 window/document 的 **capture** 阶段就 preventDefault+stopPropagation）⇒
  下游任何 `stopPropagation` 都无效（实测：在 1.0 用容器级 capture 拦截完全拦不住，框 `scrollTop` 不变、画布 `scale` 0.382→0.347）。
- ✅ 正确做法：给提示词框与重拍提示词框的包裹元素加 `data-capture-wheel="true"`
  （`asset_manager.js`：`promptWrap.setAttribute("data-capture-wheel","true")`、`editWrap.setAttribute(...)`），
  元素内的可滚动子元素聚焦后滚轮就归自己；`ctrl/shift` 等画布手势仍照旧缩放着画布。
- 实测：点击输入框聚焦后滚轮 → `scrollTop` 300 / 260（主框 / 重拍框），画布 `scale` 保持 0.3817 不变 ✅

### 规则 5：Nodes 2.0 开关是**运行时**可切换的，判定不能只做一次
用户在设置里切开关**不会刷新页面**。旧写法把判定缓存成 `const IS_NODES2_LAYOUT`：
切回经典模式后 px 固定高度仍然生效 → 用户报「开关过 2.0 之后高度被锁死」（报障 ③）。

- 改法：`isNodes2Now()` 每次实时读设置；1 秒轮询对比模式（`setInterval`，节点移除时 `clearInterval`）。
  - 切到 2.0 → 补挂尺寸手柄监听 + 重新应用默认高度；
  - 切回经典 → 把 `promptWrap/promptBox` 的行内样式**还原成首次改写前保存的原值**（`origH2`），交回原有 flex 满高布局。
    注意是「还原」而不是 `removeProperty`：`promptBox` 的 `flex:1 1 auto` / `min-height:60px` 是面板自己写在行内样式里的，删掉会破版。
- 两种模式下都装重排调度（经典模式下 `relayoutForNodes2` 直接 return，零开销）。
- 实测：2.0 → 关闭：行内 `height` 被清空、`flex` 回到 `1 1 auto`（高度不再锁死）；再打开：回到 280px 并恢复拖拽跟随 ✅

---

## 二、逐文件改动清单

| 文件 | 问题 | 修复 |
| --- | --- | --- |
| `js/asset_manager.js`（Pro/Max/Infinite 三个导演台共用） | ① 面板提示词区在 2.0 下没有滚动条、节点被撑爆（默认框高被顶到 900，用户反馈太高；且拖节点输入框不跟随） ② 初始隐藏的内部 widget 在 2.0 下不消失 ③ 拖拽结束后面板会把节点凭空顶高 ④ 拉伸超过 900 就不跟随 ⑤ 框内滚轮被画布抢走（变成缩放画布） ⑥ 切换 Nodes 2.0 开关后框高被锁死 | ① 新增 2.0 布局块：`applyPromptH2()` 给确定高度（**默认/下限 280**）+ **拖尺寸手柄时按指针位移实时跟随**（两个方向都跟手） ② 两处隐藏循环后补 `options.hidden` + 刷新调用 ③ `resizeNodeForContent()` 在 2.0 跳过用 `widget.y` 反推高度的 `setSize` ④ 上限从 900 改为 100000（实即取消） ⑤ 两个提示词框的包裹元素加 `data-capture-wheel="true"`（+ 面板内滚动区的 wheel 拦截兼容老版） ⑥ `isNodes2Now()` 实时判定 + 1s 轮询，切回经典时还原行内样式 |
| `js/music_caption.js` | `hideWidget/showWidget` 只改 `type`/`hidden`；折叠后不刷新 | 补 `options.hidden`、`_state.options.hidden`；`syncFold()` 末尾调用 `refreshWidgets(node)` |
| `js/custom_rule.js` | 隐藏只写本地 `_state`，2.0 不生效 | `setHidden()` 同步写 `options.hidden`；`syncCustomRuleVisibility()` 末尾刷新 |
| `js/llama_pro.js` | 高级参数折叠在 2.0 下不消失 | `syncAdvancedWidgets()` 末尾刷新 |
| `js/scene_dispatcher.js` | 直接访问 `w.inputEl` 可能为空 → 抛错中断 | 全部加空值保护；显示用 widget 补 `options.read_only` |
| `js/shot_formatter.js` | 同上（`_reshoot_path` 元素访问）、按钮可见性用画布写法 | 加保护；可见性改 `options.hidden` |
| `js/hailuo_link.js`、`js/minimax_hailuo_link.js` | `dispatch()` 依赖 `w.inputEl` 派值 | 无元素时回退 `w.value = val; w.callback?.(val)` |
| `js/hailuo_video.js`、`js/list_dispatcher.js` | 只读显示 widget 在 2.0 下仍可编辑/样式不统一 | 补 `options.read_only` |
| `nodes_asset_manager.py` | ①「生成详情」（`display_info`）被 `advanced=True` 归进前端「高级输入」，要展开高级才看得到 ② 节点底部一直挂着「显示高级输入」开关，但点它没有任何可见变化（剩下的高级项只有 2 个内部字段 + 4 个模型输入，前者被 JS 隐藏、后者本来就是可见 socket）→ 纯粹碍眼 | ①② 四个导演台节点（Pro/Max/Infinite/Mini）**去掉全部 `advanced=True`**（`display_info`、`internal_prompt`、`manager_settings`、`model`、`clip`、`vae`、`audio_vae`，共 7×4 处）→ 「生成详情」常显、**「显示高级输入」开关彻底消失**。⚠️ 改 Python 的 INPUT_TYPES **必须重启 ComfyUI** 才生效 |

> 说明：以上都是「1.0 能跑、2.0 有毛病」的写法；改动均向后兼容（1.0 下 `options.hidden` 不影响 canvas 渲染，
> `graph.trigger` 与 rAF 无副作用）。

---

## 三、验证记录（真实页面实测，`Comfy.VueNodes.Enabled = true`）

| 检查项 | 结果 |
| --- | --- |
| 音乐提示词预设：新建节点时 4 个折叠项（风格融合/拍号/情绪演变/段落结构） | DOM 中**不可见**；数据 `type="hidden"`、`hidden=true`、`options.hidden=true`；常显项（音乐风格/情绪氛围）仍可见 ✅ |
| 导演台（Pro / Max / Infinite 三个节点）：新建时提示词编辑区高度 | 三者均 = **280px**，节点高 953px（旧实现是 900px / 1573px）✅ |
| 同上：再等 2.6s（稳定性） | 仍是 280px，**无漂移、无自激** ✅ |
| 同上：工作流加载路径（已有节点） | 加载后也是 280px ✅ |
| 同上：灌入 60 行长文本 | 框高不变（804px），`scrollHeight 972 > 客户端高` → 可滚动；`scrollTop` 可移动 ✅ |
| 同上：真实拖拽右下角手柄（+120 / −120 / −120 / +200 屏幕像素，页面缩放 0.382） | 框高 **280 → 594 → 280 → 280 → 804**；节点高 **953 → 1270 → 960 → 953 → 1480**；
拖大跟手 ✅、拖小跟手 ✅、到下限 280 停住 ✅、松手后不再被顶到上限 ✅ |
| 同上：拖拽结束后静置 1.7s | 框高保持（594 / 280 / 804），**无回弹、无自激** ✅ |
| Pro / Max 节点同样做真实拖拽 | Pro：280 → 594 → 280；Max：280 → 437 → 647（节点 953 → 1120 → 1330）——三个导演台行为一致 ✅ |
| 控制台报错 | 加载 / 建节点 / 拖拽后均为 `[]`，ResizeObserver 警告 0 条 ✅ |
| 滚轮（主提示词框，60 行长文） | 点击聚焦后滚轮：`scrollTop` **300**，画布 `scale` 保持 **0.3817** 不变（修复前：`scrollTop` 0、`scale` → 0.347）✅ |
| 滚轮（重拍模式提示词框，60 行） | 聚焦后滚轮：`scrollTop` **260**，画布 `scale` 不变 ✅ |
| 拉伸超过 900 | 连续拖拽后框高 **1721px**（远超旧的 900 上限），松手后保持 ✅ |
| 关闭 Nodes 2.0 开关（免刷新） | 行内 `height` 被清空、`flex` 回到 `1 1 auto`（高度不再锁死，交回原有 flex 布局）✅ |
| 再打开 Nodes 2.0 开关 | 框高回到 **280px**，且拖拽跟随仍然有效（280 → 1066 → 280）✅ |
| 语法校验 | 本包 17 个 JS 文件 `--check` 全通过 ✅ |

---

## 四、回归自检脚本（浏览器控制台片段）

```js
// ① 折叠项是否真的不可见（2.0）
const n = app.graph._nodes.find(x => x.type === 'JZL_MiniMaxMusicCaption');
['风格融合','拍号','情绪演变','段落结构'].forEach(k => {
  const w = n.widgets.find(x => x.name === k);
  console.log(k, w.type, w.hidden, w.options?.hidden);
});

// ② 面板提示词区是否可滚动
const root = document.querySelector(`[data-node-id="${nodeId}"]`);
const ed = root.querySelector('[contenteditable="true"]');
console.log(ed.clientHeight, ed.scrollHeight, getComputedStyle(ed).overflowY);

// ③ 是否有 JS 报错
window.addEventListener('error', e => console.log('ERR', e.message));
```

也可以直接看 `window.comfyAPI.app.app.ui.settings.getSettingValue("Comfy.VueNodes.Enabled")` 确认当前处于 2.0 模式。
