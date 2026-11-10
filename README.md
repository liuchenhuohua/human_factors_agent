# 人因工程个人助手

一个证据驱动的人因研究工作台。当前第一个可运行切片支持：

1. 创建人因研究项目；
2. 将痛点整理为结构化问题界定草案；
3. 通过 LangGraph 暂停工作流，等待人工审批；
4. 审批后保留项目状态与研究产物。

## 目录

```text
backend/   FastAPI、领域模型、LangGraph 工作流和 SQLite 存储
frontend/  Next.js 研究工作台
docs/      架构与产品决策
```

## 本地运行

### 后端

```powershell
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000
```

### 前端

```powershell
cd frontend
pnpm install
pnpm dev
```

浏览器打开 `http://localhost:3000`。前端默认连接 `http://localhost:8000`，可用
`NEXT_PUBLIC_API_BASE_URL` 修改。

## 验证

```powershell
cd backend
uv run pytest

cd ../frontend
pnpm lint
pnpm build
```

## 当前限制

- 问题界定使用本地规则实现，尚未接入真实 LLM；
- LangGraph 检查点当前保存在进程内，项目与产物保存在 SQLite；
- 文献检索、实验设计、数据分析与报告模块将在后续切片实现。

