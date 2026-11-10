"use client";

import { FormEvent, useState } from "react";

type ProblemFrame = {
  research_question: string;
  human_factors_constructs: string[];
  candidate_outcomes: string[];
  assumptions: string[];
  uncertainties: string[];
};

type Project = {
  id: string;
  stage: "intake" | "problem_frame_review" | "problem_frame_approved";
  intake: {
    name: string;
    pain_point: string;
    population: string;
    context: string;
    constraints: string[];
  };
  problem_frame: ProblemFrame | null;
};

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function Home() {
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    const constraints = String(form.get("constraints") ?? "")
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);

    try {
      const response = await fetch(`${apiBase}/api/projects`, {
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
      if (!response.ok) throw new Error("项目创建失败，请检查输入和后端状态。");
      setProject(await response.json());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "发生未知错误");
    } finally {
      setLoading(false);
    }
  }

  async function approveProblemFrame() {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${apiBase}/api/projects/${project.id}/problem-frame/approve`,
        { method: "POST" },
      );
      if (!response.ok) throw new Error("审批失败，工作流可能已发生变化。");
      setProject(await response.json());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "发生未知错误");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <header className="hero">
        <div>
          <span className="eyebrow">HUMAN FACTORS RESEARCH COPILOT</span>
          <h1>把现场痛点，变成可验证的人因问题。</h1>
          <p>从问题界定开始，逐步连接文献、实验、数据、结论与人因建议。</p>
        </div>
        <div className="status-card">
          <span className="status-dot" />
          首个工作流已就绪
        </div>
      </header>

      <section className="workflow-strip" aria-label="研究工作流">
        {["问题界定", "文献证据", "实验设计", "数据分析", "人因建议"].map(
          (label, index) => (
            <div className={index === 0 ? "workflow-step active" : "workflow-step"} key={label}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              {label}
            </div>
          ),
        )}
      </section>

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
              {loading ? "工作流运行中…" : "生成问题界定草案"}
              <span>→</span>
            </button>
          </form>
        </section>

        <section className="panel result-panel">
          <div className="panel-heading">
            <div>
              <span className="section-kicker">Agent 产物</span>
              <h2>问题界定草案</h2>
            </div>
            {project && <span className={`badge ${project.stage}`}>{stageLabel(project.stage)}</span>}
          </div>

          {!project?.problem_frame ? (
            <div className="empty-state">
              <div className="empty-symbol">⌁</div>
              <h3>等待研究输入</h3>
              <p>Agent 将在这里展示研究问题、候选构念、指标和不确定性。</p>
            </div>
          ) : (
            <ProblemFrameView frame={project.problem_frame} />
          )}

          {project?.stage === "problem_frame_review" && (
            <div className="approval-box">
              <div>
                <strong>需要你的判断</strong>
                <p>批准后，工作流才能进入文献证据阶段。</p>
              </div>
              <button disabled={loading} onClick={approveProblemFrame}>
                批准问题界定
              </button>
            </div>
          )}

          {project?.stage === "problem_frame_approved" && (
            <div className="success-box">问题界定已批准。下一切片将接入文献证据工作流。</div>
          )}

          {error && <div className="error-box">{error}</div>}
        </section>
      </div>
    </main>
  );
}

function ProblemFrameView({ frame }: { frame: ProblemFrame }) {
  return (
    <div className="artifact">
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

function stageLabel(stage: Project["stage"]) {
  return {
    intake: "准备中",
    problem_frame_review: "待审批",
    problem_frame_approved: "已批准",
  }[stage];
}

