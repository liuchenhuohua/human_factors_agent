# 软件架构

## 核心原则

- 研究产物是系统事实来源，对话历史不是；
- Agent 负责模糊推理，确定性代码负责校验、统计和持久化；
- 高影响状态转换必须经过人工审批；
- 工作流状态只保存研究产物引用，不保存大型文件；
- 每个结论最终都必须能追溯到证据条目或分析运行。

## 当前切片

```text
Next.js 工作台
      |
      v
FastAPI 传输层
      |
      v
ProjectWorkflow (LangGraph)
  |               |
  v               v
ProblemFramer   Human approval interrupt
  |
  v
ProjectStore (SQLite)
```

`ProjectWorkflow` 是当前的外部工作流接口。调用方只需要提交项目输入或审批决定，
无需了解节点顺序、暂停恢复或问题界定实现。

## 计划模块

1. `evidence`：检索策略、证据条目、引用核验和证据综合；
2. `experiment`：变量、量表、实验设计、样本和伦理检查；
3. `analysis`：数据版本、质量报告、分析计划和隔离统计运行；
4. `recommendation`：发现、适用条件、置信度与建议；
5. `audit`：工作流轨迹、工具调用、产物版本和审批记录。

