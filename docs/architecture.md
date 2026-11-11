# 软件架构

## 核心原则

- 研究产物是系统事实来源，对话历史不是；
- Agent 负责模糊推理，确定性代码负责校验、统计和持久化；
- 高影响状态转换必须经过人工审批；
- 模型输出必须先通过领域模型验证，再进入项目记录；
- 每次生成和人工修改都创建新版本，不覆盖历史版本。

## 问题界定工作流

```text
创建项目
   |
   v
identify_gaps ── RuleBasedProblemFramer / OpenAIProblemFramer
   |
   v
collect_clarifications ── interrupt: 等待用户回答
   |
   v
frame_problem
   |
   v
review_problem_frame ── interrupt: 等待人工判断
   |              |
   | approve      | revise
   v              v
完成         revise_problem_frame ──┐
                                    └── 返回 review
```

LangGraph 状态由 `SqliteSaver` 保存，项目领域产物由独立的 `SQLiteProjectStore`
保存。两类数据分离，因此更换工作流框架不会破坏研究产物。

## 关键模块

### `ProjectWorkflow`

外部接口只有启动、提交澄清、编辑、请求重生成、批准和查询。调用方不需要理解图节点、
检查点或 `Command(resume=...)`。

### `ProblemFramer`

当前有两个适配器：

- `RuleBasedProblemFramer`：无密钥、本地可运行、适合回归测试；
- `OpenAIProblemFramer`：通过 Responses 结构化输出生成严格领域模型。

模型供应商的 HTTP 细节被限制在 `OpenAIResponsesGenerator` 内，领域与工作流不依赖
供应商响应格式。

### `Project`

保存澄清问题与回答、当前问题界定、完整版本历史和审批历史。人工编辑也会生成带有
`generator=human` 元数据的新版本。

## 数据存储

```text
human_factors.db            项目和研究产物
workflow_checkpoints.sqlite LangGraph 检查点与暂停状态
```

SQLite 只用于本地开发和轻量部署。生产版本计划使用 PostgreSQL 项目存储与
`PostgresSaver`，但保持现有领域接口不变。

## 文献证据工作流

```text
已批准的问题界定
   |
   v
EvidencePlanner ── RuleBasedEvidencePlanner / OpenAIEvidencePlanner
   |
   v
review_search_plan ── interrupt: 人工编辑与确认
   |
   v
CrossrefLiteratureSearch
   |
   v
去重并保存 LiteratureCandidate
   |
   v
await_screening ── interrupt: 人工纳入或排除
```

`EvidenceWorkflow` 与 `ProjectWorkflow` 使用不同的 LangGraph thread id，并共享同一个
持久化 checkpointer。文献源位于 `LiteratureSearch` 接口后，目前的适配器是 Crossref。
筛选决定直接写入独立的 `evidence_reviews` 表，不修改已批准的问题界定。

## 下一模块

下一切片将对已纳入文献构建 `EvidenceItem`：研究对象、方法、样本、测量指标、结果、
局限、原文定位和证据等级。摘要或 PDF 内容必须遵守来源许可并保留引用位置。

