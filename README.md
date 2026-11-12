# 人因工程个人助手

一个证据驱动的人因研究工作台。目前已完成“智能问题界定”、文献检索筛选和首个全文证据闭环：

1. 创建人因研究项目；
2. Agent 识别信息缺口并提出 3–5 个澄清问题；
3. 根据回答生成结构化问题界定；
4. 用户可以编辑、反馈重生成或批准；
5. 所有版本、审批记录和 LangGraph 暂停状态都可持久恢复。
6. 从已批准的问题界定生成可编辑的文献检索策略；
7. 通过 Crossref 公共接口检索并去重候选文献；
8. 人工纳入或排除候选文献，并强制记录筛选理由。
9. 为已纳入文献上传带可选择文字的 PDF；
10. 按页提取全文并生成结构化 `EvidenceItem`；
11. 人工修订证据字段、核对原文页码并批准为可用证据。
12. 对每条已批准证据生成可编辑的研究质量评价草案；
13. 人工审核设计、样本、测量、分析、偏倚风险和直接性；
14. 仅使用已批准证据与评价生成跨文献矩阵；
15. 记录一致发现、冲突、证据缺口、可迁移性和使用警示，并由人工批准。

## 技术结构

```text
frontend/  Next.js 研究工作台
backend/   FastAPI、领域模型、LangGraph 工作流和 SQLite 适配器
docs/      架构说明
```

默认使用本地规则适配器，不需要模型密钥。配置 `HFA_LLM_API_KEY` 后，后端会启用
OpenAI Responses 结构化输出，并记录模型、提示版本和生成时间。

## 本地运行

### 后端

```powershell
cd backend
Copy-Item .env.example .env
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000
```

如需启用模型，在 `backend/.env` 中填写：

```dotenv
HFA_LLM_API_KEY=your-key
HFA_LLM_MODEL=gpt-6-luna
```

`.env` 已被 Git 忽略，不要把密钥写入 `.env.example`。

Crossref 无需密钥即可使用。若希望进入官方 polite pool，可以配置自己的联系邮箱：

```dotenv
HFA_CROSSREF_MAILTO=your-email@example.com
```

PDF 默认保存在 `backend/data/uploads`，单个文件上限为 25 MB、250 页。可以通过
`HFA_DOCUMENT_STORAGE_PATH`、`HFA_MAX_PDF_UPLOAD_MB` 和 `HFA_MAX_PDF_PAGES`
调整。上传目录已被 Git 忽略。

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

后端测试包括：规则实现、完整 HTTP 流程、编辑与重生成、跨进程检查点恢复、
OpenAI 严格 JSON Schema、Crossref 元数据解析与去重、PDF 证据提取，以及质量评价、
跨文献矩阵和综合审批。

## 当前限制

- SQLite 检查点适合本地开发，生产环境应迁移至 PostgreSQL；
- 尚未实现用户身份、项目权限和并发编辑；
- 当前 PDF 解析只支持包含可选择文字的全文，扫描件需要先进行 OCR；
- 无模型密钥时使用保守规则提取器，只预填可核验片段和明显样本量，其余字段需人工填写；
- 当前每条候选文献只允许关联一个 PDF，尚未提供替换或删除操作；
- 尚未实现检索策略版本历史、重新检索和批量筛选；
- 质量评价是通用的人因研究辅助框架，不替代针对特定研究设计的正式 GRADE、RoB 2、ROBINS-I 或其他专门工具；
- 当前综合为叙述性综合，不执行元分析，也不会合并不兼容的效应量；
- 实验设计和数据分析仍是后续里程碑；
- 自动化测试不会调用真实模型，真实调用需要单独的集成测试环境。

