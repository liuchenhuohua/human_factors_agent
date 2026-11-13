"use client";

import { FormEvent, useState, type ReactNode } from "react";

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

type EvidenceDocument = {
  id: string;
  candidate_id: string;
  filename: string;
  byte_size: number;
  sha256: string;
  page_count: number;
};

type SourceExcerpt = {
  page_number: number;
  text: string;
  relevance: string;
};

type EvidenceItemContent = {
  research_questions: string[];
  study_design: string | null;
  participants: string | null;
  sample_size: number | null;
  task_context: string | null;
  independent_variables: string[];
  dependent_variables: string[];
  control_variables: string[];
  measures: string[];
  statistical_methods: string[];
  key_findings: string[];
  effect_sizes: string[];
  limitations: string[];
  source_excerpts: SourceExcerpt[];
};

type EvidenceItem = EvidenceItemContent & {
  id: string;
  candidate_id: string;
  document_id: string;
  status: "pending_review" | "approved" | "needs_revision";
  generation: GenerationMetadata;
  reviewer_note: string | null;
};

type ReviewStatus = "pending_review" | "approved" | "needs_revision";
type AppraisalConcern = "low" | "some_concerns" | "high" | "unclear";
type AppraisalConfidence = "high" | "moderate" | "low" | "unclear";

type AppraisalJudgment = {
  concern: AppraisalConcern;
  rationale: string;
};

type EvidenceAppraisalContent = {
  design_appropriateness: AppraisalJudgment;
  sample_adequacy: AppraisalJudgment;
  measurement_validity: AppraisalJudgment;
  analysis_adequacy: AppraisalJudgment;
  bias_risk: AppraisalJudgment;
  directness: AppraisalJudgment;
  overall_confidence: AppraisalConfidence;
  strengths: string[];
  concerns: string[];
};

type EvidenceAppraisal = EvidenceAppraisalContent & {
  id: string;
  evidence_item_id: string;
  status: ReviewStatus;
  generation: GenerationMetadata;
  reviewer_note: string | null;
};

type EvidenceMatrixRow = {
  evidence_item_id: string;
  candidate_id: string;
  citation: string;
  population_and_context: string;
  design_and_sample: string;
  exposures_or_interventions: string[];
  outcomes_and_measures: string[];
  findings_and_effects: string[];
  limitations: string[];
  appraisal_confidence: AppraisalConfidence;
};

type SynthesisClaim = {
  statement: string;
  evidence_item_ids: string[];
  confidence: AppraisalConfidence;
  rationale: string;
};

type EvidenceSynthesisContent = {
  matrix: EvidenceMatrixRow[];
  consistent_findings: SynthesisClaim[];
  conflicting_findings: SynthesisClaim[];
  evidence_gaps: string[];
  transferability_notes: string[];
  cautions: string[];
};

type EvidenceSynthesis = EvidenceSynthesisContent & {
  id: string;
  status: ReviewStatus;
  generation: GenerationMetadata;
  reviewer_note: string | null;
};

type EvidenceReview = {
  id: string;
  project_id: string;
  stage: "search_plan_review" | "screening";
  search_plan: SearchPlan;
  candidates: LiteratureCandidate[];
  documents: EvidenceDocument[];
  evidence_items: EvidenceItem[];
  appraisals: EvidenceAppraisal[];
  synthesis: EvidenceSynthesis | null;
};

type ExperimentStatus = "pending_review" | "approved" | "needs_revision" | "stale";
type ExperimentDesignType =
  | "undecided"
  | "within_subjects"
  | "between_subjects"
  | "mixed"
  | "quasi_experimental";
type VariableRole =
  | "independent"
  | "dependent"
  | "control"
  | "covariate"
  | "manipulation_check";

type ExperimentPlanContent = {
  title: string;
  objective: string;
  design_type: ExperimentDesignType;
  hypotheses: Array<{
    statement: string;
    null_hypothesis: string;
    direction: "non_directional" | "increase" | "decrease";
    primary_outcome: string;
    evidence_item_ids: string[];
  }>;
  conditions: Array<{ name: string; description: string }>;
  variables: Array<{
    name: string;
    role: VariableRole;
    operational_definition: string;
    measurement_method: string;
    measurement_timing: string;
    evidence_item_ids: string[];
  }>;
  participant_plan: {
    target_population: string;
    inclusion_criteria: string[];
    exclusion_criteria: string[];
    recruitment_strategy: string;
    sampling_method: string;
  };
  sample_size_planning: {
    planned_primary_test: string;
    effect_size_metric: string | null;
    expected_effect_size: number | null;
    effect_size_basis: string;
    alpha: number | null;
    target_power: number | null;
    attrition_allowance: number | null;
    calculation_note: string;
  };
  randomization_plan: string;
  counterbalancing_plan: string;
  procedure: Array<{
    order: number;
    name: string;
    description: string;
    duration_minutes: number | null;
    data_collected: string[];
  }>;
  analysis_plan: Array<{
    hypothesis_index: number;
    method: string;
    outcome: string;
    predictors: string[];
    assumptions_to_check: string[];
    missing_data_strategy: string;
    multiplicity_strategy: string;
  }>;
  ethics_and_safety: string[];
  assumptions: string[];
  uncertainties: string[];
  evidence_grounded_decisions: Array<{
    decision: string;
    rationale: string;
    evidence_item_ids: string[];
  }>;
};

type ExperimentPlan = ExperimentPlanContent & {
  id: string;
  project_id: string;
  source_synthesis_id: string;
  status: ExperimentStatus;
  generation: GenerationMetadata;
  reviewer_note: string | null;
};

type PreparationStatus = "pending_review" | "approved" | "needs_revision" | "stale";
type PowerTestType = "independent_t" | "paired_t" | "one_way_anova" | "correlation";

type PowerAnalysisRequest = {
  test_type: PowerTestType;
  effect_size: number;
  alpha: number;
  target_power: number;
  alternative: "two-sided" | "larger" | "smaller";
  groups: number;
  allocation_ratio: number;
  attrition_rate: number;
  sensitivity_effect_sizes: number[];
  sensitivity_powers: number[];
};

type PowerScenario = {
  effect_size: number;
  target_power: number;
  nominal_total_n: number;
  adjusted_total_n: number;
  nominal_per_group: number[];
  adjusted_per_group: number[];
};

type PowerAnalysis = {
  id: string;
  request: PowerAnalysisRequest;
  primary_result: PowerScenario;
  sensitivity_results: PowerScenario[];
  method: string;
  package_versions: Record<string, string>;
  status: PreparationStatus;
  reviewer_note: string | null;
};

type DataField = {
  key: string;
  label: string;
  role: string;
  data_type: "string" | "integer" | "float" | "category" | "boolean" | "datetime";
  unit: string | null;
  required: boolean;
  allowed_min: number | null;
  allowed_max: number | null;
  categories: string[];
  missing_values: string[];
  measurement_timing: string;
  source: string;
  sensitive: boolean;
  validation_rules: string[];
};

type DataContractContent = {
  row_grain: string;
  primary_key_fields: string[];
  fields: DataField[];
  collection_notes: string[];
};

type DataContract = DataContractContent & {
  id: string;
  status: PreparationStatus;
  reviewer_note: string | null;
};

type StudyPreparation = {
  project_id: string;
  power_analysis: PowerAnalysis | null;
  data_contract: DataContract | null;
};

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function Home() {
  const [project, setProject] = useState<Project | null>(null);
  const [evidence, setEvidence] = useState<EvidenceReview | null>(null);
  const [experimentPlan, setExperimentPlan] = useState<ExperimentPlan | null>(null);
  const [preparation, setPreparation] = useState<StudyPreparation | null>(null);
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
    setExperimentPlan(null);
    setPreparation(null);
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

  async function uploadEvidenceDocument(candidateId: string, file: File) {
    if (!project) return;
    const body = new FormData();
    body.append("file", file);
    await requestEvidence(
      `/api/projects/${project.id}/evidence/candidates/${candidateId}/document`,
      { method: "POST", body },
    );
  }

  async function reviewEvidenceItem(
    itemId: string,
    content: EvidenceItemContent,
    status: "approved" | "needs_revision",
    note: string,
  ) {
    if (!project) return;
    await requestEvidence(
      `/api/projects/${project.id}/evidence/evidence-items/${itemId}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, status, note: note.trim() || null }),
      },
    );
  }

  async function appraiseEvidenceItem(itemId: string) {
    if (!project) return;
    await requestEvidence(
      `/api/projects/${project.id}/evidence/evidence-items/${itemId}/appraisal`,
      { method: "POST" },
    );
  }

  async function reviewAppraisal(
    appraisalId: string,
    content: EvidenceAppraisalContent,
    status: "approved" | "needs_revision",
    note: string,
  ) {
    if (!project) return;
    await requestEvidence(
      `/api/projects/${project.id}/evidence/appraisals/${appraisalId}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, status, note: note.trim() || null }),
      },
    );
  }

  async function generateSynthesis() {
    if (!project) return;
    await requestEvidence(`/api/projects/${project.id}/evidence/synthesis`, {
      method: "POST",
    });
  }

  async function reviewSynthesis(
    content: EvidenceSynthesisContent,
    status: "approved" | "needs_revision",
    note: string,
  ) {
    if (!project) return;
    await requestEvidence(`/api/projects/${project.id}/evidence/synthesis`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, status, note: note.trim() || null }),
    });
  }

  async function requestExperiment(path: string, init?: RequestInit) {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiBase}${path}`, init);
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "实验设计请求失败。");
      }
      const updated: ExperimentPlan = await response.json();
      setExperimentPlan(updated);
      return updated;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "发生未知错误");
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function startExperimentPlan() {
    if (!project) return;
    await requestExperiment(`/api/projects/${project.id}/experiment-plan`, {
      method: "POST",
    });
  }

  async function reviewExperimentPlan(
    content: ExperimentPlanContent,
    status: "approved" | "needs_revision",
    note: string,
  ) {
    if (!project) return;
    await requestExperiment(`/api/projects/${project.id}/experiment-plan`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, status, note: note.trim() || null }),
    });
  }

  async function requestPreparation(path: string, init?: RequestInit) {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiBase}${path}`, init);
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "研究执行准备请求失败。");
      }
      const updated: StudyPreparation = await response.json();
      setPreparation(updated);
      return updated;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "发生未知错误");
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function calculatePower(request: PowerAnalysisRequest) {
    if (!project) return;
    await requestPreparation(
      `/api/projects/${project.id}/study-preparation/power-analysis`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      },
    );
  }

  async function reviewPower(status: "approved" | "needs_revision", note: string) {
    if (!project) return;
    await requestPreparation(
      `/api/projects/${project.id}/study-preparation/power-analysis`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, note: note.trim() || null }),
      },
    );
  }

  async function generateDataContract() {
    if (!project) return;
    await requestPreparation(
      `/api/projects/${project.id}/study-preparation/data-contract`,
      { method: "POST" },
    );
  }

  async function reviewDataContract(
    content: DataContractContent,
    status: "approved" | "needs_revision",
    note: string,
  ) {
    if (!project) return;
    await requestPreparation(
      `/api/projects/${project.id}/study-preparation/data-contract`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, status, note: note.trim() || null }),
      },
    );
  }

  async function downloadDataTemplate() {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${apiBase}/api/projects/${project.id}/study-preparation/template.csv`,
      );
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "数据模板下载失败。");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `human-factors-${project.id}-template.csv`;
      anchor.click();
      URL.revokeObjectURL(url);
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
          <p>Agent 先澄清关键信息，再生成可编辑、可追溯的问题界定。</p>
        </div>
        <div className="status-card">
          <span className="status-dot" />
          证据驱动研究工作流
        </div>
      </header>

      <WorkflowStrip
        stage={project?.stage ?? "intake"}
        evidence={evidence}
        experimentPlan={experimentPlan}
      />

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
              <h2>
                {preparation
                  ? "功效分析与数据契约"
                  : experimentPlan
                  ? "实验设计方案"
                  : evidence?.synthesis
                    ? "证据矩阵与综合"
                    : resultTitle(project?.stage, evidence?.stage)}
              </h2>
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

          {evidence?.stage === "screening" && !experimentPlan && (
            <LiteratureScreening
              candidates={evidence.candidates}
              documents={evidence.documents}
              evidenceItems={evidence.evidence_items}
              appraisals={evidence.appraisals}
              synthesis={evidence.synthesis}
              loading={loading}
              onScreen={screenCandidate}
              onUpload={uploadEvidenceDocument}
              onReview={reviewEvidenceItem}
              onAppraise={appraiseEvidenceItem}
              onReviewAppraisal={reviewAppraisal}
              onGenerateSynthesis={generateSynthesis}
              onReviewSynthesis={reviewSynthesis}
            />
          )}

          {evidence?.synthesis?.status === "approved" && !experimentPlan && (
            <div className="experiment-entry">
              <div>
                <strong>证据综合已批准</strong>
                <p>可以生成带证据引用、功效分析输入和人工审批的实验方案草案。</p>
              </div>
              <button disabled={loading} onClick={startExperimentPlan}>
                生成实验方案
              </button>
            </div>
          )}

          {experimentPlan && evidence?.synthesis && (
            <ExperimentPlanEditor
              plan={experimentPlan}
              matrix={evidence.synthesis.matrix}
              loading={loading}
              onReview={reviewExperimentPlan}
              onRegenerate={startExperimentPlan}
            />
          )}

          {experimentPlan?.status === "approved" && (
            <StudyPreparationPanel
              experimentPlan={experimentPlan}
              preparation={preparation}
              loading={loading}
              onCalculatePower={calculatePower}
              onReviewPower={reviewPower}
              onGenerateContract={generateDataContract}
              onReviewContract={reviewDataContract}
              onDownloadTemplate={downloadDataTemplate}
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
  experimentPlan,
}: {
  stage: ProjectStage;
  evidence: EvidenceReview | null;
  experimentPlan: ExperimentPlan | null;
}) {
  const current = experimentPlan
    ? 2
    : evidence || stage === "problem_frame_approved"
      ? 1
      : 0;
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
  documents,
  evidenceItems,
  appraisals,
  synthesis,
  loading,
  onScreen,
  onUpload,
  onReview,
  onAppraise,
  onReviewAppraisal,
  onGenerateSynthesis,
  onReviewSynthesis,
}: {
  candidates: LiteratureCandidate[];
  documents: EvidenceDocument[];
  evidenceItems: EvidenceItem[];
  appraisals: EvidenceAppraisal[];
  synthesis: EvidenceSynthesis | null;
  loading: boolean;
  onScreen: (
    candidateId: string,
    status: "included" | "excluded",
    reason: string,
  ) => void;
  onUpload: (candidateId: string, file: File) => void;
  onReview: (
    itemId: string,
    content: EvidenceItemContent,
    status: "approved" | "needs_revision",
    note: string,
  ) => void;
  onAppraise: (itemId: string) => void;
  onReviewAppraisal: (
    appraisalId: string,
    content: EvidenceAppraisalContent,
    status: "approved" | "needs_revision",
    note: string,
  ) => void;
  onGenerateSynthesis: () => void;
  onReviewSynthesis: (
    content: EvidenceSynthesisContent,
    status: "approved" | "needs_revision",
    note: string,
  ) => void;
}) {
  const included = candidates.filter((item) => item.screening_status === "included").length;
  const excluded = candidates.filter((item) => item.screening_status === "excluded").length;
  const approvedItems = evidenceItems.filter((item) => item.status === "approved");
  const readyForSynthesis = approvedItems.length > 0 && approvedItems.every((item) =>
    appraisals.some(
      (appraisal) => appraisal.evidence_item_id === item.id && appraisal.status === "approved",
    ),
  );
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
            document={documents.find((item) => item.candidate_id === candidate.id)}
            evidenceItem={evidenceItems.find((item) => item.candidate_id === candidate.id)}
            appraisal={appraisals.find((item) =>
              item.evidence_item_id === evidenceItems.find(
                (evidenceItem) => evidenceItem.candidate_id === candidate.id,
              )?.id
            )}
            loading={loading}
            onScreen={onScreen}
            onUpload={onUpload}
            onReview={onReview}
            onAppraise={onAppraise}
            onReviewAppraisal={onReviewAppraisal}
            key={candidate.id}
          />
        ))}
      </div>
      {readyForSynthesis && !synthesis && (
        <div className="synthesis-entry">
          <div>
            <strong>所有可用证据均已完成质量评价</strong>
            <p>现在可以建立跨文献矩阵并生成待审核的叙述性综合。</p>
          </div>
          <button disabled={loading} onClick={onGenerateSynthesis}>
            生成证据矩阵与综合
          </button>
        </div>
      )}
      {synthesis && (
        <EvidenceSynthesisEditor
          synthesis={synthesis}
          loading={loading}
          onReview={onReviewSynthesis}
        />
      )}
    </div>
  );
}

function CandidateCard({
  candidate,
  document,
  evidenceItem,
  appraisal,
  loading,
  onScreen,
  onUpload,
  onReview,
  onAppraise,
  onReviewAppraisal,
}: {
  candidate: LiteratureCandidate;
  document?: EvidenceDocument;
  evidenceItem?: EvidenceItem;
  appraisal?: EvidenceAppraisal;
  loading: boolean;
  onScreen: (
    candidateId: string,
    status: "included" | "excluded",
    reason: string,
  ) => void;
  onUpload: (candidateId: string, file: File) => void;
  onReview: (
    itemId: string,
    content: EvidenceItemContent,
    status: "approved" | "needs_revision",
    note: string,
  ) => void;
  onAppraise: (itemId: string) => void;
  onReviewAppraisal: (
    appraisalId: string,
    content: EvidenceAppraisalContent,
    status: "approved" | "needs_revision",
    note: string,
  ) => void;
}) {
  const [reason, setReason] = useState(candidate.screening_reason ?? "");
  const [file, setFile] = useState<File | null>(null);
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
      {candidate.screening_status === "included" && !document && (
        <div className="pdf-upload">
          <div>
            <strong>上传研究全文</strong>
            <small>仅支持包含可选择文字的 PDF，最大 25 MB。</small>
          </div>
          <input
            type="file"
            accept="application/pdf,.pdf"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
          <button
            disabled={loading || !file}
            onClick={() => file && onUpload(candidate.id, file)}
          >
            {loading ? "正在提取…" : "上传并提取证据"}
          </button>
        </div>
      )}
      {document && (
        <div className="document-meta">
          <span>PDF 已导入</span>
          <strong>{document.filename}</strong>
          <small>{document.page_count} 页 · {(document.byte_size / 1024).toFixed(1)} KB</small>
        </div>
      )}
      {evidenceItem && (
        <EvidenceItemEditor
          item={evidenceItem}
          loading={loading}
          onReview={onReview}
        />
      )}
      {evidenceItem?.status === "approved" && !appraisal && (
        <div className="appraisal-entry">
          <div>
            <strong>下一步：研究质量评价</strong>
            <small>生成评价草案后，需要人工判断设计、样本、测量和偏倚风险。</small>
          </div>
          <button disabled={loading} onClick={() => onAppraise(evidenceItem.id)}>
            生成评价草案
          </button>
        </div>
      )}
      {appraisal && (
        <EvidenceAppraisalEditor
          appraisal={appraisal}
          loading={loading}
          onReview={onReviewAppraisal}
        />
      )}
    </article>
  );
}

function EvidenceItemEditor({
  item,
  loading,
  onReview,
}: {
  item: EvidenceItem;
  loading: boolean;
  onReview: (
    itemId: string,
    content: EvidenceItemContent,
    status: "approved" | "needs_revision",
    note: string,
  ) => void;
}) {
  const [content, setContent] = useState<EvidenceItemContent>({
    research_questions: item.research_questions,
    study_design: item.study_design,
    participants: item.participants,
    sample_size: item.sample_size,
    task_context: item.task_context,
    independent_variables: item.independent_variables,
    dependent_variables: item.dependent_variables,
    control_variables: item.control_variables,
    measures: item.measures,
    statistical_methods: item.statistical_methods,
    key_findings: item.key_findings,
    effect_sizes: item.effect_sizes,
    limitations: item.limitations,
    source_excerpts: item.source_excerpts,
  });
  const [note, setNote] = useState(item.reviewer_note ?? "");

  const listFields = [
    ["research_questions", "研究问题或假设"],
    ["independent_variables", "自变量"],
    ["dependent_variables", "因变量"],
    ["control_variables", "控制变量"],
    ["measures", "测量工具与量表"],
    ["statistical_methods", "统计方法"],
    ["key_findings", "关键结果"],
    ["effect_sizes", "效应量"],
    ["limitations", "研究局限"],
  ] as const;

  function updateList(field: typeof listFields[number][0], value: string) {
    setContent((current) => ({
      ...current,
      [field]: value.split("\n").map((entry) => entry.trim()).filter(Boolean),
    }));
  }

  return (
    <div className="evidence-item-editor">
      <div className="evidence-item-heading">
        <div>
          <strong>结构化证据</strong>
          <small>
            {item.generation.generator === "human"
              ? "人工复核版本"
              : item.generation.model ?? "本地保守提取"}
          </small>
        </div>
        <span className={`evidence-status ${item.status}`}>
          {item.status === "approved" ? "已批准" : item.status === "needs_revision" ? "需修订" : "待复核"}
        </span>
      </div>
      <div className="field-grid">
        <label>
          研究设计
          <input
            value={content.study_design ?? ""}
            onChange={(event) => setContent((current) => ({ ...current, study_design: event.target.value || null }))}
          />
        </label>
        <label>
          样本量
          <input
            type="number"
            min={1}
            value={content.sample_size ?? ""}
            onChange={(event) => setContent((current) => ({
              ...current,
              sample_size: event.target.value ? Number(event.target.value) : null,
            }))}
          />
        </label>
      </div>
      <label>
        参与者
        <input
          value={content.participants ?? ""}
          onChange={(event) => setContent((current) => ({ ...current, participants: event.target.value || null }))}
        />
      </label>
      <label>
        任务与场景
        <textarea
          rows={2}
          value={content.task_context ?? ""}
          onChange={(event) => setContent((current) => ({ ...current, task_context: event.target.value || null }))}
        />
      </label>
      {listFields.map(([field, label]) => (
        <label key={field}>
          {label} <small>每行一项</small>
          <textarea
            rows={3}
            value={content[field].join("\n")}
            onChange={(event) => updateList(field, event.target.value)}
          />
        </label>
      ))}
      <div className="source-excerpts">
        <strong>原文依据</strong>
        {content.source_excerpts.map((excerpt, index) => (
          <blockquote key={`${excerpt.page_number}-${index}`}>
            <span>第 {excerpt.page_number} 页 · {excerpt.relevance}</span>
            {excerpt.text}
          </blockquote>
        ))}
      </div>
      <label>
        复核备注
        <textarea
          rows={2}
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder="记录人工修订或仍需确认的问题"
        />
      </label>
      <div className="evidence-review-actions">
        <button
          disabled={loading || note.trim().length < 3}
          onClick={() => onReview(item.id, content, "needs_revision", note)}
        >
          标记需修订
        </button>
        <button
          className="approve-evidence"
          disabled={loading}
          onClick={() => onReview(item.id, content, "approved", note)}
        >
          批准为可用证据
        </button>
      </div>
    </div>
  );
}

function EvidenceAppraisalEditor({
  appraisal,
  loading,
  onReview,
}: {
  appraisal: EvidenceAppraisal;
  loading: boolean;
  onReview: (
    appraisalId: string,
    content: EvidenceAppraisalContent,
    status: "approved" | "needs_revision",
    note: string,
  ) => void;
}) {
  const [content, setContent] = useState<EvidenceAppraisalContent>({
    design_appropriateness: appraisal.design_appropriateness,
    sample_adequacy: appraisal.sample_adequacy,
    measurement_validity: appraisal.measurement_validity,
    analysis_adequacy: appraisal.analysis_adequacy,
    bias_risk: appraisal.bias_risk,
    directness: appraisal.directness,
    overall_confidence: appraisal.overall_confidence,
    strengths: appraisal.strengths,
    concerns: appraisal.concerns,
  });
  const [note, setNote] = useState(appraisal.reviewer_note ?? "");
  const domains = [
    ["design_appropriateness", "研究设计适切性"],
    ["sample_adequacy", "样本充分性"],
    ["measurement_validity", "测量有效性"],
    ["analysis_adequacy", "统计分析适切性"],
    ["bias_risk", "偏倚风险"],
    ["directness", "对当前问题的直接性"],
  ] as const;

  function updateJudgment(
    field: typeof domains[number][0],
    patch: Partial<AppraisalJudgment>,
  ) {
    setContent((current) => ({
      ...current,
      [field]: { ...current[field], ...patch },
    }));
  }

  return (
    <div className="appraisal-editor">
      <div className="evidence-item-heading">
        <div>
          <strong>研究质量评价</strong>
          <small>辅助评价草案，不等同于正式 GRADE 或 RoB 2 评价</small>
        </div>
        <span className={`evidence-status ${appraisal.status}`}>
          {reviewStatusLabel(appraisal.status)}
        </span>
      </div>
      <div className="appraisal-domains">
        {domains.map(([field, label]) => (
          <div className="appraisal-domain" key={field}>
            <label>
              {label}
              <select
                value={content[field].concern}
                onChange={(event) => updateJudgment(field, {
                  concern: event.target.value as AppraisalConcern,
                })}
              >
                <option value="low">低关注</option>
                <option value="some_concerns">存在一些关注</option>
                <option value="high">高关注</option>
                <option value="unclear">信息不足</option>
              </select>
            </label>
            <textarea
              rows={2}
              value={content[field].rationale}
              onChange={(event) => updateJudgment(field, { rationale: event.target.value })}
            />
          </div>
        ))}
      </div>
      <label>
        单篇研究总体可信度
        <select
          value={content.overall_confidence}
          onChange={(event) => setContent((current) => ({
            ...current,
            overall_confidence: event.target.value as AppraisalConfidence,
          }))}
        >
          <option value="high">高</option>
          <option value="moderate">中等</option>
          <option value="low">低</option>
          <option value="unclear">信息不足</option>
        </select>
      </label>
      {(["strengths", "concerns"] as const).map((field) => (
        <label key={field}>
          {field === "strengths" ? "主要优势" : "主要关注"} <small>每行一项</small>
          <textarea
            rows={3}
            value={content[field].join("\n")}
            onChange={(event) => setContent((current) => ({
              ...current,
              [field]: event.target.value.split("\n").map((item) => item.trim()).filter(Boolean),
            }))}
          />
        </label>
      ))}
      <label>
        评价复核备注
        <textarea rows={2} value={note} onChange={(event) => setNote(event.target.value)} />
      </label>
      <div className="evidence-review-actions">
        <button
          disabled={loading || note.trim().length < 3}
          onClick={() => onReview(appraisal.id, content, "needs_revision", note)}
        >
          标记需修订
        </button>
        <button
          className="approve-evidence"
          disabled={loading}
          onClick={() => onReview(appraisal.id, content, "approved", note)}
        >
          批准质量评价
        </button>
      </div>
    </div>
  );
}

function EvidenceSynthesisEditor({
  synthesis,
  loading,
  onReview,
}: {
  synthesis: EvidenceSynthesis;
  loading: boolean;
  onReview: (
    content: EvidenceSynthesisContent,
    status: "approved" | "needs_revision",
    note: string,
  ) => void;
}) {
  const [content, setContent] = useState<EvidenceSynthesisContent>({
    matrix: synthesis.matrix,
    consistent_findings: synthesis.consistent_findings,
    conflicting_findings: synthesis.conflicting_findings,
    evidence_gaps: synthesis.evidence_gaps,
    transferability_notes: synthesis.transferability_notes,
    cautions: synthesis.cautions,
  });
  const [note, setNote] = useState(synthesis.reviewer_note ?? "");

  function updateClaim(
    group: "consistent_findings" | "conflicting_findings",
    index: number,
    patch: Partial<SynthesisClaim>,
  ) {
    setContent((current) => ({
      ...current,
      [group]: current[group].map((claim, claimIndex) =>
        claimIndex === index ? { ...claim, ...patch } : claim
      ),
    }));
  }

  function addClaim(group: "consistent_findings" | "conflicting_findings") {
    if (content.matrix.length < 2) return;
    setContent((current) => ({
      ...current,
      [group]: [
        ...current[group],
        {
          statement: "",
          evidence_item_ids: current.matrix.slice(0, 2).map((row) => row.evidence_item_id),
          confidence: "unclear" as const,
          rationale: "",
        },
      ],
    }));
  }

  function removeClaim(
    group: "consistent_findings" | "conflicting_findings",
    index: number,
  ) {
    setContent((current) => ({
      ...current,
      [group]: current[group].filter((_, claimIndex) => claimIndex !== index),
    }));
  }

  const claimsValid = [
    ...content.consistent_findings,
    ...content.conflicting_findings,
  ].every((claim) =>
    claim.statement.trim().length >= 3
    && claim.rationale.trim().length >= 3
    && new Set(claim.evidence_item_ids).size >= 2
  );

  return (
    <section className="synthesis-editor">
      <div className="evidence-item-heading">
        <div>
          <span className="section-kicker">跨文献综合</span>
          <h3>证据矩阵与综合判断</h3>
        </div>
        <span className={`evidence-status ${synthesis.status}`}>
          {reviewStatusLabel(synthesis.status)}
        </span>
      </div>
      <div className="matrix-scroll">
        <table className="evidence-matrix">
          <thead>
            <tr>
              <th>文献</th>
              <th>人群与场景</th>
              <th>设计与样本</th>
              <th>变量/干预</th>
              <th>结果与测量</th>
              <th>发现与效应量</th>
              <th>可信度</th>
            </tr>
          </thead>
          <tbody>
            {content.matrix.map((row) => (
              <tr key={row.evidence_item_id}>
                <td>{row.citation}</td>
                <td>{row.population_and_context}</td>
                <td>{row.design_and_sample}</td>
                <td>{row.exposures_or_interventions.join("；") || "未报告"}</td>
                <td>{row.outcomes_and_measures.join("；") || "未报告"}</td>
                <td>{row.findings_and_effects.join("；") || "未报告"}</td>
                <td>{confidenceLabel(row.appraisal_confidence)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {(["consistent_findings", "conflicting_findings"] as const).map((group) => (
        <div className="synthesis-claims" key={group}>
          <div className="synthesis-claim-heading">
            <strong>{group === "consistent_findings" ? "一致发现" : "冲突发现"}</strong>
            <button
              disabled={content.matrix.length < 2}
              onClick={() => addClaim(group)}
            >
              添加结论
            </button>
          </div>
          {content[group].length === 0 && <small>当前没有形成该类跨研究结论。</small>}
          {content[group].map((claim, index) => (
            <div className="synthesis-claim" key={`${group}-${index}`}>
              <textarea
                rows={2}
                value={claim.statement}
                onChange={(event) => updateClaim(group, index, { statement: event.target.value })}
              />
              <textarea
                rows={2}
                value={claim.rationale}
                onChange={(event) => updateClaim(group, index, { rationale: event.target.value })}
              />
              <select
                value={claim.confidence}
                onChange={(event) => updateClaim(group, index, {
                  confidence: event.target.value as AppraisalConfidence,
                })}
              >
                <option value="high">高可信度</option>
                <option value="moderate">中等可信度</option>
                <option value="low">低可信度</option>
                <option value="unclear">信息不足</option>
              </select>
              <button className="remove-claim" onClick={() => removeClaim(group, index)}>
                删除
              </button>
              <div className="claim-references">
                <span>支持该结论的证据（至少两项）</span>
                {content.matrix.map((row) => {
                  const checked = claim.evidence_item_ids.includes(row.evidence_item_id);
                  return (
                    <label key={row.evidence_item_id}>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => updateClaim(group, index, {
                          evidence_item_ids: checked
                            ? claim.evidence_item_ids.filter((id) => id !== row.evidence_item_id)
                            : [...claim.evidence_item_ids, row.evidence_item_id],
                        })}
                      />
                      {row.citation}
                    </label>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      ))}
      {([
        ["evidence_gaps", "证据缺口"],
        ["transferability_notes", "适用性与迁移说明"],
        ["cautions", "使用警示"],
      ] as const).map(([field, label]) => (
        <label key={field}>
          {label} <small>每行一项</small>
          <textarea
            rows={4}
            value={content[field].join("\n")}
            onChange={(event) => setContent((current) => ({
              ...current,
              [field]: event.target.value.split("\n").map((item) => item.trim()).filter(Boolean),
            }))}
          />
        </label>
      ))}
      <label>
        综合复核备注
        <textarea rows={2} value={note} onChange={(event) => setNote(event.target.value)} />
      </label>
      <div className="evidence-review-actions">
        <button
          disabled={loading || note.trim().length < 3}
          onClick={() => onReview(content, "needs_revision", note)}
        >
          标记需修订
        </button>
        <button
          className="approve-evidence"
          disabled={loading || !claimsValid}
          onClick={() => onReview(content, "approved", note)}
        >
          批准证据综合
        </button>
      </div>
    </section>
  );
}

function reviewStatusLabel(status: ReviewStatus) {
  return status === "approved" ? "已批准" : status === "needs_revision" ? "需修订" : "待复核";
}

function confidenceLabel(confidence: AppraisalConfidence) {
  return {
    high: "高",
    moderate: "中等",
    low: "低",
    unclear: "信息不足",
  }[confidence];
}

function ExperimentPlanEditor({
  plan,
  matrix,
  loading,
  onReview,
  onRegenerate,
}: {
  plan: ExperimentPlan;
  matrix: EvidenceMatrixRow[];
  loading: boolean;
  onReview: (
    content: ExperimentPlanContent,
    status: "approved" | "needs_revision",
    note: string,
  ) => void;
  onRegenerate: () => void;
}) {
  const [content, setContent] = useState<ExperimentPlanContent>({
    title: plan.title,
    objective: plan.objective,
    design_type: plan.design_type,
    hypotheses: plan.hypotheses,
    conditions: plan.conditions,
    variables: plan.variables,
    participant_plan: plan.participant_plan,
    sample_size_planning: plan.sample_size_planning,
    randomization_plan: plan.randomization_plan,
    counterbalancing_plan: plan.counterbalancing_plan,
    procedure: plan.procedure,
    analysis_plan: plan.analysis_plan,
    ethics_and_safety: plan.ethics_and_safety,
    assumptions: plan.assumptions,
    uncertainties: plan.uncertainties,
    evidence_grounded_decisions: plan.evidence_grounded_decisions,
  });
  const [note, setNote] = useState(plan.reviewer_note ?? "");
  const approvalReady = content.design_type !== "undecided"
    && Boolean(content.sample_size_planning.effect_size_metric)
    && content.sample_size_planning.expected_effect_size !== null
    && content.sample_size_planning.alpha !== null
    && content.sample_size_planning.target_power !== null;

  if (plan.status === "stale") {
    return (
      <div className="stale-plan">
        <strong>实验方案已过期</strong>
        <p>上游证据综合已经变化。旧方案保留用于审计，但不能继续批准。</p>
        <button disabled={loading} onClick={onRegenerate}>根据最新证据重新生成</button>
      </div>
    );
  }

  return (
    <section className="experiment-editor">
      <div className="evidence-item-heading">
        <div>
          <span className="section-kicker">阶段 3 · 实验设计</span>
          <h3>证据驱动实验方案</h3>
          <small>{plan.generation.model ?? (plan.generation.generator === "human" ? "人工复核版本" : "本地保守草案")}</small>
        </div>
        <span className={`evidence-status ${plan.status}`}>
          {reviewStatusLabel(plan.status as ReviewStatus)}
        </span>
      </div>

      <label>
        方案标题
        <input
          value={content.title}
          onChange={(event) => setContent((current) => ({ ...current, title: event.target.value }))}
        />
      </label>
      <label>
        研究目标
        <textarea
          rows={4}
          value={content.objective}
          onChange={(event) => setContent((current) => ({ ...current, objective: event.target.value }))}
        />
      </label>
      <label>
        实验设计类型
        <select
          value={content.design_type}
          onChange={(event) => setContent((current) => ({
            ...current,
            design_type: event.target.value as ExperimentDesignType,
          }))}
        >
          <option value="undecided">待确定</option>
          <option value="within_subjects">组内设计</option>
          <option value="between_subjects">组间设计</option>
          <option value="mixed">混合设计</option>
          <option value="quasi_experimental">准实验设计</option>
        </select>
      </label>

      <ExperimentSection title="研究假设">
        {content.hypotheses.map((hypothesis, index) => (
          <div className="experiment-card" key={`hypothesis-${index}`}>
            <strong>假设 {index + 1}</strong>
            <label>
              备择假设
              <textarea
                rows={2}
                value={hypothesis.statement}
                onChange={(event) => setContent((current) => ({
                  ...current,
                  hypotheses: current.hypotheses.map((item, itemIndex) =>
                    itemIndex === index ? { ...item, statement: event.target.value } : item
                  ),
                }))}
              />
            </label>
            <label>
              零假设
              <textarea
                rows={2}
                value={hypothesis.null_hypothesis}
                onChange={(event) => setContent((current) => ({
                  ...current,
                  hypotheses: current.hypotheses.map((item, itemIndex) =>
                    itemIndex === index ? { ...item, null_hypothesis: event.target.value } : item
                  ),
                }))}
              />
            </label>
            <div className="field-grid">
              <label>
                方向
                <select
                  value={hypothesis.direction}
                  onChange={(event) => setContent((current) => ({
                    ...current,
                    hypotheses: current.hypotheses.map((item, itemIndex) =>
                      itemIndex === index
                        ? { ...item, direction: event.target.value as typeof item.direction }
                        : item
                    ),
                  }))}
                >
                  <option value="non_directional">非方向性</option>
                  <option value="increase">预期增加</option>
                  <option value="decrease">预期降低</option>
                </select>
              </label>
              <label>
                主要结局
                <input
                  value={hypothesis.primary_outcome}
                  onChange={(event) => setContent((current) => ({
                    ...current,
                    hypotheses: current.hypotheses.map((item, itemIndex) =>
                      itemIndex === index ? { ...item, primary_outcome: event.target.value } : item
                    ),
                  }))}
                />
              </label>
            </div>
            <EvidenceReferencePicker
              matrix={matrix}
              selected={hypothesis.evidence_item_ids}
              onChange={(selected) => setContent((current) => ({
                ...current,
                hypotheses: current.hypotheses.map((item, itemIndex) =>
                  itemIndex === index ? { ...item, evidence_item_ids: selected } : item
                ),
              }))}
            />
          </div>
        ))}
      </ExperimentSection>

      <ExperimentSection title="实验条件">
        {content.conditions.map((condition, index) => (
          <div className="experiment-card compact-card" key={`condition-${index}`}>
            <input
              value={condition.name}
              onChange={(event) => setContent((current) => ({
                ...current,
                conditions: current.conditions.map((item, itemIndex) =>
                  itemIndex === index ? { ...item, name: event.target.value } : item
                ),
              }))}
            />
            <textarea
              rows={2}
              value={condition.description}
              onChange={(event) => setContent((current) => ({
                ...current,
                conditions: current.conditions.map((item, itemIndex) =>
                  itemIndex === index ? { ...item, description: event.target.value } : item
                ),
              }))}
            />
          </div>
        ))}
      </ExperimentSection>

      <ExperimentSection title="变量与操作化">
        {content.variables.map((variable, index) => (
          <div className="experiment-card" key={`variable-${index}`}>
            <div className="field-grid">
              <label>
                变量名称
                <input
                  value={variable.name}
                  onChange={(event) => setContent((current) => ({
                    ...current,
                    variables: current.variables.map((item, itemIndex) =>
                      itemIndex === index ? { ...item, name: event.target.value } : item
                    ),
                  }))}
                />
              </label>
              <label>
                变量角色
                <select
                  value={variable.role}
                  onChange={(event) => setContent((current) => ({
                    ...current,
                    variables: current.variables.map((item, itemIndex) =>
                      itemIndex === index ? { ...item, role: event.target.value as VariableRole } : item
                    ),
                  }))}
                >
                  <option value="independent">自变量</option>
                  <option value="dependent">因变量</option>
                  <option value="control">控制变量</option>
                  <option value="covariate">协变量</option>
                  <option value="manipulation_check">操纵检验</option>
                </select>
              </label>
            </div>
            {([
              ["operational_definition", "操作化定义"],
              ["measurement_method", "测量或记录方法"],
              ["measurement_timing", "测量时点"],
            ] as const).map(([field, label]) => (
              <label key={field}>
                {label}
                <textarea
                  rows={2}
                  value={variable[field]}
                  onChange={(event) => setContent((current) => ({
                    ...current,
                    variables: current.variables.map((item, itemIndex) =>
                      itemIndex === index ? { ...item, [field]: event.target.value } : item
                    ),
                  }))}
                />
              </label>
            ))}
            <EvidenceReferencePicker
              matrix={matrix}
              selected={variable.evidence_item_ids}
              onChange={(selected) => setContent((current) => ({
                ...current,
                variables: current.variables.map((item, itemIndex) =>
                  itemIndex === index ? { ...item, evidence_item_ids: selected } : item
                ),
              }))}
            />
          </div>
        ))}
      </ExperimentSection>

      <ExperimentSection title="被试与招募">
        <label>
          目标人群
          <input
            value={content.participant_plan.target_population}
            onChange={(event) => setContent((current) => ({
              ...current,
              participant_plan: { ...current.participant_plan, target_population: event.target.value },
            }))}
          />
        </label>
        <div className="field-grid">
          <StringListField
            label="纳入标准"
            value={content.participant_plan.inclusion_criteria}
            onChange={(value) => setContent((current) => ({
              ...current,
              participant_plan: { ...current.participant_plan, inclusion_criteria: value },
            }))}
          />
          <StringListField
            label="排除标准"
            value={content.participant_plan.exclusion_criteria}
            onChange={(value) => setContent((current) => ({
              ...current,
              participant_plan: { ...current.participant_plan, exclusion_criteria: value },
            }))}
          />
        </div>
        <label>
          招募策略
          <textarea
            rows={2}
            value={content.participant_plan.recruitment_strategy}
            onChange={(event) => setContent((current) => ({
              ...current,
              participant_plan: { ...current.participant_plan, recruitment_strategy: event.target.value },
            }))}
          />
        </label>
        <label>
          抽样方法
          <input
            value={content.participant_plan.sampling_method}
            onChange={(event) => setContent((current) => ({
              ...current,
              participant_plan: { ...current.participant_plan, sampling_method: event.target.value },
            }))}
          />
        </label>
      </ExperimentSection>

      <ExperimentSection title="功效分析输入">
        <div className="power-warning">
          此处只记录计算输入，不会生成最终样本量。样本量将在确定性计算模块中产生。
        </div>
        <label>
          计划主要检验
          <input
            value={content.sample_size_planning.planned_primary_test}
            onChange={(event) => setContent((current) => ({
              ...current,
              sample_size_planning: { ...current.sample_size_planning, planned_primary_test: event.target.value },
            }))}
          />
        </label>
        <div className="power-grid">
          <label>
            效应量指标
            <input
              value={content.sample_size_planning.effect_size_metric ?? ""}
              placeholder="例如 Cohen's dz"
              onChange={(event) => setContent((current) => ({
                ...current,
                sample_size_planning: { ...current.sample_size_planning, effect_size_metric: event.target.value || null },
              }))}
            />
          </label>
          <NumericNullableField
            label="预期效应量"
            value={content.sample_size_planning.expected_effect_size}
            onChange={(value) => setContent((current) => ({
              ...current,
              sample_size_planning: { ...current.sample_size_planning, expected_effect_size: value },
            }))}
          />
          <NumericNullableField
            label="显著性水平 α"
            value={content.sample_size_planning.alpha}
            min={0.001}
            max={0.999}
            step={0.001}
            onChange={(value) => setContent((current) => ({
              ...current,
              sample_size_planning: { ...current.sample_size_planning, alpha: value },
            }))}
          />
          <NumericNullableField
            label="目标检验效能"
            value={content.sample_size_planning.target_power}
            min={0.01}
            max={0.99}
            step={0.01}
            onChange={(value) => setContent((current) => ({
              ...current,
              sample_size_planning: { ...current.sample_size_planning, target_power: value },
            }))}
          />
          <NumericNullableField
            label="预计脱落比例"
            value={content.sample_size_planning.attrition_allowance}
            min={0}
            max={0.99}
            step={0.01}
            onChange={(value) => setContent((current) => ({
              ...current,
              sample_size_planning: { ...current.sample_size_planning, attrition_allowance: value },
            }))}
          />
        </div>
        <label>
          效应量依据
          <textarea
            rows={2}
            value={content.sample_size_planning.effect_size_basis}
            onChange={(event) => setContent((current) => ({
              ...current,
              sample_size_planning: { ...current.sample_size_planning, effect_size_basis: event.target.value },
            }))}
          />
        </label>
        <small>{content.sample_size_planning.calculation_note}</small>
      </ExperimentSection>

      <ExperimentSection title="随机化与顺序控制">
        <label>
          随机化计划
          <textarea
            rows={3}
            value={content.randomization_plan}
            onChange={(event) => setContent((current) => ({ ...current, randomization_plan: event.target.value }))}
          />
        </label>
        <label>
          顺序平衡计划
          <textarea
            rows={3}
            value={content.counterbalancing_plan}
            onChange={(event) => setContent((current) => ({ ...current, counterbalancing_plan: event.target.value }))}
          />
        </label>
      </ExperimentSection>

      <ExperimentSection title="实验流程">
        {content.procedure.map((step, index) => (
          <div className="experiment-card procedure-card" key={`procedure-${step.order}`}>
            <span className="procedure-order">{step.order}</span>
            <label>
              步骤名称
              <input
                value={step.name}
                onChange={(event) => setContent((current) => ({
                  ...current,
                  procedure: current.procedure.map((item, itemIndex) =>
                    itemIndex === index ? { ...item, name: event.target.value } : item
                  ),
                }))}
              />
            </label>
            <label>
              说明
              <textarea
                rows={2}
                value={step.description}
                onChange={(event) => setContent((current) => ({
                  ...current,
                  procedure: current.procedure.map((item, itemIndex) =>
                    itemIndex === index ? { ...item, description: event.target.value } : item
                  ),
                }))}
              />
            </label>
            <NumericNullableField
              label="预计分钟数"
              value={step.duration_minutes}
              min={1}
              step={1}
              onChange={(value) => setContent((current) => ({
                ...current,
                procedure: current.procedure.map((item, itemIndex) =>
                  itemIndex === index ? { ...item, duration_minutes: value } : item
                ),
              }))}
            />
            <StringListField
              label="采集数据"
              value={step.data_collected}
              onChange={(value) => setContent((current) => ({
                ...current,
                procedure: current.procedure.map((item, itemIndex) =>
                  itemIndex === index ? { ...item, data_collected: value } : item
                ),
              }))}
            />
          </div>
        ))}
      </ExperimentSection>

      <ExperimentSection title="统计分析计划">
        {content.analysis_plan.map((analysis, index) => (
          <div className="experiment-card" key={`analysis-${index}`}>
            <strong>对应假设 {analysis.hypothesis_index}</strong>
            <label>
              方法
              <textarea
                rows={2}
                value={analysis.method}
                onChange={(event) => setContent((current) => ({
                  ...current,
                  analysis_plan: current.analysis_plan.map((item, itemIndex) =>
                    itemIndex === index ? { ...item, method: event.target.value } : item
                  ),
                }))}
              />
            </label>
            <label>
              结局
              <input
                value={analysis.outcome}
                onChange={(event) => setContent((current) => ({
                  ...current,
                  analysis_plan: current.analysis_plan.map((item, itemIndex) =>
                    itemIndex === index ? { ...item, outcome: event.target.value } : item
                  ),
                }))}
              />
            </label>
            <StringListField
              label="预测变量"
              value={analysis.predictors}
              onChange={(value) => setContent((current) => ({
                ...current,
                analysis_plan: current.analysis_plan.map((item, itemIndex) =>
                  itemIndex === index ? { ...item, predictors: value } : item
                ),
              }))}
            />
            <StringListField
              label="需要检查的假设"
              value={analysis.assumptions_to_check}
              onChange={(value) => setContent((current) => ({
                ...current,
                analysis_plan: current.analysis_plan.map((item, itemIndex) =>
                  itemIndex === index ? { ...item, assumptions_to_check: value } : item
                ),
              }))}
            />
            {([
              ["missing_data_strategy", "缺失数据策略"],
              ["multiplicity_strategy", "多重比较策略"],
            ] as const).map(([field, label]) => (
              <label key={field}>
                {label}
                <textarea
                  rows={2}
                  value={analysis[field]}
                  onChange={(event) => setContent((current) => ({
                    ...current,
                    analysis_plan: current.analysis_plan.map((item, itemIndex) =>
                      itemIndex === index ? { ...item, [field]: event.target.value } : item
                    ),
                  }))}
                />
              </label>
            ))}
          </div>
        ))}
      </ExperimentSection>

      <div className="field-grid">
        <StringListField
          label="伦理与安全"
          value={content.ethics_and_safety}
          onChange={(value) => setContent((current) => ({ ...current, ethics_and_safety: value }))}
        />
        <StringListField
          label="当前假设"
          value={content.assumptions}
          onChange={(value) => setContent((current) => ({ ...current, assumptions: value }))}
        />
      </div>
      <StringListField
        label="尚待确认的不确定性"
        value={content.uncertainties}
        onChange={(value) => setContent((current) => ({ ...current, uncertainties: value }))}
      />

      <ExperimentSection title="证据支持的设计决策">
        {content.evidence_grounded_decisions.map((decision, index) => (
          <div className="experiment-card" key={`decision-${index}`}>
            <textarea
              rows={2}
              value={decision.decision}
              onChange={(event) => setContent((current) => ({
                ...current,
                evidence_grounded_decisions: current.evidence_grounded_decisions.map((item, itemIndex) =>
                  itemIndex === index ? { ...item, decision: event.target.value } : item
                ),
              }))}
            />
            <textarea
              rows={2}
              value={decision.rationale}
              onChange={(event) => setContent((current) => ({
                ...current,
                evidence_grounded_decisions: current.evidence_grounded_decisions.map((item, itemIndex) =>
                  itemIndex === index ? { ...item, rationale: event.target.value } : item
                ),
              }))}
            />
            <EvidenceReferencePicker
              matrix={matrix}
              selected={decision.evidence_item_ids}
              onChange={(selected) => setContent((current) => ({
                ...current,
                evidence_grounded_decisions: current.evidence_grounded_decisions.map((item, itemIndex) =>
                  itemIndex === index ? { ...item, evidence_item_ids: selected } : item
                ),
              }))}
            />
          </div>
        ))}
      </ExperimentSection>

      {!approvalReady && (
        <div className="approval-readiness">
          批准前必须确定设计类型，并填写效应量指标、预期效应量、α 和目标检验效能。
        </div>
      )}
      <label>
        实验方案复核备注
        <textarea rows={3} value={note} onChange={(event) => setNote(event.target.value)} />
      </label>
      <div className="evidence-review-actions">
        <button
          disabled={loading || note.trim().length < 3}
          onClick={() => onReview(content, "needs_revision", note)}
        >
          标记需修订
        </button>
        <button
          className="approve-evidence"
          disabled={loading || !approvalReady}
          onClick={() => onReview(content, "approved", note)}
        >
          批准实验方案
        </button>
      </div>
    </section>
  );
}

function ExperimentSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="experiment-section">
      <h4>{title}</h4>
      {children}
    </div>
  );
}

function EvidenceReferencePicker({
  matrix,
  selected,
  onChange,
}: {
  matrix: EvidenceMatrixRow[];
  selected: string[];
  onChange: (selected: string[]) => void;
}) {
  return (
    <div className="evidence-reference-picker">
      <span>证据引用</span>
      {matrix.map((row) => {
        const checked = selected.includes(row.evidence_item_id);
        return (
          <label key={row.evidence_item_id}>
            <input
              type="checkbox"
              checked={checked}
              onChange={() => onChange(
                checked
                  ? selected.filter((id) => id !== row.evidence_item_id)
                  : [...selected, row.evidence_item_id],
              )}
            />
            {row.citation}
          </label>
        );
      })}
    </div>
  );
}

function StringListField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string[];
  onChange: (value: string[]) => void;
}) {
  return (
    <label>
      {label} <small>每行一项</small>
      <textarea
        rows={4}
        value={value.join("\n")}
        onChange={(event) => onChange(
          event.target.value.split("\n").map((item) => item.trim()).filter(Boolean),
        )}
      />
    </label>
  );
}

function NumericNullableField({
  label,
  value,
  onChange,
  min,
  max,
  step,
}: {
  label: string;
  value: number | null;
  onChange: (value: number | null) => void;
  min?: number;
  max?: number;
  step?: number;
}) {
  return (
    <label>
      {label}
      <input
        type="number"
        value={value ?? ""}
        min={min}
        max={max}
        step={step}
        onChange={(event) => onChange(event.target.value ? Number(event.target.value) : null)}
      />
    </label>
  );
}

function StudyPreparationPanel({
  experimentPlan,
  preparation,
  loading,
  onCalculatePower,
  onReviewPower,
  onGenerateContract,
  onReviewContract,
  onDownloadTemplate,
}: {
  experimentPlan: ExperimentPlan;
  preparation: StudyPreparation | null;
  loading: boolean;
  onCalculatePower: (request: PowerAnalysisRequest) => void;
  onReviewPower: (status: "approved" | "needs_revision", note: string) => void;
  onGenerateContract: () => void;
  onReviewContract: (
    content: DataContractContent,
    status: "approved" | "needs_revision",
    note: string,
  ) => void;
  onDownloadTemplate: () => void;
}) {
  const defaultTest: PowerTestType = experimentPlan.design_type === "within_subjects"
    ? "paired_t"
    : "independent_t";
  const [request, setRequest] = useState<PowerAnalysisRequest>({
    test_type: preparation?.power_analysis?.request.test_type ?? defaultTest,
    effect_size: preparation?.power_analysis?.request.effect_size
      ?? experimentPlan.sample_size_planning.expected_effect_size
      ?? 0.5,
    alpha: preparation?.power_analysis?.request.alpha
      ?? experimentPlan.sample_size_planning.alpha
      ?? 0.05,
    target_power: preparation?.power_analysis?.request.target_power
      ?? experimentPlan.sample_size_planning.target_power
      ?? 0.8,
    alternative: preparation?.power_analysis?.request.alternative ?? "two-sided",
    groups: preparation?.power_analysis?.request.groups
      ?? Math.max(2, experimentPlan.conditions.length),
    allocation_ratio: preparation?.power_analysis?.request.allocation_ratio ?? 1,
    attrition_rate: preparation?.power_analysis?.request.attrition_rate
      ?? experimentPlan.sample_size_planning.attrition_allowance
      ?? 0,
    sensitivity_effect_sizes: preparation?.power_analysis?.request.sensitivity_effect_sizes
      ?? [0.3, 0.5, 0.7],
    sensitivity_powers: preparation?.power_analysis?.request.sensitivity_powers
      ?? [0.8, 0.9],
  });
  const [powerNote, setPowerNote] = useState(
    preparation?.power_analysis?.reviewer_note ?? "",
  );

  return (
    <section className="preparation-panel">
      <div className="evidence-item-heading">
        <div>
          <span className="section-kicker">研究执行准备</span>
          <h3>确定性功效分析与数据契约</h3>
        </div>
      </div>

      <div className="preparation-section">
        <h4>功效分析参数</h4>
        <div className="power-grid">
          <label>
            统计检验
            <select
              value={request.test_type}
              onChange={(event) => setRequest((current) => ({
                ...current,
                test_type: event.target.value as PowerTestType,
                groups: event.target.value === "one_way_anova" ? Math.max(3, current.groups) : 2,
                allocation_ratio: 1,
                alternative: event.target.value === "one_way_anova" ? "two-sided" : current.alternative,
              }))}
            >
              <option value="independent_t">独立样本 t 检验</option>
              <option value="paired_t">配对样本 t 检验</option>
              <option value="one_way_anova">平衡单因素 ANOVA</option>
              <option value="correlation">相关分析（Fisher z 近似）</option>
            </select>
          </label>
          <label>
            效应量
            <input
              type="number"
              min={0.001}
              max={request.test_type === "correlation" ? 0.999 : undefined}
              step={0.01}
              value={request.effect_size}
              onChange={(event) => setRequest((current) => ({
                ...current,
                effect_size: Number(event.target.value),
              }))}
            />
          </label>
          <label>
            α
            <input
              type="number"
              min={0.001}
              max={0.999}
              step={0.001}
              value={request.alpha}
              onChange={(event) => setRequest((current) => ({ ...current, alpha: Number(event.target.value) }))}
            />
          </label>
          <label>
            目标效能
            <input
              type="number"
              min={0.01}
              max={0.99}
              step={0.01}
              value={request.target_power}
              onChange={(event) => setRequest((current) => ({ ...current, target_power: Number(event.target.value) }))}
            />
          </label>
          <label>
            检验方向
            <select
              value={request.alternative}
              disabled={request.test_type === "one_way_anova"}
              onChange={(event) => setRequest((current) => ({
                ...current,
                alternative: event.target.value as PowerAnalysisRequest["alternative"],
              }))}
            >
              <option value="two-sided">双侧</option>
              <option value="larger">单侧：较大</option>
              <option value="smaller">单侧：较小</option>
            </select>
          </label>
          <label>
            组数
            <input
              type="number"
              min={2}
              max={12}
              disabled={request.test_type !== "one_way_anova"}
              value={request.groups}
              onChange={(event) => setRequest((current) => ({ ...current, groups: Number(event.target.value) }))}
            />
          </label>
          <label>
            组间分配比
            <input
              type="number"
              min={0.1}
              max={10}
              step={0.1}
              disabled={request.test_type !== "independent_t"}
              value={request.allocation_ratio}
              onChange={(event) => setRequest((current) => ({ ...current, allocation_ratio: Number(event.target.value) }))}
            />
          </label>
          <label>
            预计脱落率
            <input
              type="number"
              min={0}
              max={0.99}
              step={0.01}
              value={request.attrition_rate}
              onChange={(event) => setRequest((current) => ({ ...current, attrition_rate: Number(event.target.value) }))}
            />
          </label>
        </div>
        <div className="field-grid">
          <NumberListField
            label="敏感性效应量"
            value={request.sensitivity_effect_sizes}
            onChange={(value) => setRequest((current) => ({ ...current, sensitivity_effect_sizes: value }))}
          />
          <NumberListField
            label="敏感性目标效能"
            value={request.sensitivity_powers}
            onChange={(value) => setRequest((current) => ({ ...current, sensitivity_powers: value }))}
          />
        </div>
        <button
          className="primary-button compact"
          disabled={loading || request.effect_size <= 0}
          onClick={() => onCalculatePower(request)}
        >
          {preparation?.power_analysis ? "重新计算" : "计算所需样本量"}
        </button>
      </div>

      {preparation?.power_analysis && (
        <PowerAnalysisResult
          analysis={preparation.power_analysis}
          loading={loading}
          note={powerNote}
          onNote={setPowerNote}
          onReview={onReviewPower}
        />
      )}

      <div className="preparation-section">
        <div className="section-action-heading">
          <div>
            <h4>数据契约</h4>
            <p>定义每列的数据类型、编码、范围、敏感性和采集来源。</p>
          </div>
          {!preparation?.data_contract && (
            <button disabled={loading} onClick={onGenerateContract}>生成数据字典</button>
          )}
        </div>
        {preparation?.data_contract && (
          <DataContractEditor
            contract={preparation.data_contract}
            loading={loading}
            onReview={onReviewContract}
            onDownload={onDownloadTemplate}
          />
        )}
      </div>
    </section>
  );
}

function PowerAnalysisResult({
  analysis,
  loading,
  note,
  onNote,
  onReview,
}: {
  analysis: PowerAnalysis;
  loading: boolean;
  note: string;
  onNote: (value: string) => void;
  onReview: (status: "approved" | "needs_revision", note: string) => void;
}) {
  const primary = analysis.primary_result;
  return (
    <div className="preparation-section power-results">
      <div className="evidence-item-heading">
        <div>
          <h4>功效分析结果</h4>
          <small>{analysis.method}</small>
        </div>
        <span className={`evidence-status ${analysis.status}`}>
          {preparationStatusLabel(analysis.status)}
        </span>
      </div>
      {analysis.status === "stale" && <div className="approval-readiness">实验方案已变化，请重新计算。</div>}
      <div className="power-result-summary">
        <div><span>原始总样本量</span><strong>{primary.nominal_total_n}</strong></div>
        <div><span>脱落调整后</span><strong>{primary.adjusted_total_n}</strong></div>
        <div><span>原始分组</span><strong>{primary.nominal_per_group.join(" / ")}</strong></div>
        <div><span>调整后分组</span><strong>{primary.adjusted_per_group.join(" / ")}</strong></div>
      </div>
      <div className="matrix-scroll">
        <table className="sensitivity-table">
          <thead><tr><th>效应量</th><th>目标效能</th><th>原始 N</th><th>调整后 N</th><th>调整后分组</th></tr></thead>
          <tbody>
            {[primary, ...analysis.sensitivity_results].map((scenario, index) => (
              <tr key={`${scenario.effect_size}-${scenario.target_power}-${index}`}>
                <td>{scenario.effect_size.toFixed(3)}</td>
                <td>{scenario.target_power.toFixed(2)}</td>
                <td>{scenario.nominal_total_n}</td>
                <td>{scenario.adjusted_total_n}</td>
                <td>{scenario.adjusted_per_group.join(" / ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="package-versions">
        {Object.entries(analysis.package_versions).map(([name, version]) => (
          <span key={name}>{name} {version}</span>
        ))}
      </div>
      <label>
        复核备注
        <textarea rows={2} value={note} onChange={(event) => onNote(event.target.value)} />
      </label>
      <div className="evidence-review-actions">
        <button disabled={loading || note.trim().length < 3} onClick={() => onReview("needs_revision", note)}>
          标记需修订
        </button>
        <button className="approve-evidence" disabled={loading || analysis.status === "stale"} onClick={() => onReview("approved", note)}>
          批准功效分析
        </button>
      </div>
    </div>
  );
}

function DataContractEditor({
  contract,
  loading,
  onReview,
  onDownload,
}: {
  contract: DataContract;
  loading: boolean;
  onReview: (
    content: DataContractContent,
    status: "approved" | "needs_revision",
    note: string,
  ) => void;
  onDownload: () => void;
}) {
  const [content, setContent] = useState<DataContractContent>({
    row_grain: contract.row_grain,
    primary_key_fields: contract.primary_key_fields,
    fields: contract.fields,
    collection_notes: contract.collection_notes,
  });
  const [note, setNote] = useState(contract.reviewer_note ?? "");
  return (
    <div className="data-contract-editor">
      <div className="evidence-item-heading">
        <span className={`evidence-status ${contract.status}`}>
          {preparationStatusLabel(contract.status)}
        </span>
      </div>
      {contract.status === "stale" && <div className="approval-readiness">实验方案已变化，请重新生成数据契约。</div>}
      <label>
        每行数据代表什么
        <textarea
          rows={2}
          value={content.row_grain}
          onChange={(event) => setContent((current) => ({ ...current, row_grain: event.target.value }))}
        />
      </label>
      <StringListField
        label="联合主键字段"
        value={content.primary_key_fields}
        onChange={(value) => setContent((current) => ({ ...current, primary_key_fields: value }))}
      />
      <div className="data-field-list">
        {content.fields.map((field, index) => (
          <div className="data-field-card" key={`${field.key}-${index}`}>
            <div className="field-grid">
              <label>
                字段名
                <input
                  value={field.key}
                  onChange={(event) => setContent((current) => ({
                    ...current,
                    fields: current.fields.map((item, itemIndex) => itemIndex === index ? { ...item, key: event.target.value } : item),
                  }))}
                />
              </label>
              <label>
                中文标签
                <input
                  value={field.label}
                  onChange={(event) => setContent((current) => ({
                    ...current,
                    fields: current.fields.map((item, itemIndex) => itemIndex === index ? { ...item, label: event.target.value } : item),
                  }))}
                />
              </label>
            </div>
            <div className="field-grid">
              <label>
                数据类型
                <select
                  value={field.data_type}
                  onChange={(event) => setContent((current) => ({
                    ...current,
                    fields: current.fields.map((item, itemIndex) => itemIndex === index ? { ...item, data_type: event.target.value as DataField["data_type"] } : item),
                  }))}
                >
                  <option value="string">文本</option>
                  <option value="integer">整数</option>
                  <option value="float">数值</option>
                  <option value="category">分类</option>
                  <option value="boolean">布尔</option>
                  <option value="datetime">日期时间</option>
                </select>
              </label>
              <label>
                单位
                <input
                  value={field.unit ?? ""}
                  onChange={(event) => setContent((current) => ({
                    ...current,
                    fields: current.fields.map((item, itemIndex) => itemIndex === index ? { ...item, unit: event.target.value || null } : item),
                  }))}
                />
              </label>
            </div>
            <div className="field-flags">
              <label><input type="checkbox" checked={field.required} onChange={(event) => setContent((current) => ({ ...current, fields: current.fields.map((item, itemIndex) => itemIndex === index ? { ...item, required: event.target.checked } : item) }))} />必填</label>
              <label><input type="checkbox" checked={field.sensitive} onChange={(event) => setContent((current) => ({ ...current, fields: current.fields.map((item, itemIndex) => itemIndex === index ? { ...item, sensitive: event.target.checked } : item) }))} />敏感字段</label>
            </div>
            <div className="field-grid">
              <StringListField
                label="分类编码"
                value={field.categories}
                onChange={(value) => setContent((current) => ({ ...current, fields: current.fields.map((item, itemIndex) => itemIndex === index ? { ...item, categories: value } : item) }))}
              />
              <StringListField
                label="缺失值编码"
                value={field.missing_values}
                onChange={(value) => setContent((current) => ({ ...current, fields: current.fields.map((item, itemIndex) => itemIndex === index ? { ...item, missing_values: value } : item) }))}
              />
            </div>
            <label>
              测量时点
              <input value={field.measurement_timing} onChange={(event) => setContent((current) => ({ ...current, fields: current.fields.map((item, itemIndex) => itemIndex === index ? { ...item, measurement_timing: event.target.value } : item) }))} />
            </label>
            <label>
              数据来源
              <textarea rows={2} value={field.source} onChange={(event) => setContent((current) => ({ ...current, fields: current.fields.map((item, itemIndex) => itemIndex === index ? { ...item, source: event.target.value } : item) }))} />
            </label>
            <StringListField
              label="校验规则"
              value={field.validation_rules}
              onChange={(value) => setContent((current) => ({ ...current, fields: current.fields.map((item, itemIndex) => itemIndex === index ? { ...item, validation_rules: value } : item) }))}
            />
          </div>
        ))}
      </div>
      <StringListField
        label="采集说明"
        value={content.collection_notes}
        onChange={(value) => setContent((current) => ({ ...current, collection_notes: value }))}
      />
      <label>
        复核备注
        <textarea rows={2} value={note} onChange={(event) => setNote(event.target.value)} />
      </label>
      <div className="evidence-review-actions contract-actions">
        {contract.status === "approved" && (
          <button className="download-template" disabled={loading} onClick={onDownload}>下载 CSV 模板</button>
        )}
        <button disabled={loading || note.trim().length < 3} onClick={() => onReview(content, "needs_revision", note)}>标记需修订</button>
        <button className="approve-evidence" disabled={loading || contract.status === "stale"} onClick={() => onReview(content, "approved", note)}>批准数据契约</button>
      </div>
    </div>
  );
}

function NumberListField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number[];
  onChange: (value: number[]) => void;
}) {
  return (
    <label>
      {label} <small>逗号分隔</small>
      <input
        value={value.join(", ")}
        onChange={(event) => onChange(
          event.target.value.split(",").map((item) => Number(item.trim())).filter((item) => Number.isFinite(item) && item > 0),
        )}
      />
    </label>
  );
}

function preparationStatusLabel(status: PreparationStatus) {
  return {
    pending_review: "待复核",
    approved: "已批准",
    needs_revision: "需修订",
    stale: "已过期",
  }[status];
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

