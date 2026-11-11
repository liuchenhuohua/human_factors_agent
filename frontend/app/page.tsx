"use client";

import { FormEvent, useState } from "react";

type ProjectStage =
  | "intake"
  | "clarification_required"
  | "problem_frame_review"
  | "problem_frame_approved";

type ClarificationQuestion = {
  id: string;
  prompt: string;
  rationale: string;
};

type GenerationMetadata = {
  generator: string;
  model: string | null;
  prompt_version: string;
  generated_at: string;
};

type ProblemFrameContent = {
  research_question: string;
  human_factors_constructs: string[];
  candidate_outcomes: string[];
  assumptions: string[];
  uncertainties: string[];
};

type ProblemFrame = ProblemFrameContent & {
  generation: GenerationMetadata;
};

type Project = {
  id: string;
  stage: ProjectStage;
  intake: {
    name: string;
    pain_point: string;
    population: string;
    context: string;
    constraints: string[];
  };
  clarification_questions: ClarificationQuestion[];
  clarification_answers: Record<string, string>;
  problem_frame: ProblemFrame | null;
  problem_frame_version: number;
  review_history: Array<{
    action: "edited" | "revision_requested" | "approved";
    problem_frame_version: number;
    note: string | null;
  }>;
};

type SearchPlanContent = {
  query: string;
  keywords: string[];
  inclusion_criteria: string[];
  exclusion_criteria: string[];
  from_year: number | null;
  until_year: number | null;
  max_results: number;
};

type SearchPlan = SearchPlanContent & {
  generation: GenerationMetadata;
};

type LiteratureCandidate = {
  id: string;
  source: string;
  source_id: string;
  doi: string | null;
  title: string;
  authors: string[];
  publication_year: number | null;
  venue: string | null;
  url: string;
  work_type: string | null;
  screening_status: "unscreened" | "included" | "excluded";
  screening_reason: string | null;
};

type EvidenceReview = {
  id: string;
  project_id: string;
  stage: "search_plan_review" | "screening";
  search_plan: SearchPlan;
  candidates: LiteratureCandidate[];
};

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function Home() {
  const [project, setProject] = useState<Project | null>(null);
  const [evidence, setEvidence] = useState<EvidenceReview | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [revisionFeedback, setRevisionFeedback] = useState("");
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function requestProject(path: string, init?: RequestInit) {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiBase}${path}`, init);
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "请求失败，请检查后端状态。");
      }
      const updated: Project = await response.json();
      setProject(updated);
      return updated;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "发生未知错误");
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const constraints = String(form.get("constraints") ?? "")
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
    setAnswers({});
    setEditing(false);
    setEvidence(null);
    await requestProject("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: form.get("name"),
        pain_point: form.get("pain_point"),
        population: form.get("population"),
        context: form.get("context"),
        constraints,
      }),
    });
  }

  async function submitClarifications(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project) return;
    await requestProject(`/api/projects/${project.id}/clarifications`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers }),
    });
  }

  async function approveProblemFrame() {
    if (!project) return;
    await requestProject(`/api/projects/${project.id}/problem-frame/approve`, {
      method: "POST",
    });
  }

  async function requestRevision() {
    if (!project || revisionFeedback.trim().length < 3) return;
    const updated = await requestProject(
      `/api/projects/${project.id}/problem-frame/revise`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ feedback: revisionFeedback }),
      },
    );
    if (updated) setRevisionFeedback("");
  }

  async function saveEdit(content: ProblemFrameContent) {
    if (!project) return;
    const updated = await requestProject(
      `/api/projects/${project.id}/problem-frame`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(content),
      },
    );
    if (updated) setEditing(false);
  }

  async function requestEvidence(path: string, init?: RequestInit) {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiBase}${path}`, init);
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "文献工作流请求失败。");
      }
      const updated: EvidenceReview = await response.json();
      setEvidence(updated);
      return updated;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "发生未知错误");
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function startEvidenceReview() {
    if (!project) return;
    await requestEvidence(`/api/projects/${project.id}/evidence`, { method: "POST" });
  }

  async function approveSearchPlan(content: SearchPlanContent) {
    if (!project) return;
    await requestEvidence(`/api/projects/${project.id}/evidence/search-plan/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(content),
    });
  }

  async function screenCandidate(
    candidateId: string,
    status: "included" | "excluded",
    reason: string,
  ) {
    if (!project) return;
    await requestEvidence(
      `/api/projects/${project.id}/evidence/candidates/${candidateId}/screen`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, reason }),
      },
    );
  }

  return (
    <main>
      <header className="hero">
        <div>
          <span className="eyebrow">HUMAN FACTORS RESEARCH COPILOT</span>
          <h1>把现场痛点，变成可验证的人因问题。</h1>
          <p>Agent 先澄清关键信息，再生成可编辑、可追溯的问题界定。</p>
        </div>
        <div className="status-card">
          <span className="status-dot" />
          智能问题界定工作流
        </div>
      </header>

      <WorkflowStrip stage={project?.stage ?? "intake"} evidence={evidence} />

      <div className="workspace">
        <section className="panel intake-panel">
          <div className="panel-heading">
            <div>
              <span className="section-kicker">研究输入</span>
              <h2>描述你正在面对的问题</h2>
            </div>
            <span className="badge">阶段 1</span>
          </div>

          <form onSubmit={createProject}>
            <label>
              项目名称
              <input name="name" minLength={2} required placeholder="例如：夜班装配错误研究" />
            </label>
            <label>
              痛点或需求
              <textarea
                name="pain_point"
                minLength={10}
                required
                rows={5}
                placeholder="描述观察到的现象，不必急着给出原因……"
              />
            </label>
            <div className="field-grid">
              <label>
                目标人群
                <input name="population" required placeholder="例如：装配操作员" />
              </label>
              <label>
                使用或工作情境
                <input name="context" required placeholder="例如：夜间装配工位" />
              </label>
            </div>
            <label>
              已知约束 <small>每行一项，可选</small>
              <textarea name="constraints" rows={3} placeholder={"测试不超过 30 分钟\n无法中断生产线"} />
            </label>
            <button className="primary-button" disabled={loading} type="submit">
              {loading ? "工作流运行中…" : "启动问题界定"}
              <span>→</span>
            </button>
          </form>
        </section>

        <section className="panel result-panel">
          <div className="panel-heading">
            <div>
              <span className="section-kicker">Agent 产物</span>
              <h2>{resultTitle(project?.stage, evidence?.stage)}</h2>
            </div>
            {project && (
              <span className={`badge ${project.stage}`}>
                {stageLabel(project.stage)}
              </span>
            )}
          </div>

          {!project && <EmptyState />}

          {project?.stage === "clarification_required" && (
            <ClarificationForm
              questions={project.clarification_questions}
              answers={answers}
              loading={loading}
              onAnswer={(id, value) =>
                setAnswers((current) => ({ ...current, [id]: value }))
              }
              onSubmit={submitClarifications}
            />
          )}

          {project?.problem_frame && !editing && !evidence && (
            <ProblemFrameView
              frame={project.problem_frame}
              version={project.problem_frame_version}
            />
          )}

          {project?.problem_frame && editing && !evidence && (
            <ProblemFrameEditor
              frame={project.problem_frame}
              loading={loading}
              onCancel={() => setEditing(false)}
              onSave={saveEdit}
            />
          )}

          {project?.stage === "problem_frame_review" && !editing && !evidence && (
            <div className="review-controls">
              <div className="approval-box">
                <div>
                  <strong>需要你的专业判断</strong>
                  <p>可以直接编辑、提交修改意见，或批准当前版本。</p>
                </div>
                <button disabled={loading} onClick={approveProblemFrame}>
                  批准当前版本
                </button>
              </div>
              <div className="secondary-actions">
                <button className="secondary-button" onClick={() => setEditing(true)}>
                  直接编辑
                </button>
                <textarea
                  value={revisionFeedback}
                  onChange={(event) => setRevisionFeedback(event.target.value)}
                  rows={2}
                  placeholder="说明需要修改的方向，例如：进一步考虑操作经验的混杂影响"
                />
                <button
                  className="secondary-button"
                  disabled={loading || revisionFeedback.trim().length < 3}
                  onClick={requestRevision}
                >
                  根据意见重新生成
                </button>
              </div>
            </div>
          )}

          {project?.stage === "problem_frame_approved" && !evidence && (
            <div className="success-box evidence-entry">
              <span>
                问题界定第 {project.problem_frame_version} 版已批准，可以进入文献证据阶段。
              </span>
              <button disabled={loading} onClick={startEvidenceReview}>
                生成文献检索策略
              </button>
            </div>
          )}

          {evidence?.stage === "search_plan_review" && (
            <SearchPlanEditor
              plan={evidence.search_plan}
              loading={loading}
              onApprove={approveSearchPlan}
            />
          )}

          {evidence?.stage === "screening" && (
            <LiteratureScreening
              candidates={evidence.candidates}
              loading={loading}
              onScreen={screenCandidate}
            />
          )}

          {error && <div className="error-box">{error}</div>}
        </section>
      </div>
    </main>
  );
}

function WorkflowStrip({
  stage,
  evidence,
}: {
  stage: ProjectStage;
  evidence: EvidenceReview | null;
}) {
  const current = evidence || stage === "problem_frame_approved" ? 1 : 0;
  return (
    <section className="workflow-strip" aria-label="研究工作流">
      {["问题界定", "文献证据", "实验设计", "数据分析", "人因建议"].map(
        (label, index) => (
          <div className={index === current ? "workflow-step active" : "workflow-step"} key={label}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            {label}
          </div>
        ),
      )}
    </section>
  );
}

function ClarificationForm({
  questions,
  answers,
  loading,
  onAnswer,
  onSubmit,
}: {
  questions: ClarificationQuestion[];
  answers: Record<string, string>;
  loading: boolean;
  onAnswer: (id: string, value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="clarification-form" onSubmit={onSubmit}>
      <div className="form-intro">
        <span>Agent 发现了 {questions.length} 个关键信息缺口</span>
        <p>这些回答会进入项目记录，并直接影响研究问题和指标选择。</p>
      </div>
      {questions.map((question, index) => (
        <label className="question-card" key={question.id}>
          <span className="question-number">0{index + 1}</span>
          <span>{question.prompt}</span>
          <small>{question.rationale}</small>
          <textarea
            required
            rows={3}
            value={answers[question.id] ?? ""}
            onChange={(event) => onAnswer(question.id, event.target.value)}
            placeholder="输入你目前掌握的信息；不确定时也可以明确说明。"
          />
        </label>
      ))}
      <button className="primary-button" disabled={loading} type="submit">
        {loading ? "正在生成问题界定…" : "提交回答并生成草案"}
        <span>→</span>
      </button>
    </form>
  );
}

function EmptyState() {
  return (
    <div className="empty-state">
      <div className="empty-symbol">⌁</div>
      <h3>等待研究输入</h3>
      <p>Agent 会先提出澄清问题，再生成研究问题、候选构念、指标和不确定性。</p>
    </div>
  );
}

function ProblemFrameView({ frame, version }: { frame: ProblemFrame; version: number }) {
  return (
    <div className="artifact">
      <div className="artifact-meta">
        <span>版本 {version}</span>
        <span>
          {frame.generation.generator === "human"
            ? "人工编辑"
            : frame.generation.model ?? "本地规则"}
        </span>
        <span>提示版本 {frame.generation.prompt_version}</span>
      </div>
      <div className="research-question">
        <span>研究问题</span>
        <p>{frame.research_question}</p>
      </div>
      <ArtifactList title="候选人因构念" items={frame.human_factors_constructs} accent />
      <ArtifactList title="候选结果指标" items={frame.candidate_outcomes} />
      <ArtifactList title="当前假设" items={frame.assumptions} />
      <ArtifactList title="必须澄清的不确定性" items={frame.uncertainties} warning />
    </div>
  );
}

function ProblemFrameEditor({
  frame,
  loading,
  onCancel,
  onSave,
}: {
  frame: ProblemFrame;
  loading: boolean;
  onCancel: () => void;
  onSave: (content: ProblemFrameContent) => void;
}) {
  const [content, setContent] = useState<ProblemFrameContent>({
    research_question: frame.research_question,
    human_factors_constructs: frame.human_factors_constructs,
    candidate_outcomes: frame.candidate_outcomes,
    assumptions: frame.assumptions,
    uncertainties: frame.uncertainties,
  });

  function updateList(field: keyof Omit<ProblemFrameContent, "research_question">, value: string) {
    setContent((current) => ({
      ...current,
      [field]: value.split("\n").map((item) => item.trim()).filter(Boolean),
    }));
  }

  return (
    <div className="editor-form">
      <label>
        研究问题
        <textarea
          rows={4}
          value={content.research_question}
          onChange={(event) =>
            setContent((current) => ({ ...current, research_question: event.target.value }))
          }
        />
      </label>
      {(
        [
          ["human_factors_constructs", "候选人因构念"],
          ["candidate_outcomes", "候选结果指标"],
          ["assumptions", "当前假设"],
          ["uncertainties", "不确定性"],
        ] as const
      ).map(([field, label]) => (
        <label key={field}>
          {label} <small>每行一项</small>
          <textarea
            rows={4}
            value={content[field].join("\n")}
            onChange={(event) => updateList(field, event.target.value)}
          />
        </label>
      ))}
      <div className="editor-actions">
        <button className="secondary-button" onClick={onCancel}>取消</button>
        <button className="primary-button compact" disabled={loading} onClick={() => onSave(content)}>
          保存为新版本
        </button>
      </div>
    </div>
  );
}

function SearchPlanEditor({
  plan,
  loading,
  onApprove,
}: {
  plan: SearchPlan;
  loading: boolean;
  onApprove: (content: SearchPlanContent) => void;
}) {
  const [content, setContent] = useState<SearchPlanContent>({
    query: plan.query,
    keywords: plan.keywords,
    inclusion_criteria: plan.inclusion_criteria,
    exclusion_criteria: plan.exclusion_criteria,
    from_year: plan.from_year,
    until_year: plan.until_year,
    max_results: plan.max_results,
  });

  function updateList(
    field: "keywords" | "inclusion_criteria" | "exclusion_criteria",
    value: string,
  ) {
    setContent((current) => ({
      ...current,
      [field]: value.split("\n").map((item) => item.trim()).filter(Boolean),
    }));
  }

  return (
    <div className="search-plan-editor">
      <div className="form-intro">
        <span>检索策略需要确认</span>
        <p>关键词将发送到 Crossref。确认前可以修改检索式、年份和筛选标准。</p>
      </div>
      <label>
        英文检索式
        <textarea
          rows={4}
          value={content.query}
          onChange={(event) =>
            setContent((current) => ({ ...current, query: event.target.value }))
          }
        />
      </label>
      <label>
        关键词 <small>每行一项</small>
        <textarea
          rows={5}
          value={content.keywords.join("\n")}
          onChange={(event) => updateList("keywords", event.target.value)}
        />
      </label>
      <div className="field-grid">
        <label>
          起始年份
          <input
            type="number"
            min={1900}
            max={2100}
            value={content.from_year ?? ""}
            onChange={(event) =>
              setContent((current) => ({
                ...current,
                from_year: event.target.value ? Number(event.target.value) : null,
              }))
            }
          />
        </label>
        <label>
          截止年份
          <input
            type="number"
            min={1900}
            max={2100}
            value={content.until_year ?? ""}
            onChange={(event) =>
              setContent((current) => ({
                ...current,
                until_year: event.target.value ? Number(event.target.value) : null,
              }))
            }
          />
        </label>
      </div>
      <label>
        纳入标准 <small>每行一项</small>
        <textarea
          rows={5}
          value={content.inclusion_criteria.join("\n")}
          onChange={(event) => updateList("inclusion_criteria", event.target.value)}
        />
      </label>
      <label>
        排除标准 <small>每行一项</small>
        <textarea
          rows={5}
          value={content.exclusion_criteria.join("\n")}
          onChange={(event) => updateList("exclusion_criteria", event.target.value)}
        />
      </label>
      <label>
        最大候选数量
        <input
          type="number"
          min={5}
          max={50}
          value={content.max_results}
          onChange={(event) =>
            setContent((current) => ({
              ...current,
              max_results: Number(event.target.value),
            }))
          }
        />
      </label>
      <button
        className="primary-button"
        disabled={loading}
        onClick={() => onApprove(content)}
      >
        {loading ? "正在检索 Crossref…" : "确认策略并检索文献"}
        <span>→</span>
      </button>
    </div>
  );
}

function LiteratureScreening({
  candidates,
  loading,
  onScreen,
}: {
  candidates: LiteratureCandidate[];
  loading: boolean;
  onScreen: (
    candidateId: string,
    status: "included" | "excluded",
    reason: string,
  ) => void;
}) {
  const included = candidates.filter((item) => item.screening_status === "included").length;
  const excluded = candidates.filter((item) => item.screening_status === "excluded").length;
  return (
    <div className="screening-board">
      <div className="screening-summary">
        <span>候选 {candidates.length}</span>
        <span className="included">已纳入 {included}</span>
        <span className="excluded">已排除 {excluded}</span>
      </div>
      {candidates.length === 0 && (
        <div className="empty-state compact-empty">
          <h3>没有找到候选文献</h3>
          <p>当前切片会保留空结果；下一版将增加修改策略并重新检索。</p>
        </div>
      )}
      <div className="candidate-list">
        {candidates.map((candidate) => (
          <CandidateCard
            candidate={candidate}
            loading={loading}
            onScreen={onScreen}
            key={candidate.id}
          />
        ))}
      </div>
    </div>
  );
}

function CandidateCard({
  candidate,
  loading,
  onScreen,
}: {
  candidate: LiteratureCandidate;
  loading: boolean;
  onScreen: (
    candidateId: string,
    status: "included" | "excluded",
    reason: string,
  ) => void;
}) {
  const [reason, setReason] = useState(candidate.screening_reason ?? "");
  return (
    <article className={`candidate-card ${candidate.screening_status}`}>
      <div className="candidate-meta">
        <span>{candidate.publication_year ?? "年份未知"}</span>
        <span>{candidate.venue ?? candidate.work_type ?? "来源未知"}</span>
        {candidate.doi && <span>DOI {candidate.doi}</span>}
      </div>
      <h3>{candidate.title}</h3>
      <p>{candidate.authors.length ? candidate.authors.join("、") : "作者信息缺失"}</p>
      <a href={candidate.url} target="_blank" rel="noreferrer">查看来源 ↗</a>
      <textarea
        rows={2}
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        placeholder="记录纳入或排除理由"
      />
      <div className="candidate-actions">
        <button
          disabled={loading || reason.trim().length < 3}
          onClick={() => onScreen(candidate.id, "excluded", reason)}
        >
          排除
        </button>
        <button
          className="include-button"
          disabled={loading || reason.trim().length < 3}
          onClick={() => onScreen(candidate.id, "included", reason)}
        >
          纳入
        </button>
      </div>
    </article>
  );
}

function ArtifactList({
  title,
  items,
  accent = false,
  warning = false,
}: {
  title: string;
  items: string[];
  accent?: boolean;
  warning?: boolean;
}) {
  return (
    <div className="artifact-section">
      <h3>{title}</h3>
      <div className={accent ? "chips" : "artifact-list"}>
        {items.map((item) =>
          accent ? (
            <span className="chip" key={item}>{item}</span>
          ) : (
            <div className={warning ? "list-item warning" : "list-item"} key={item}>
              <span>{warning ? "!" : "·"}</span>{item}
            </div>
          ),
        )}
      </div>
    </div>
  );
}

function resultTitle(stage?: ProjectStage, evidenceStage?: EvidenceReview["stage"]) {
  if (evidenceStage === "search_plan_review") return "文献检索策略";
  if (evidenceStage === "screening") return "候选文献筛选";
  return stage === "clarification_required" ? "补充关键信息" : "问题界定草案";
}

function stageLabel(stage: ProjectStage) {
  return {
    intake: "准备中",
    clarification_required: "待补充",
    problem_frame_review: "待审批",
    problem_frame_approved: "已批准",
  }[stage];
}

