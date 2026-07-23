import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  Brain,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Gauge,
  GraduationCap,
  HelpCircle,
  Layers3,
  Play,
} from "lucide-react";
import "./styles.css";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

function StatCard({ icon: Icon, label, value, tone, hint, numericValue = 0 }) {
  return (
    <section className={`stat-card stat-card-${tone}`}>
      <div className="stat-header">
        <div className="stat-label">
          <Icon size={18} />
          <span>{label}</span>
        </div>
        <strong>{value}</strong>
      </div>
      <div className="stat-meter" aria-hidden="true">
        <span style={{ width: `${Math.max(0, Math.min(100, numericValue))}%` }} />
      </div>
      <p>{hint}</p>
    </section>
  );
}

function App() {
  const [health, setHealth] = useState("checking");
  const [modules, setModules] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [activeModuleId, setActiveModuleId] = useState(null);
  const [activeTask, setActiveTask] = useState(null);
  const [session, setSession] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [selectedChoice, setSelectedChoice] = useState("");
  const [codeAnswer, setCodeAnswer] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState("");
  const [clock, setClock] = useState(Date.now());
  const taskStartedAt = useRef(Date.now());

  useEffect(() => {
    Promise.all([
      fetch(`${API_URL}/health/`).then((response) => response.json()),
      fetch(`${API_URL}/learning/modules/`).then((response) => response.json()),
      fetch(`${API_URL}/learning/tasks/`).then((response) => response.json()),
    ])
      .then(async ([healthResponse, moduleResponse, taskResponse]) => {
        setHealth(healthResponse.status);
        setModules(moduleResponse.modules ?? []);
        setTasks(taskResponse.tasks ?? []);

        const storedToken = window.localStorage.getItem("fuzzyTutorSessionToken");
        let sessionResponse = null;
        if (storedToken) {
          const restoreResponse = await fetch(`${API_URL}/learning/sessions/${storedToken}/`);
          if (restoreResponse.ok) {
            sessionResponse = await restoreResponse.json();
          } else {
            window.localStorage.removeItem("fuzzyTutorSessionToken");
          }
        }
        if (!sessionResponse) {
          const createResponse = await fetch(`${API_URL}/learning/sessions/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
          });
          sessionResponse = await createResponse.json();
          window.localStorage.setItem("fuzzyTutorSessionToken", sessionResponse.sessionToken);
        }

        setSession(sessionResponse);
        setActiveModuleId(sessionResponse.currentModuleId);
        setActiveTask(sessionResponse.currentTask);
        if (sessionResponse.completedTaskCount > 0) {
          setEvaluation({
            knowledgeMastery: sessionResponse.aggregateMastery,
            systemCognitiveFriction: sessionResponse.aggregateFriction,
            recommendation: sessionResponse.latestRecommendation,
          });
        }
      })
      .catch(() => setHealth("offline"));
  }, []);

  useEffect(() => {
    const intervalId = window.setInterval(() => setClock(Date.now()), 1000);
    return () => window.clearInterval(intervalId);
  }, []);

  const activeModule = useMemo(
    () => modules.find((module) => module.id === activeModuleId) ?? null,
    [modules, activeModuleId],
  );

  const moduleTasks = useMemo(
    () => tasks.filter((task) => task.moduleId === activeModuleId),
    [tasks, activeModuleId],
  );

  const activeTaskIndex = Math.max(
    0,
    moduleTasks.findIndex((task) => task.id === activeTask?.id),
  );

  const elapsedSeconds = useMemo(() => {
    if (!activeTask) {
      return 0;
    }

    return Math.max(0, Math.round((clock - taskStartedAt.current) / 1000));
  }, [activeTask, clock]);

  useEffect(() => {
    if (!activeTask) {
      return;
    }

    setSelectedChoice(activeTask.choices?.[0] ?? "");
    setCodeAnswer(activeTask.starterCode ?? "");
    taskStartedAt.current = Date.now();
  }, [activeTask?.id]);

  async function submitAnswer(skipped = false) {
    if (!activeTask || !session || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setActionError("");
    const responseTime = Math.max(0.1, (Date.now() - taskStartedAt.current) / 1000);
    const answerText = activeTask.type === "code" ? codeAnswer.trim() : selectedChoice.trim();
    const payload = {
      sessionToken: session.sessionToken,
      taskId: activeTask.id,
      elapsedTimeSeconds: responseTime,
      assistanceInteractions: skipped ? 0 : activeTask.type === "code" ? 1 : 0,
      completionRatio: skipped ? 0 : answerText.length > 0 ? 1 : 0,
      skipped,
    };
    if (!skipped && activeTask.type === "mcq") {
      payload.selectedChoice = selectedChoice;
    }
    if (!skipped && activeTask.type === "code") {
      payload.answerText = answerText;
    }

    try {
      const response = await fetch(`${API_URL}/learning/submissions/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail ?? "We could not record this task attempt.");
      }

      setEvaluation(result);
      setSession(result.session);
      setActiveModuleId(result.session.currentModuleId);
      setActiveTask(result.nextTask);
    } catch (error) {
      setActionError(error.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  const progressLabel = activeTask ? `${activeTaskIndex + 1} / ${moduleTasks.length}` : "0 / 0";
  const canGoForward = Boolean(activeTask && !isSubmitting && !session?.curriculumComplete);
  const displayedMetrics =
    evaluation ??
    (session?.completedTaskCount > 0
      ? {
          knowledgeMastery: session.aggregateMastery,
          systemCognitiveFriction: session.aggregateFriction,
          recommendation: session.latestRecommendation,
        }
      : null);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Programming Concepts Tutor</p>
          <h1>FuzzyTutor</h1>
        </div>
        <div className={`status status-${health}`}>
          <Activity size={16} />
          <span>API {health}</span>
        </div>
      </header>

      <section className="workspace">
        <aside className="module-panel">
          <div className="panel-heading compact">
            <Layers3 size={22} />
            <div>
              <p>Curriculum</p>
              <h2>Modules</h2>
            </div>
          </div>

          <div className="module-list">
            {modules.map((module) => {
              const active = module.id === activeModuleId;

              return (
                <button
                  key={module.id}
                  type="button"
                  className={`module-item ${active ? "active" : ""}`}
                  disabled={!active}
                >
                  <div className="module-item-head">
                    <span>M{module.id}</span>
                    <h3>{module.title}</h3>
                  </div>
                  <div className="module-score-row">
                    <span className="score-pill">Score {module.score}%</span>
                    <span className="score-pill muted">Aggregate {module.aggregateScore}%</span>
                  </div>
                  <small>{module.concepts?.join(" · ")}</small>
                </button>
              );
            })}
          </div>
        </aside>

        <section className="task-panel">
          <div className="task-window">
            <div className="task-header">
              <GraduationCap size={24} />
              <div>
                <p>
                  {activeModule?.title ?? "Select a module"} · {progressLabel}
                </p>
                <h2>{activeTask?.prompt ?? "Choose a module to load its first task."}</h2>
              </div>
            </div>

            <div className="task-meta">
              <span>{activeTask?.type?.toUpperCase() ?? "TASK"}</span>
              <span>{activeTask?.difficulty ?? "foundation"}</span>
              <span>{activeTask?.baselineTimeSeconds ?? 0}s baseline</span>
            </div>

            {activeTask?.type === "mcq" ? (
              <div className="choices">
                {(activeTask?.choices ?? []).map((choice) => (
                  <label key={choice} className={selectedChoice === choice ? "choice selected" : "choice"}>
                    <input
                      type="radio"
                      name="choice"
                      value={choice}
                      checked={selectedChoice === choice}
                      onChange={(event) => setSelectedChoice(event.target.value)}
                    />
                    <span>{choice}</span>
                  </label>
                ))}
              </div>
            ) : activeTask ? (
              <div className="code-answer">
                <textarea
                  value={codeAnswer}
                  onChange={(event) => setCodeAnswer(event.target.value)}
                  rows={11}
                  spellCheck="false"
                />
                <p>{activeTask?.answerGuide}</p>
              </div>
            ) : (
              <div className="empty-task-state">
                Select a module to begin.
              </div>
            )}

            <div className="task-footer">
              <div className="task-footer-meta">
                <Clock3 size={16} />
                <span>{elapsedSeconds}s elapsed</span>
              </div>
              <div className="task-navigation">
                <button type="button" disabled title="Tasks are recorded in sequence">
                  <ChevronLeft size={16} />
                  Back
                </button>
                <button
                  type="button"
                  onClick={() => submitAnswer(true)}
                  disabled={!canGoForward}
                  title="Skip this question and update your learning metrics"
                >
                  Forward
                  <ChevronRight size={16} />
                </button>
              </div>
              <button
                className="primary-action"
                type="button"
                onClick={() => submitAnswer(false)}
                disabled={!activeTask || isSubmitting}
              >
                <Play size={18} />
                {isSubmitting ? "Saving..." : "Submit response"}
              </button>
            </div>
            {actionError ? <p className="action-error">{actionError}</p> : null}
          </div>
        </section>

        <aside className="xai-panel">
          <div className="panel-heading">
            <Brain size={22} />
            <div>
              <p>Explainable AI</p>
              <h2>Learning state</h2>
            </div>
          </div>

          <StatCard
            icon={Gauge}
            label="Knowledge mastery"
            value={displayedMetrics ? `${displayedMetrics.knowledgeMastery}%` : "-"}
            tone="mastery"
            hint="How ready the learner looks for the next step."
            numericValue={displayedMetrics?.knowledgeMastery ?? 0}
          />
          <StatCard
            icon={HelpCircle}
            label="Cognitive friction"
            value={displayedMetrics ? `${displayedMetrics.systemCognitiveFriction}%` : "-"}
            tone="friction"
            hint="How much strain or hesitation the system detected."
            numericValue={displayedMetrics?.systemCognitiveFriction ?? 0}
          />

          <div className="recommendation">
            <span>{displayedMetrics?.focusState ?? "Waiting for a submission"}</span>
            <p>{displayedMetrics?.recommendation ?? "The next task will adapt after the first response."}</p>
            <strong>{displayedMetrics?.supportMessage ?? "Submit a response to see the fuzzy summary."}</strong>
          </div>
        </aside>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
