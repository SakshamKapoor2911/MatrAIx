# MatrAIx Playground — 演示顺序手册（中文）

**用途：** 路演 · 内部分享 · 新人 tutorial · 同事上手  
**建议时长：** 22–28 分钟（含 batch 等待时间）  
**配套：** 英文视频旁白稿见 [DEMO_VIDEO_SCRIPT.md](./DEMO_VIDEO_SCRIPT.md)

---

## 演示前 Checklist

| 项 | 说明 |
|----|------|
| 环境 | Playground 已启动（Vite：`http://localhost:5173`；或 `run_demo.sh` 单源：`http://127.0.0.1:8765`） |
| API Key | `ANTHROPIC_API_KEY` 或 `LLM_API_KEY` 已设置 |
| Chatbot | RecAI task 卡片无 sidecar 报错（需要先 **Start sidecar**） |
| Web | Cocoa 任务提前 smoke 一次（首次 run 需要build Docker 镜像，这个比较耗时间 需要先做一下） |
| OS app | 可选：提前跑完一个 trial 作为备用录屏素材；demo 中不等待完整 run |
| 浏览器 | 全屏或 1440p，缩放 100%，light mode |

---

## 总览结构

```
Home（开场 + 使命）
  → Playground（主战场）
      → Survey：Quick run → Batch run → View job → Trial 下钻
      → Chatbot：Quick run → Filtered batch → View job → Trial 下钻
      → Web（Cocoa）：Quick run → Step 回放
      → OS app：平台介绍 + 鼓励上手（不等待完整 run）
  → Runs（实验归档）
  → Persona World（Persona 库浏览）
  → Home（收尾 + Slogan）
```

---

## 第一幕：Home 开场（~2 min）

### 操作

1. 打开 Playground，停留在 **Home**
2. 指顶部导航：**Home · Playground · Runs · Persona World**
3. 指 hero 区：`8.3B` personas、`Planetary-scale digital humans`
4. 点击 **Playground** 进入

### 讲解要点

- 大多数团队是在产品上线**之后**才了解用户行为；MatrAIx 问的是：**能否在真实用户接触产品之前，就用结构化行为证据完成评测？**
- 三个栏目分工：
  - **Playground** = 开发试验场，配置并发起仿真
  - **Runs** = 实验结果、cohort 报告、per-persona 证据归档
  - **Persona World** = 浏览 persona 库、设计 study cohort
- 今天走完整条 evaluation 链路，从单次 smoke test 到分布式 cohort batch

---

## 第二幕：Playground 总览（~1 min）

### 操作

1. 进入 Playground，指右上角 **Application type** 四个 tab

### 讲解要点

| 类型 | 一句话 |
|------|--------|
| Survey | 固定问卷 — 产品反馈、概念测试 |
| Chatbot | 多轮对话 — 推荐系统、客服 bot |
| Web | 真实浏览器任务 — 导航、比较、决策 |
| OS app | 原生应用仿真 — Linux / macOS / iOS |

- 四种类型共享同一套 configure → run → score → report 管线；交互面和 metrics 不同，科学严谨性一致
- 从 **Survey** 开始，最快跑通完整 loop

---

## 第三幕：Survey — Quick Run（~4 min）

### 操作

1. 选 **Survey**
2. 指 **Persona model** 下拉 — 为 persona 指定 LLM 引擎（persona = 实验对象，model = 可控变量）
3. 介绍三种 **persona 采样模式**（左侧 rail）：
   - **Quick pick** — 手动选 1 个或多个，快速迭代
   - **Random sample** — 随机抽样，可加 filter
   - **Stratified** — 按维度分层均衡抽样
4. 保持 **Quick pick**，选 1 个 persona（如 `0042`）
5. 选 task：**Product concept survey / FocusLoop**（`example-survey_product-feedback`）
6. 点击 **Run eval**，等待完成
7. 看 live trajectory + **scorecard / Evaluation** 指标
8. 点击 **Reset**

### 讲解要点

- Persona = 身份档案（demographics、偏好、来源）；Persona model = 驱动它的 LLM
- 二者分离对研究有意义：可以 ablate model、换 engine、在 cohort 间保持 persona 恒定
- Evaluation metrics 由领域专家为**该任务**设计 — coverage、persona alignment、friction 等 — 不是通用 LLM 分数
- 核心研究价值：**结构化行为证据**，不是 vibe check

---

## 第四幕：Survey — Batch Run（~5 min，含等待）

### 操作

1. 切到 **Random sample**
2. **不设置 filter**，但点开 filter 弹窗展示维度（age、source、occupation 等），然后关闭
3. **Sample size → 24**
4. **Parallel → 8**
5. 点击 **Run eval**
6. 指 **batch trial grid**：24 格，运行中转动，完成变绿，失败变红
7. 全部完成后点 **View job**

### 讲解要点

- Batch = 一次 job，N 个 trial（每个 persona 一个）
- **Parallel** = 同时并发几个 trial，不是总 persona 数；24 人 × parallel 8 = 大幅缩短墙钟时间
- 实时 grid 让 batch 进度可见 — 适合 demo，更适合生产
- Filter 词汇表在 Store 和 Eval 采样间复用 — 一套 cohort 定义，处处可用

---

## 第五幕：Survey — Job 报告 & Trial 下钻（~3 min）

### 操作

1. 在 **Runs → Job detail** 页，指 cohort 级 aggregation 指标（挑 2–3 个讲）
2. 往下滚到 trial 列表
3. 点开 **某一个 trial**，看该 persona 的 submission / trajectory / verifier / 单项分数
4. 返回 Playground（顶栏 Playground）

### 讲解要点

- Job 层 = cohort 整体表现（分布、汇总）
- Trial 层 = 每个 persona 的具体行为证据 — 研究员引用的层，产品团队行动的层
- 完整的 **persona evaluation** 闭环：配置 → 运行 → cohort insight → per-subject evidence

---

## 第六幕：Chatbot — Quick Run（~3 min）

### 操作

1. Application type → **Chatbot**
2. 选 **RecAI / recommender-agent** task
3. **先不跑** — 演示上下文：
   - 点 persona card 上的 **info 图标** → persona 属性
   - 点 task card 上的 **info 图标** → task instruction
4. **Quick pick**，选 1 个 persona
5. **Run eval** → 看多轮 chat trajectory + scorecard
6. **Reset**

### 讲解要点

- **Who × What**：persona 属性 + task instruction = 实验设计，在花 API call 之前就可见
- Chatbot metrics 关注对话质量、推荐相关性、persona 一致性 — 为对话场景定义，不是从 survey 借来的

---

## 第七幕：Chatbot — Filtered Batch（~4 min，含等待）

### 操作

1. 切 **Random sample**
2. **打开 filter**，设一个具体 cohort 条件（如特定 source / age band — 按当天数据选能出 4 个结果的 filter）
3. **Sample size → 4**，**Parallel → 4**
4. **Run eval** → 等待 → **View job**
5. 看 RecAI cohort 评测报告
6. 点开 **一个 trial** → 完整 **chat history** 和单次用户行为结果
7. 返回 cockpit

### 讲解要点

- Filtered batch = 有研究意图的 cohort
- Aggregate 告诉你 scale 上发生了什么；trial report 告诉你为什么
- Transcript 是指标背后的原始证据

---

## 第八幕：Web — Cocoa Quick Run（~3 min）

### 操作

1. Application type → **Web**
2. 选 **Cocoa plan-choice** task（pythonanywhere.com 定价页）
3. **Quick pick**，1 个 persona
4. **Run eval**
5. 完成后指 **step 列表**，点一步做 **回放**
6. 指最终 decision output + scorecard

### 讲解要点

- Web 模式支持多种交互栈（Playwright、browser-use、Cocoa、CUA）— cockpit 抽象了栈，选 task 即可
- 得到的不是最终答案，是 **steps** — 导航、点击、每步推理
- Step replay = 可审计的浏览行为证据，支撑产品决策也支撑研究发表

---

## 第九幕：OS App — 原生应用 Playground（~2 min）★ 新增

### 操作

1. Application type → **OS app**
2. 指 task picker 中按平台分类的任务（Linux / macOS / iOS）
3. 展示 setup 界面：persona 选择、task card、Run eval 按钮 — **可不实际点击 Run**，或展示一个预跑完的 run 截图/录屏
4. 口头介绍三个平台，邀请观众会后自己试

### 讲解要点

- **OS app playground** 是 PersonaBench 面向原生应用环境的仿真面
- 支持三种平台：
  - **Linux** — 容器化桌面工作流
  - **macOS** — 原生 macOS 应用 computer-use 仿真
  - **iOS** — 移动端设置、权限、in-app 流程
- 每个 task 定义真实原生场景（如通知偏好设置、系统设置导航）— persona 不是填表或聊天，而是像真实用户一样操作 UI
- Playground 工作流完全一致：采样 → 配置并行 → 启动；但 OS app run **更重** — 可能需要平台专属 runtime、更长 timeout
- **Demo 中不等待完整 run 结束。** 单次 trial 可能数分钟，这种深度正是 native app 评测的价值所在 — 也是过早 ship 代价最高的地方
- **鼓励观众会后自己跑一个：** 选一个平台、指定 persona、看 digital human 如何在真实应用环境中导航 — 这是最好的 firsthand 体验

### 话术参考

> "这是 OS app 类型的 playground。我们支持 Linux、macOS、iOS 三种不同平台的 native 应用系统测试。和前面几种类型一样，你可以在这里选 persona、选 task、跑 evaluation — 但 OS app 的 run 会更花时间，因为它要真实地操作原生 UI。这次 demo 我们不在这里等它跑完，但我非常鼓励大家会后自己上手体验一次。"

---

## 第十幕：Runs 栏目（~2 min）

### 操作

1. 顶栏点 **Runs**
2. 指 job 列表：刚才的 survey batch、chatbot batch 都在
3. 演示 **搜索** 或按时间浏览
4. 指 app-type 标签区分 survey / chatbot / web / os-app

### 讲解要点

- 一次 batch run = 一条 job；一个 job 里有多个 trial = 多个 persona
- Runs 不是 log viewer，是每次 cockpit session 背后的 **持久研究记录**
- 团队可回溯、对比实验条件、分享证据，不必重跑

---

## 第十一幕：Persona World（~2 min）

### 操作

1. 顶栏点 **Persona World**
2. 简述 persona 来源：Nemotron / OASIS / PRIMEX / PersonaHub 及合成 persona
3. 演示 **搜索** 或 **filter** 某一类属性 cohort
4. 展示筛选后的 persona grid
5. 可选：点开 persona detail drawer

### 讲解要点

- Store 既是探索库，也是 cohort 设计入口
- Filter 与 Playground 采样 filter 同一套逻辑
- Persona 质量是一切下游行为可信度的基础

---

## 第十二幕：Home 收尾（~1 min）

### 操作

1. 点 logo 或 **Home** 回到首页
2. 指 hero 文案，做 closing

### 收尾话术

**中文：**

> 今天我们走了 MatrAIx 的完整 loop：在 Playground 配置四种应用类型的仿真，从单次 smoke test 到分布式 cohort batch；在 Runs 读 cohort 报告和 per-persona 证据；在 Persona World 设计 study population。
>
> 研究价值很直接：**用结构化行为证据替代猜测** — 在真实用户接触产品之前。
>
> 使命更大：建设 **planetary-scale digital human simulation** 的基础设施 — 让每个团队都能以软件应有的速度，对 realistic users 完成产品评测。
>
> **MatrAIx** — 在真实用户之前，先模拟用户。

**English（如需双语收尾）：**

> *Simulate users across your applications — before real users do. Planetary-scale digital humans.*

---

## 关键参数速查

| 场景 | Persona 模式 | 人数 | Parallel | Filter | 是否等待 |
|------|-------------|------|----------|--------|----------|
| Survey quick | Quick pick | 1 | — | 无 | 等 |
| Survey batch | Random sample | 24 | 8 | 无（只展示 UI） | 等 |
| Chatbot quick | Quick pick | 1 | — | 无 | 等 |
| Chatbot batch | Random sample | 4 | 4 | **有** | 等 |
| Web Cocoa quick | Quick pick | 1 | — | 无 | 等 |
| OS app | Quick pick 或展示 | 1 | — | 无 | **不等** |

---

## 常见问题预案

| 情况 | 处理 |
|------|------|
| Survey/Chatbot batch 等待太久 | 调低人数（如 survey 改 12×4），或提前跑完 |
| RecAI sidecar 未启动 | 点 Start sidecar，等 health 变绿 |
| Web 首次 Docker build | 提前 smoke；口头说 "first run builds the image" |
| Filter 筛不出 4 人 | 换宽松条件，或改 sample size |
| 某个 trial 失败 | 指红色格："failures are first-class — visible in the job report" |
| OS app 观众问为什么不跑 | "单次 trial 数分钟，深度是特性；会后欢迎自己试" |
| 时间不够 | 砍掉 Chatbot batch，保留 Survey batch + Web + OS app 介绍 |

---

## 时间分配参考

| 幕 | 内容 | 建议时长 |
|----|------|----------|
| 1 | Home 开场 | 2 min |
| 2 | Playground 总览 | 1 min |
| 3 | Survey quick | 4 min |
| 4 | Survey batch（含等待） | 5 min |
| 5 | Survey job + trial | 3 min |
| 6 | Chatbot quick | 3 min |
| 7 | Chatbot batch（含等待） | 4 min |
| 8 | Web Cocoa | 3 min |
| 9 | **OS app playground** | **2 min** |
| 10 | Runs | 2 min |
| 11 | Persona World | 2 min |
| 12 | Home 收尾 | 1 min |
| | **合计** | **~32 min**（含等待；压缩 batch 可压到 ~22 min） |
