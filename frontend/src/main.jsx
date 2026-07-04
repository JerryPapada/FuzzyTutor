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
  const [taskIndexByModule, setTaskIndexByModule] = useState({});
  const [evaluation, setEvaluation] = useState(null);
  const [selectedChoice, setSelectedChoice] = useState("");
  const [codeAnswer, setCodeAnswer] = useState("");
  const [clock, setClock] = useState(Date.now());
  const taskStartedAt = useRef(Date.now());

  useEffect(() => {
    Promise.all([
      fetch(`${API_URL}/health/`).then((response) => response.json()),
      fetch(`${API_URL}/learning/modules/`).then((response) => response.json()),
      fetch(`${API_URL}/learning/tasks/`).then((response) => response.json()),
    ])
      .then(([healthResponse, moduleResponse, taskResponse]) => {
        setHealth(healthResponse.status);
        setModules(moduleResponse.modules ?? []);
        setTasks(taskResponse.tasks ?? []);
        const firstModuleId = moduleResponse.modules?.[0]?.id ?? null;
        setActiveModuleId(firstModuleId);
        setTaskIndexByModule(
          Object.fromEntries((moduleResponse.modules ?? []).map((module) => [module.id, 0])),
        );
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

  const activeTaskIndex = activeModuleId == null ? 0 : taskIndexByModule[activeModuleId] ?? 0;
  const activeTask = moduleTasks[activeTaskIndex] ?? null;

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
    setEvaluation(null);
    taskStartedAt.current = Date.now();
  }, [activeTask?.id]);

  function selectModule(moduleId) {
    setActiveModuleId(moduleId);
    setEvaluation(null);
  }

  function moveTask(direction) {
    if (activeModuleId == null || moduleTasks.length === 0) {
      return;
    }

    setTaskIndexByModule((current) => {
      const currentIndex = current[activeModuleId] ?? 0;
      const nextIndex = direction === "back" ? currentIndex - 1 : currentIndex + 1;
      const boundedIndex = Math.max(0, Math.min(moduleTasks.length - 1, nextIndex));

      return {
        ...current,
        [activeModuleId]: boundedIndex,
      };
    });
  }

  async function submitAnswer() {
    if (!activeTask) {
      return;
    }

    const responseTime = Math.max(0.1, (Date.now() - taskStartedAt.current) / 1000);
    const taskMetricWeight =
      activeTask.difficulty === "foundation" ? 35 : activeTask.difficulty === "intermediate" ? 55 : 75;
    const answerText = activeTask.type === "code" ? codeAnswer.trim() : selectedChoice.trim();

    const response = await fetch(`${API_URL}/fuzzy/evaluate/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        taskMetricWeight,
        historicalGradeAverage: 76,
        relativeResponseTime: responseTime / activeTask.baselineTimeSeconds,
        assistanceInteractions: activeTask.type === "code" ? 1 : 0,
        completionRatio: answerText.length > 0 ? 1 : 0,
        taskType: activeTask.type,
        isCorrect:
          activeTask.type === "mcq"
            ? selectedChoice === activeTask.correctChoice
            : answerText.length > 0,
        selectedChoice,
        answerText,
      }),
    });

    setEvaluation(await response.json());
  }

  const progressLabel = activeTask ? `${activeTaskIndex + 1} / ${moduleTasks.length}` : "0 / 0";
  const canGoBack = activeTaskIndex > 0;
  const canGoForward = activeTaskIndex < moduleTasks.length - 1;

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
                  onClick={() => selectModule(module.id)}
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
                <button type="button" onClick={() => moveTask("back")} disabled={!canGoBack}>
                  <ChevronLeft size={16} />
                  Back
                </button>
                <button type="button" onClick={() => moveTask("forward")} disabled={!canGoForward}>
                  Forward
                  <ChevronRight size={16} />
                </button>
              </div>
              <button className="primary-action" type="button" onClick={submitAnswer} disabled={!activeTask}>
                <Play size={18} />
                Submit response
              </button>
            </div>
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
            value={`${evaluation?.knowledgeMastery ?? "--"}%`}
            tone="mastery"
            hint="How ready the learner looks for the next step."
            numericValue={evaluation?.knowledgeMastery ?? 0}
          />
          <StatCard
            icon={HelpCircle}
            label="Cognitive friction"
            value={`${evaluation?.systemCognitiveFriction ?? "--"}%`}
            tone="friction"
            hint="How much strain or hesitation the system detected."
            numericValue={evaluation?.systemCognitiveFriction ?? 0}
          />

          <div className="recommendation">
            <span>{evaluation?.focusState ?? "Waiting for a submission"}</span>
            <p>{evaluation?.recommendation ?? "The next task will adapt after the first response."}</p>
            <strong>{evaluation?.supportMessage ?? "Submit a response to see the fuzzy summary."}</strong>
          </div>
        </aside>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
