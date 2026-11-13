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

## 证据评价与跨文献综合

```text
已批准 EvidenceItem
   |
   v
EvidenceAppraiser ── RuleBased / OpenAI
   |
   v
人工审核 EvidenceAppraisal
   |
   v
EvidenceSynthesizer ── 只读取已批准的证据与评价
   |
   +── 确定性 EvidenceMatrixRow
   |
   └── 一致发现 / 冲突 / 缺口 / 可迁移性 / 警示
           |
           v
       人工审核 EvidenceSynthesis
```

单篇质量评价覆盖设计适切性、样本充分性、测量有效性、分析适切性、偏倚风险和对当前问题
的直接性。这是通用的人因研究辅助评价，不宣称替代 GRADE、RoB 2 或其他特定方法。

矩阵行由确定性代码生成，模型只参与待审核的叙述性综合。领域模型要求矩阵恰好包含每条
已批准证据一次；跨研究结论至少引用两条已批准证据。任何 EvidenceItem 或 Appraisal 被
修改后，旧评价或综合自动失效，从而避免后续实验设计读取过期结论。

## 实验设计工作流

```text
已批准 EvidenceSynthesis
   |
   v
ExperimentDesigner ── RuleBasedExperimentDesigner / OpenAIExperimentDesigner
   |
   v
ExperimentPlan
   |── 假设与证据引用
   |── 设计类型、条件与变量操作化
   |── 被试与招募
   |── 功效分析输入（不包含模型猜测的样本量）
   |── 流程、随机化、顺序平衡
   |── 统计计划、伦理与安全
   v
人工编辑与批准
```

`ExperimentWorkflow` 只接受已批准的综合，并校验所有假设、变量和关键设计决策引用的
`evidence_item_ids` 均来自该综合。批准前必须确定设计类型、效应量指标、预期效应量、
显著性水平和目标检验效能。最终样本量不由模型生成，而是在实验方案批准后交给确定性
统计适配器计算。

实验方案保存源综合的内容哈希。证据综合被修改、撤销或替换后，已有方案会被标记为
`stale`，必须根据最新证据重新生成，不能继续审批。

## 研究执行准备

```text
已批准 ExperimentPlan
   |
   +── StatsmodelsPowerCalculator
   |      |── 独立样本 t / 配对样本 t / 平衡单因素 ANOVA
   |      |── Fisher z 相关分析近似
   |      └── 脱落调整 + 敏感性场景 + 计算包版本
   |
   └── ExperimentDataContractBuilder
          |── 系统字段 + 实验变量字段
          |── 类型 / 编码 / 单位 / 时点 / 来源 / 敏感性 / 校验规则
          └── 人工审核后输出 UTF-8 CSV 模板
```

`PreparationWorkflow` 只接受已批准且未过期的实验方案。统计计算位于 `PowerCalculator`
接口后，当前适配器使用 Statsmodels，并用 SciPy 的正态分布函数实现相关分析的 Fisher z
近似；请求、结果、方法和依赖版本一同保存，使结果可以复核。计算失败会显式返回错误，
不会回退到模型估算。

数据契约由确定性构建器把实验变量映射为采集字段，同时加入参与者标识、条件、试次和
记录时间等系统字段。只有人工批准且仍与当前实验方案一致的数据契约才能导出 CSV 模板。
功效分析和数据契约都保存实验方案内容哈希；方案一旦变化，两者会标记为 `stale`。

## 数据接入与质量控制

```text
已批准 DataContract
   |
   v
DatasetWorkflow.upload
   |── 文件格式与大小校验
   |── CsvDatasetValidator：契约、逐行值、联合主键、质量摘要
   |── LocalDatasetStorage：不可变原始 CSV
   └── SQLiteDatasetStore：DatasetVersion + DataQualityReport
           |
           v
       人工质量复核
       |           |
       | approve   | revise
       v           v
 analysis_ready  needs_revision
```

`DatasetWorkflow` 的上传接口隐藏解析、验证、持久化和版本分配。每次成功上传都产生新的
`DatasetVersion`，保存原始文件 SHA-256、来源契约 ID 和契约内容哈希。CSV 验证器只执行
可确定复现的规则：字段集合、字段数量、必填值、数据类型、分类编码、数值上下界、联合
主键重复，以及字段级缺失率和不同值数量。质量问题保留出现次数和最多 20 个 CSV 行号。

有错误的数据集保持 `validation_failed`，不能批准进入分析；零错误版本仍需人工复核后
才成为 `analysis_ready`。数据契约内容变化或失效时，相关数据集被标记为 `stale`，活动
数据集引用同时清除，但不可变原始文件仍可下载用于审计。

## 下一模块

下一切片将根据已批准实验方案和分析就绪数据集生成可审核的统计执行计划，确定性运行
描述统计、假设检验、效应量与诊断，并把每个结论绑定到数据版本和分析代码版本。

