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

## 全文证据提取

```text
已纳入 LiteratureCandidate
   |
   v
校验 PDF ── 大小 / 类型 / 文件头
   |
   v
PdfTextExtractor ── PypdfTextExtractor
   |
   v
DocumentStorage ── LocalDocumentStorage
   |
   v
EvidenceExtractor ── RuleBasedEvidenceExtractor / OpenAIEvidenceExtractor
   |
   v
EvidenceItem（字段 + 页码原文）
   |
   v
人工编辑与批准
```

上传、解析、存储和结构化提取位于三个独立接口后。工作流只依赖这些接口，因此未来可以
把本地目录替换为对象存储、把 `pypdf` 替换为带 OCR 的解析器，而不改变 HTTP 或领域层。

`EvidenceItem` 保存研究问题、设计、参与者、样本量、任务场景、变量、量表、统计方法、
结果、效应量和局限。`source_excerpts` 必须包含页码；模型适配器还会验证原文片段确实
出现在对应页。未经过人工审批的条目保持 `pending_review`，不能作为后续实验设计的正式输入。

## 下一模块

下一切片将汇总已批准的 `EvidenceItem`，形成跨文献证据矩阵，识别一致结果、冲突、研究
空白和可迁移性限制，再将矩阵作为实验设计模块的唯一证据输入。

