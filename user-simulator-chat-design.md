# UserSimulator Chat 设计（执行备忘）

> 状态：设计稿，待实现。  
> 范围：**模拟用户（UserSimulator）+ 对话协议 + 评分分层**；被测 chatbot 仅定义薄适配器接口，不在本文展开具体实现。  
> 背景：当前 PersonaEval local chat 使用 `kickoff / respond / feedback` 三轮固定 JSON prompt（T0）；本文描述目标架构（T1+）。

---

## 1. 目标

| 能力 | 说明 |
|------|------|
| **Persona + Task 注入** | persona 描述与 task 内「用户侧隐藏剧本」分开注入 |
| **真多轮 + 渐进披露** | 使用 Chat API 的 `messages[]`，不靠每轮粘贴 transcript 的 JSON |
| **结构化行为约束** | function calling / tool schema 约束行为，聊天内容仍是自然语言 |
| **可扩展结束** | 主路径用 tool 结束；token（如 `###STOP###`）仅作 fallback |
| **多 SUT 复用** | 同一 UserSim 核心对接 RecAI、HTTP sidecar、未来其他 chatbot |
| **Multi-UserSim（未来）** | playground：多个 UserSim 共享频道，Orchestrator 调度 |
| **双轨评分** | persona 主观 self-report + owner 客观 verifier/metrics，不混为一谈 |

与仓库现有契约对齐：

- `application/tasks/interface/chatbot/README.md` — artifacts: transcript, application result, persona self-report, evaluation result
- `plan.md` — T1 chat：HTTP + `sessionId`、Harbor-native UserSimulator loop（preferred）

---

## 2. 非目标（本文阶段）

- 重写 web / computer-use 任务为 T1
- 用 PersonaEval `run_store` 替代 Harbor `jobs/` 作为 sign-off 输出
- 一步实现 multi-user playground（仅预留抽象）
- 替换 Harbor T3 的 `persona-claude-code` 等容器 agent

---

## 3. 总体架构

```text
┌─────────────────────────────────────────────────────────┐
│  UserSimSession（核心，与被测 chat 无关）                  │
│  ├── PersonaRender      ← persona YAML + Jinja 模板      │
│  ├── UserScenario       ← task hidden user instruction   │
│  ├── SimGuidelines      ← 渐进披露、风格、结束规则        │
│  ├── ChatMemory         ← messages[]（真多轮）           │
│  └── TurnDriver         ← LLM + tools（每步一个 user turn）│
└───────────────────────────┬─────────────────────────────┘
                            │ ChatSessionPort（协议）
                            ▼
              各种被测 chatbot（adapter 实现）
```

PersonaEval Cockpit、Harbor T1 driver、未来 playground **共用** `UserSimSession`；变化的是 `ChatSessionPort` 与 task 的 scenario 定义。

---

## 4. 注入：Persona 与 Task 分离

### 4.1 Persona（谁）

- **生产路径**：`persona/datasets/.../persona_*.yaml` + `persona_system.md.j2`（Harbor / personabench 已有）
- **Cockpit 路径**：catalog persona → 渲染为与 Harbor 相同的 system 文本；避免长期维持两套 `persona_system_prompt()` 拼接

参考：`environment/agents/personabench/agents/persona/templating.py`

### 4.2 UserScenario（隐藏剧本，agent 看不到）

从 task 拆出，**不要**把整份 agent 向 `instruction.md` 直接塞给 UserSim。

建议新增 `user_scenario.yaml`（或 `instruction.md` 内独立 `USER` 区块），示例：

```yaml
identity: "Financial manager, Bel Air MD, age 51"
goal: "Find a desk lamp under $80 with warm light for home office"
preferences:
  - "Dislikes overly techy products"
disclosure:
  mode: progressive          # progressive | upfront
  facts:
    - id: budget
      text: "Budget is around $75"
      reveal_when: asked_about_price
    - id: room
      text: "Room is north-facing, needs warm light"
      reveal_when: asked_about_use_case
style: "Brief, professional, doesn't volunteer extra detail"
stop_when: goal_satisfied    # 供 verifier 参考，不给 agent
```

### 4.3 System prompt 组装

```text
[SimGuidelines]     # 全局：一次一条、渐进披露、不编造、如何结束
[PersonaRender]     # Jinja 渲染 persona
[UserScenario]      # hidden goal + disclosure policy
```

全局 guidelines 可参考 tau-bench 的 `simulation_guidelines.md`（渐进披露、`###STOP###` 语义等），放在 repo 内单一来源（如 `persona_eval/sim_guidelines.md` 或 Jinja partial）。

---

## 5. 真多轮：`messages[]` 替代 JSON transcript 粘贴

**现状（T0）**：每轮 `complete_json(system, user)`，`user` 内手工拼 transcript。

**目标**：UserSim 维护 `messages[]`，每轮只 append 新 observation。

```text
messages = [
  { role: "system", content: assembled_system },
  ... 每轮 agent 回复后 append observation ...
  → LLM tool call → send_message / end_conversation
]
```

**发给被测 chat 的**只有 `send_message` 的自然语言，不是 JSON。

渐进披露由 **SimGuidelines + UserScenario.facts** 驱动；不再依赖 `kickoff` / `respond` 两套固定 user 模板。

---

## 6. Function calling：约束行为，不约束说话格式

### 6.1 最小 tool set（单 UserSim）

| Tool | 作用 |
|------|------|
| `send_message(message: str)` | 唯一进入 SUT transcript 的用户话 |
| `end_conversation(reason)` | `satisfied` \| `give_up` \| `out_of_scope` \| `transferred` |
| `reveal_fact(fact_id: str)` | 可选；更新内部披露状态，不直接发给 SUT |

### 6.2 每步流程

```text
1. 将 agent 回复 append 到 UserSim memory（observation）
2. LLM 带 tools 跑一步
3. send_message → 调用 ChatSessionPort + 写入 transcript
4. end_conversation → 结束 loop
5. reveal_fact → 仅更新内部 state，可再继续 send_message
```

OpenAI `response_format` / Anthropic tool use 优于 prompt 内 “strict JSON”。

### 6.3 结束信号

- **主路径**：`end_conversation` tool（可扩展 reason enum）
- **Fallback**：解析 `###STOP###` 等 token（兼容 tau 风格；不推荐作为唯一机制）

---

## 7. 与被测 chat 的边界：`ChatSessionPort`

UserSimulator **只依赖**此协议；RecAI、finance/medical sidecar、未来 SUT 均为 adapter。

```python
class ChatSessionPort(Protocol):
    session_id: str

    def send_user_message(self, text: str) -> AgentTurn:
        """返回 assistant_message, recommended_items, terminal_state, ..."""
```

`AgentTurn` 字段与现有 `session.run_turn_sync` 返回值对齐，便于从 `local/chatbot_eval.py` 迁移。

---

## 8. 对话主循环（单 UserSim）

```text
assemble system (Guidelines + Persona + UserScenario)
init messages[]

loop until max_turns or end_conversation:
  user_text = turn_driver.next_user_action(agent_turn)
  if end_conversation: break
  agent_turn = chat_port.send_user_message(user_text)
  append to transcript / events.jsonl

persona_self_report = turn_driver.final_self_report(transcript)
write persona_self_report.json

# 客观评分由 verifier 异步或同 job 内单独阶段完成
```

与 `persona_eval/runner.py` 中 `run_persona_eval` 等价，但去掉 JSON kickoff/respond，改为 tool loop。

---

## 9. 事后评分：双轨

| 轨道 | 产出方 | 内容 | 用途 |
|------|--------|------|------|
| **Persona self-report** | UserSim（对话结束后一次 LLM + schema） | constraint/preference/overall、clarifying questions 等 | 主观 UX、「这个人设觉得如何」 |
| **Objective eval** | Task verifier + SUT artifacts | transcript 合法性、业务 KPI、ground truth、pass^k | 应用 owner 客观度量 |

**原则**：self-report **不参与** objective pass/fail（避免 sim user 自评当 benchmark）。

Artifacts（与 chatbot interface 一致）：

- `transcript.json`
- `application_result.json`（SUT 侧）
- `persona_self_report.json`
- `objective_result.json` / Harbor verifier reward

---

## 10. 未来：Multi-UserSimulator Playground

```text
PlaygroundOrchestrator
  ├── UserSimSession A (persona A, scenario A)
  ├── UserSimSession B (persona B, scenario B)
  ├── Moderator（可选）
  └── SharedChannel
        ├── public_messages[]
        └── per_sim private state
```

**现在预留**：TurnDriver 输入为 `Observation`（谁说了什么），输出为 `Action`（send / end / reveal），不要写死「只有一个 user」。  
`ChatSessionPort` 可演进为 `ChannelPort.post(speaker_id, text)`。

---

## 11. 与现状对比

| 维度 | 现状（T0 local） | 目标 |
|------|------------------|------|
| 文件 | `persona_eval/user_simulator.py` | `persona_eval/user_sim/` 或重构同文件 |
| Persona | `Persona.context` 文本 + `GoalContext` 模板 | Jinja + YAML（对齐 Harbor） |
| Task | `sut_description` 一句 | `user_scenario.yaml` |
| 轮次 | kickoff + N×respond JSON + feedback JSON | messages[] + tools |
| 结束 | JSON `decision` | `end_conversation` tool |
| 评分 | feedback 问卷混在 sim 流程 | self-report 独立 artifact + verifier 客观分 |

---

## 12. 实施阶段

### Phase 0（当前）

- 保留 JSON UserSimulator 作 Cockpit smoke / T0
- 文档标注 W0/T0，不作 benchmark sign-off

### Phase 1 — UserSim v2 核心（优先）

- [ ] `messages[]` + tools（`send_message`, `end_conversation`）
- [ ] Persona 走 Jinja（复用 personabench loader/templates）
- [ ] 首个 `user_scenario.yaml`（建议：`recommender-agent_chat_api` 或 `example-chat-api_support_chatbot`）
- [ ] `ChatSessionPort` 协议 + 现有 local adapter 实现
- [ ] `persona_self_report.json` 独立一步；PersonaEval UI 读取不变
- [ ] 全局 `SimGuidelines` 单文件

### Phase 2 — Runtime 统一

- [ ] PersonaEval local chat 默认 v2
- [ ] Harbor T1 driver 复用同一 `UserSimSession`（HTTP sidecar + per-trial `sessionId`）
- [ ] 弃用 kickoff/respond JSON 模板（或仅测试保留）

### Phase 3 — Playground

- [ ] `PlaygroundOrchestrator` + multi UserSim
- [ ] UI：PersonaEval 新 surface 或 Harbor cockpit 扩展

---

## 13. 参考

- 仓库：`application/tasks/interface/chatbot/README.md`, `plan.md` § T1 chat
- 现状：`application/persona_eval/persona_eval/user_simulator.py`, `persona_eval/runner.py`
- Persona 渲染：`environment/agents/personabench/agents/persona/templating.py`
- 外部： [τ-bench](https://arxiv.org/abs/2406.12045), [tau2-bench UserSimulator](https://github.com/sierra-research/tau2-bench), [iEvaLM](https://aclanthology.org/2023.emnlp-main.621/)

---

## 14. 执行时首个 PR 建议范围

1. 新增 `persona_eval/user_sim/session.py`（或等价模块）：`UserSimSession` + tool loop  
2. 新增 `persona_eval/user_sim/port.py`：`ChatSessionPort`  
3. 新增 `application/tasks/.../user_scenario.yaml` ×1  
4. `deps.py` local chat 切到 v2 runner（feature flag：`MATRIX_USER_SIM_V2=1` 可选）  
5. 测试：`test_user_simulator.py` 扩 tool loop + mock port；不删旧测试直至 Phase 2  

不在首个 PR 做：multi-user playground、Harbor T1 接线、弃用 T0 JSON 路径。
