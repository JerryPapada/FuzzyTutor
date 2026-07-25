import React, { useEffect, useMemo, useState, useRef } from "react";
import {
  Brain,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Gauge,
  GraduationCap,
  HelpCircle,
  Layers3,
  Play,
  Check,
  Lock,
  AlertCircle,
} from "lucide-react";
import StatCard from "../components/StatCard";
import Header from "../components/Header";
import useElapsedTimer from "../hooks/useElapsedTimer";
import { fetchHealth } from "../services/healthService";
import { fetchModules, fetchTasks } from "../services/learningService";
import { submitEvaluation } from "../services/fuzzyService";
import "../pages-css/TutorPage.css";

const RECOMMENDATION_LABELS = {
  increase_or_hold_high_tier: "Advance or Maintain High Difficulty Level",
  reduce_difficulty_and_show_support: "Reduce Difficulty Level and Provide Support",
  hold_current_tier: "Maintain Current Difficulty Level",
};

function TutorPage() {
  const [health, setHealth] = useState("checking");
  const [modules, setModules] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [activeModuleId, setActiveModuleId] = useState(null);
  const [taskIndexByModule, setTaskIndexByModule] = useState({});
  const [evaluation, setEvaluation] = useState(null);
  const [moduleScores, setModuleScores] = useState({});
  const [selectedChoice, setSelectedChoice] = useState("");
  const [codeAnswer, setCodeAnswer] = useState("");
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [submittedTaskIds, setSubmittedTaskIds] = useState([]);
  const [skippedTaskIds, setSkippedTaskIds] = useState([]);
  const [notificationMsg, setNotificationMsg] = useState("");
  const [showNotification, setShowNotification] = useState(false);
  const notificationTimeoutRef = useRef(null);

  function triggerNotification(message) {
    setNotificationMsg(message);
    setShowNotification(true);
    if (notificationTimeoutRef.current) {
      clearTimeout(notificationTimeoutRef.current);
    }
    notificationTimeoutRef.current = setTimeout(() => {
      setShowNotification(false);
    }, 5000);
  }

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

  const { elapsedSeconds, taskStartedAt, resetTimer } = useElapsedTimer(activeTask);

  useEffect(() => {
    Promise.all([
      fetchHealth(),
      fetchModules(),
      fetchTasks(),
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
    if (!activeTask) {
      return;
    }

    setSelectedChoice(activeTask.choices?.[0] ?? "");
    setCodeAnswer(activeTask.starterCode ?? "");
    resetTimer();
  }, [activeTask?.id]);

  useEffect(() => {
    setEvaluation(null);
  }, [activeModuleId]);

  function selectModule(moduleId) {
    if (moduleId > activeModuleId) {
      if (moduleId > activeModuleId + 1) {
        return;
      }
      const allTasksSubmitted = moduleTasks.every((task) =>
        submittedTaskIds.includes(task.id)
      );
      if (!allTasksSubmitted) {
        triggerNotification(
          "Please complete all tasks in this module to proceed."
        );
        return;
      }
    }
    setActiveModuleId(moduleId);
  }

  function triggerTaskChange(changeCallback) {
    setIsTransitioning(true);
    setTimeout(() => {
      changeCallback();
      setIsTransitioning(false);
    }, 200); // Matches CSS transition duration
  }

  function goBack() {
    if (activeTask && !submittedTaskIds.includes(activeTask.id)) {
      setSkippedTaskIds((prev) =>
        prev.includes(activeTask.id) ? prev : [...prev, activeTask.id]
      );
    }
    triggerTaskChange(() => {
      moveTask("back");
    });
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

  function advanceToNextTask(wasSubmitted = false, lastEvaluation = null) {
    if (activeModuleId == null || moduleTasks.length === 0) {
      return;
    }

    const updatedSubmittedIds = wasSubmitted
      ? (submittedTaskIds.includes(activeTask.id) ? submittedTaskIds : [...submittedTaskIds, activeTask.id])
      : submittedTaskIds;

    const allTasksSubmitted = moduleTasks.every((task) =>
      updatedSubmittedIds.includes(task.id)
    );

    if (allTasksSubmitted) {
      const evalToUse = lastEvaluation || evaluation;
      if (evalToUse) {
        setModuleScores((prev) => ({
          ...prev,
          [activeModuleId]: {
            score: evalToUse.knowledgeMastery,
            aggregate: evalToUse.systemCognitiveFriction,
          },
        }));
      }

      const currentModuleIdx = modules.findIndex((m) => m.id === activeModuleId);
      if (currentModuleIdx !== -1 && currentModuleIdx < modules.length - 1) {
        const nextModule = modules[currentModuleIdx + 1];
        setActiveModuleId(nextModule.id);
        setTaskIndexByModule((current) => ({
          ...current,
          [nextModule.id]: 0,
        }));
        
        // Scroll the next module smoothly into view (centered)
        setTimeout(() => {
          const nextModuleBtn = document.querySelector(`.module-item[data-id="${nextModule.id}"]`);
          if (nextModuleBtn) {
            nextModuleBtn.scrollIntoView({ behavior: "smooth", block: "center" });
          }
        }, 50);
      } else {
        alert("Congratulations! You have completed all modules.");
      }
    } else {
      if (activeTaskIndex < moduleTasks.length - 1) {
        setTaskIndexByModule((current) => ({
          ...current,
          [activeModuleId]: activeTaskIndex + 1,
        }));
      } else {
        triggerNotification(
          "Please complete all tasks in this module to proceed."
        );
      }
    }
  }

  function skipTask() {
    setSkippedTaskIds((prev) =>
      prev.includes(activeTask.id) ? prev : [...prev, activeTask.id]
    );

    triggerTaskChange(() => {
      advanceToNextTask(false);
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

    const result = await submitEvaluation({
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
    });

    setEvaluation(result);
    setSubmittedTaskIds((prev) =>
      prev.includes(activeTask.id) ? prev : [...prev, activeTask.id]
    );
    setSkippedTaskIds((prev) => prev.filter((id) => id !== activeTask.id));

    triggerTaskChange(() => {
      advanceToNextTask(true, result);
    });
  }

  const progressLabel = activeTask ? `${activeTaskIndex + 1} / ${moduleTasks.length}` : "0 / 0";
  const canGoBack = activeTaskIndex > 0;
  const canGoForward = activeTaskIndex < moduleTasks.length - 1;

  return (
    <main className="app-shell">
      <Header />

      {/* Custom Notification Toast */}
      <div className={`custom-notification ${showNotification ? "show" : ""}`}>
        <div className="custom-notification-icon">
          <AlertCircle size={20} />
        </div>
        <div className="custom-notification-content">
          {notificationMsg}
        </div>
      </div>

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
              const completed = module.id < activeModuleId;
              const locked = module.id > activeModuleId;

              return (
                <button
                  key={module.id}
                  data-id={module.id}
                  type="button"
                  className={`module-item ${active ? "active" : ""} ${completed ? "completed" : ""} ${locked ? "locked" : ""}`}
                  onClick={() => selectModule(module.id)}
                >
                  <div className="module-timeline">
                    <div className="module-indicator">
                      {completed ? (
                        <div className="circle completed">
                          <Check size={14} strokeWidth={3} />
                        </div>
                      ) : active ? (
                        <div className="circle current">
                          <Play size={11} fill="currentColor" style={{ marginLeft: "1.5px" }} />
                        </div>
                      ) : (
                        <div className="circle locked">
                          <Lock size={12} />
                        </div>
                      )}
                      <div className="line" />
                    </div>
                    <div className="module-details">
                      <div className="module-title-row">
                        {active && <span className="current-badge">CURRENT</span>}
                        <h3>{module.title}</h3>
                      </div>
                      <div className="module-score-row">
                        <span className="score-pill">Score {moduleScores[module.id]?.score != null ? `${moduleScores[module.id].score}%` : "-%"}</span>
                        <span className="score-pill muted">Aggregate {moduleScores[module.id]?.aggregate != null ? `${moduleScores[module.id].aggregate}%` : "-%"}</span>
                      </div>
                      <small>{module.concepts?.join(" · ")}</small>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        <section className="task-panel">
          <div className="task-window">
            <div className="task-header">
              <div className="task-header-top">
                <div className="task-header-title">
                  <GraduationCap size={20} />
                  <span>
                    {activeModule?.title ?? "Select a module"} · {progressLabel}
                  </span>
                </div>
                <div className="progress-pills">
                  {moduleTasks.map((task, idx) => {
                    const isActive = idx === activeTaskIndex;
                    const isSubmitted = submittedTaskIds.includes(task.id);
                    const isSkipped = skippedTaskIds.includes(task.id);
                    const statusClass = isActive
                      ? "active"
                      : isSubmitted
                      ? "submitted"
                      : isSkipped
                      ? "skipped"
                      : "";

                    return (
                      <div
                        key={task.id}
                        className={`progress-pill ${statusClass}`}
                      />
                    );
                  })}
                </div>
              </div>
            </div>

            <div className={`task-body-transition ${isTransitioning ? "transitioning" : ""}`} style={{ display: "flex", flexDirection: "column", flexGrow: 1 }}>
              <h2 className="task-prompt">{activeTask?.prompt ?? "Choose a module to load its first task."}</h2>

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
            </div>

            <div className="task-footer">
              <div className="task-footer-meta">
                <Clock3 size={16} />
                <span className="timer-text">{elapsedSeconds}s elapsed</span>
              </div>
              <div className="task-navigation">
                <button type="button" onClick={goBack} disabled={!canGoBack}>
                  <ChevronLeft size={16} />
                  Back
                </button>
                <button type="button" onClick={skipTask} disabled={!activeTask || activeTaskIndex === moduleTasks.length - 1}>
                  Skip
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
            <p>
              {evaluation?.recommendation
                ? (RECOMMENDATION_LABELS[evaluation.recommendation] ?? evaluation.recommendation)
                : "The next task will adapt after the first response."}
            </p>
            <strong>{evaluation?.supportMessage ?? "Submit a response to see the fuzzy summary."}</strong>
          </div>
        </aside>
      </section>
    </main>
  );
}

export default TutorPage;
