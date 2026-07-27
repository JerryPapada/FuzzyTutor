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
  Unlock,
  AlertCircle,
} from "lucide-react";
import StatCard from "../components/StatCard";
import Header from "../components/Header";
import useElapsedTimer from "../hooks/useElapsedTimer";
import { fetchHealth } from "../services/healthService";
import { fetchModules, fetchTasks, createSession, fetchSession, submitSubmission, submitMicroSurvey, fetchSessionReview, revealHint, deleteSession } from "../services/learningService";
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
  const [session, setSession] = useState(null);
  const [sessionToken, setSessionToken] = useState(null);
  const [selectedChoice, setSelectedChoice] = useState("");
  const [codeAnswer, setCodeAnswer] = useState("");
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [submittedTaskIds, setSubmittedTaskIds] = useState([]);
  const [skippedTaskIds, setSkippedTaskIds] = useState([]);
  const [notificationMsg, setNotificationMsg] = useState("");
  const [showNotification, setShowNotification] = useState(false);
  const [surveyDue, setSurveyDue] = useState(false);
  const [showSurveyModal, setShowSurveyModal] = useState(false);
  const [showResetModal, setShowResetModal] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [satisfaction, setSatisfaction] = useState(5);
  const [perceivedDifficulty, setPerceivedDifficulty] = useState(3);
  const [confidence, setConfidence] = useState(5);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [submittingSurvey, setSubmittingSurvey] = useState(false);
  const [showTrace, setShowTrace] = useState(false);
  const [hintState, setHintState] = useState(null);
  const [revealingHint, setRevealingHint] = useState(false);

  useEffect(() => {
    if (session) {
      setHintState(session.hintState);
    }
  }, [session]);
  const [reviewItems, setReviewItems] = useState({});
  const [localAnswers, setLocalAnswers] = useState({});
  const notificationTimeoutRef = useRef(null);

  useEffect(() => {
    if (surveyDue) {
      setSatisfaction(5);
      setPerceivedDifficulty(3);
      setConfidence(5);
      setFeedbackComment("");
      setShowSurveyModal(true);
    } else {
      setShowSurveyModal(false);
    }
  }, [surveyDue]);

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

  const timeline = useMemo(() => {
    if (!session || !activeModuleId) return [];
    const attempts = (session.orderedAttempts || []).filter(att => att.moduleId == activeModuleId);
    return [...attempts.map(att => att.taskId), session.currentTaskId].filter(Boolean);
  }, [session, activeModuleId]);

  const activeTaskIndexInTimeline = useMemo(() => {
    if (!activeTask || timeline.length === 0) return 0;
    return timeline.indexOf(activeTask.id);
  }, [activeTask, timeline]);

  const isReviewMode = useMemo(() => {
    return activeTask && session && activeTask.id !== session.currentTaskId;
  }, [activeTask, session]);

  const canGoForwardReview = useMemo(() => {
    if (!activeTask || !session) return false;
    return activeTaskIndexInTimeline < timeline.length - 1;
  }, [activeTask, session, activeTaskIndexInTimeline, timeline]);

  const { elapsedSeconds, taskStartedAt, resetTimer } = useElapsedTimer(activeTask);

  useEffect(() => {
    async function initApp() {
      try {
        const [healthResponse, moduleResponse, taskResponse] = await Promise.all([
          fetchHealth(),
          fetchModules(),
          fetchTasks(),
        ]);

        setHealth(healthResponse.status);
        const fetchedModules = moduleResponse.modules ?? [];
        const fetchedTasks = taskResponse.tasks ?? [];
        setModules(fetchedModules);
        setTasks(fetchedTasks);

        // Load token from localStorage
        const storedToken = localStorage.getItem("sessionToken");
        const justReset = localStorage.getItem("justReset");
        let activeSession = null;

        if (storedToken) {
          try {
            activeSession = await fetchSession(storedToken);
          } catch (err) {
            console.warn("Stored session invalid or expired, creating new one.", err);
          }
          if (justReset === "true") {
            localStorage.removeItem("justReset");
          }
        } else {
          // No stored token: new user
          if (justReset === "true") {
            localStorage.removeItem("justReset");
          } else {
            setShowHelpModal(true);
          }
        }

        if (!activeSession) {
          activeSession = await createSession();
        }

        setSession(activeSession);
        setSessionToken(activeSession.sessionToken);
        localStorage.setItem("sessionToken", activeSession.sessionToken);
        if (activeSession.surveyDue != null) {
          setSurveyDue(activeSession.surveyDue);
        }
        if (activeSession.submittedTaskIds) {
          setSubmittedTaskIds(activeSession.submittedTaskIds);
        }
        if (activeSession.skippedTaskIds) {
          setSkippedTaskIds(activeSession.skippedTaskIds);
        }

        const storedAnswers = localStorage.getItem(`answers_${activeSession.sessionToken}`);
        if (storedAnswers) {
          setLocalAnswers(JSON.parse(storedAnswers));
        }

        // Fetch review items (skipped or incorrect MCQs) on boot
        try {
          const reviewData = await fetchSessionReview(activeSession.sessionToken);
          const reviewMap = {};
          if (reviewData && reviewData.items) {
            reviewData.items.forEach((item) => {
              reviewMap[item.task.id] = item;
            });
          }
          setReviewItems(reviewMap);
        } catch (reviewErr) {
          console.warn("Failed to fetch session review items on boot", reviewErr);
        }

        const targetModuleId = activeSession.currentModuleId ?? fetchedModules[0]?.id ?? null;
        setActiveModuleId(targetModuleId);

        // Initialize taskIndexByModule
        const initialIndices = Object.fromEntries(
          fetchedModules.map((module) => [module.id, 0])
        );

        if (targetModuleId != null) {
          const modTasks = fetchedTasks.filter((t) => t.moduleId === targetModuleId);
          const taskIdx = modTasks.findIndex((t) => t.id === activeSession.currentTaskId);
          if (taskIdx !== -1) {
            initialIndices[targetModuleId] = taskIdx;
          }
        }
        setTaskIndexByModule(initialIndices);

      } catch (error) {
        console.error("Initialization failed", error);
        setHealth("offline");
      }
    }

    initApp();
  }, []);

  useEffect(() => {
    if (!activeTask) {
      return;
    }

    const isReview = session && activeTask.id !== session.currentTaskId;
    if (isReview) {
      const persistedAttempt = (session.orderedAttempts || []).find(
        (attempt) => attempt.taskId === activeTask.id,
      );
      const learnerAnswer =
        reviewItems[activeTask.id]?.learnerAnswer
        ?? persistedAttempt?.learnerAnswer
        ?? {};
      const submittedVal =
        (activeTask.type === "mcq"
          ? learnerAnswer.selectedChoice
          : learnerAnswer.answerText)
        ?? localAnswers[activeTask.id]
        ?? "";
      setSelectedChoice(activeTask.type === "mcq" ? submittedVal : "");
      setCodeAnswer(activeTask.type === "code" ? submittedVal : "");
    } else {
      setSelectedChoice(localAnswers[activeTask.id] || activeTask.choices?.[0] || "");
      setCodeAnswer(localAnswers[activeTask.id] || activeTask.starterCode || "");
      resetTimer();
    }
  }, [activeTask?.id, session?.currentTaskId, reviewItems, localAnswers]);

  useEffect(() => {
    setEvaluation(null);
  }, [activeModuleId]);

  function selectModule(moduleId) {
    const progress = session?.moduleProgress?.find((p) => p.moduleId === moduleId);
    const isUnlocked = progress && progress.status !== "not_started";
    const isCurrent = session && moduleId === session.currentModuleId;

    if (!isUnlocked && !isCurrent) {
      triggerNotification("This module is locked. Complete the current module tasks to unlock.");
      return;
    }

    setActiveModuleId(moduleId);

    setTaskIndexByModule((current) => {
      const selectedModuleTasks = tasks.filter((t) => t.moduleId === moduleId);
      let targetIdx = 0;
      if (session && moduleId === session.currentModuleId) {
        const currentTaskIdx = selectedModuleTasks.findIndex((t) => t.id === session.currentTaskId);
        if (currentTaskIdx !== -1) {
          targetIdx = currentTaskIdx;
        }
      }
      return {
        ...current,
        [moduleId]: targetIdx,
      };
    });
  }

  function triggerTaskChange(changeCallback) {
    setIsTransitioning(true);
    setTimeout(() => {
      changeCallback();
      setIsTransitioning(false);
    }, 200); // Matches CSS transition duration
  }

  function goBack() {
    triggerTaskChange(() => {
      moveTask("back");
    });
  }

  function goForwardReview() {
    triggerTaskChange(() => {
      moveTask("forward");
    });
  }

  function moveTask(direction) {
    if (activeModuleId == null || moduleTasks.length === 0 || timeline.length === 0 || !activeTask) {
      return;
    }

    const currentIndex = timeline.indexOf(activeTask.id);
    if (currentIndex === -1) return;

    const nextIndex = direction === "back" ? currentIndex - 1 : currentIndex + 1;
    if (nextIndex < 0 || nextIndex >= timeline.length) return;

    const targetTaskId = timeline[nextIndex];
    const targetIdxInModule = moduleTasks.findIndex(t => t.id === targetTaskId);

    if (targetIdxInModule !== -1) {
      setTaskIndexByModule((current) => ({
        ...current,
        [activeModuleId]: targetIdxInModule,
      }));
    }
  }

  function transitionToNextTask(nextTask) {
    if (!nextTask) return;

    // Find the next task's module tasks from our catalog
    const nextModuleTasks = tasks.filter((t) => t.moduleId === nextTask.moduleId);
    const nextTaskIdx = nextModuleTasks.findIndex((t) => t.id === nextTask.id);

    // If module is changing, handle scrolling and transition
    if (nextTask.moduleId !== activeModuleId) {
      setTimeout(() => {
        const nextModuleBtn = document.querySelector(`.module-item[data-id="${nextTask.moduleId}"]`);
        if (nextModuleBtn) {
          nextModuleBtn.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }, 100);
    }

    triggerTaskChange(() => {
      setActiveModuleId(nextTask.moduleId);
      setTaskIndexByModule((current) => ({
        ...current,
        [nextTask.moduleId]: nextTaskIdx !== -1 ? nextTaskIdx : 0,
      }));
    });
  }

  async function skipTask() {
    if (!activeTask || !sessionToken) {
      return;
    }

    const responseTime = Math.max(0.1, (Date.now() - taskStartedAt.current) / 1000);

    try {
      const result = await submitSubmission({
        sessionToken,
        taskId: activeTask.id,
        elapsedTimeSeconds: responseTime,
        skipped: true,
        completionRatio: 0.0,
      });

      setEvaluation(result);
      
      if (result.session) {
        setSession(result.session);
        if (result.session.submittedTaskIds) {
          setSubmittedTaskIds(result.session.submittedTaskIds);
        }
        if (result.session.skippedTaskIds) {
          setSkippedTaskIds(result.session.skippedTaskIds);
        }
      }
      if (result.surveyDue != null) {
        setSurveyDue(result.surveyDue);
      }

      // Display module decision notification if any module is exited
      if (result.moduleDecision && result.moduleDecision.outcome !== "continue") {
        if (result.moduleDecision.outcome === "mastery_exit") {
          triggerNotification("Congratulations! You mastered the module early!");
        } else if (result.moduleDecision.outcome === "bank_exhausted") {
          triggerNotification("Module completed. Moving to next module.");
        }
      }

      if (result.adaptation?.curriculumComplete || result.session?.curriculumComplete) {
        alert("Congratulations! You have completed all modules.");
      } else {
        transitionToNextTask(result.nextTask);
      }

      // Fetch updated review items in the background
      fetchSessionReview(sessionToken).then((reviewData) => {
        const reviewMap = {};
        if (reviewData && reviewData.items) {
          reviewData.items.forEach((item) => {
            reviewMap[item.task.id] = item;
          });
        }
        setReviewItems(reviewMap);
      }).catch((reviewErr) => {
        console.warn("Failed to fetch session review items after skip", reviewErr);
      });

    } catch (error) {
      console.error("Failed to skip task:", error);
      triggerNotification("An error occurred while skipping the task.");
    }
  }

  async function submitAnswer() {
    if (!activeTask || !sessionToken) {
      return;
    }

    const responseTime = Math.max(0.1, (Date.now() - taskStartedAt.current) / 1000);
    const answerText = activeTask.type === "code" ? codeAnswer.trim() : selectedChoice.trim();

    try {
      const result = await submitSubmission({
        sessionToken,
        taskId: activeTask.id,
        elapsedTimeSeconds: responseTime,
        skipped: false,
        completionRatio: answerText.length > 0 ? 1 : 0,
        selectedChoice: activeTask.type === "mcq" ? selectedChoice : "",
        answerText: activeTask.type === "code" ? codeAnswer : "",
      });

      setEvaluation(result);

      if (result.session) {
        setSession(result.session);
        if (result.session.submittedTaskIds) {
          setSubmittedTaskIds(result.session.submittedTaskIds);
        }
        if (result.session.skippedTaskIds) {
          setSkippedTaskIds(result.session.skippedTaskIds);
        }
      }
      if (result.surveyDue != null) {
        setSurveyDue(result.surveyDue);
      }

      // Display module decision notification if any module is exited
      if (result.moduleDecision && result.moduleDecision.outcome !== "continue") {
        if (result.moduleDecision.outcome === "mastery_exit") {
          triggerNotification("Congratulations! You mastered the module early!");
        } else if (result.moduleDecision.outcome === "bank_exhausted") {
          triggerNotification("Module completed. Moving to next module.");
        }
      }

      if (result.adaptation?.curriculumComplete || result.session?.curriculumComplete) {
        alert("Congratulations! You have completed all modules.");
      } else {
        transitionToNextTask(result.nextTask);
      }

      // Fetch updated review items in the background
      fetchSessionReview(sessionToken).then((reviewData) => {
        const reviewMap = {};
        if (reviewData && reviewData.items) {
          reviewData.items.forEach((item) => {
            reviewMap[item.task.id] = item;
          });
        }
        setReviewItems(reviewMap);
      }).catch((reviewErr) => {
        console.warn("Failed to fetch session review items after submission", reviewErr);
      });
    } catch (error) {
      console.error("Submission failed:", error);
      triggerNotification(error.message || "An error occurred during submission.");
    }
  }

  async function handleSurveySubmit(e) {
    if (e) e.preventDefault();
    if (!sessionToken) return;

    setSubmittingSurvey(true);
    try {
      const result = await submitMicroSurvey({
        sessionToken,
        satisfactionScore: satisfaction,
        perceivedDifficulty: perceivedDifficulty,
        confidenceScore: confidence,
        comment: feedbackComment,
      });

      triggerNotification("Feedback submitted! Thank you.");
      setSurveyDue(result.surveyDue);
      setShowSurveyModal(false);

      // Refresh the session state from backend
      const updatedSession = await fetchSession(sessionToken);
      setSession(updatedSession);
      if (updatedSession.submittedTaskIds) {
        setSubmittedTaskIds(updatedSession.submittedTaskIds);
      }
      if (updatedSession.skippedTaskIds) {
        setSkippedTaskIds(updatedSession.skippedTaskIds);
      }

    } catch (error) {
      console.error("Survey submission failed:", error);
      triggerNotification(error.message || "Failed to submit survey.");
    } finally {
      setSubmittingSurvey(false);
    }
  }

  async function requestHint() {
    if (!activeTask || !sessionToken || revealingHint) return;

    const responseTime = Math.max(0.1, (Date.now() - taskStartedAt.current) / 1000);
    setRevealingHint(true);
    try {
      const result = await revealHint({
        sessionToken,
        taskId: activeTask.id,
        elapsedTimeSeconds: responseTime,
      });
      setHintState(result.hintState);
      triggerNotification("New hint revealed!");
    } catch (err) {
      console.error("Failed to reveal hint:", err);
      triggerNotification(err.message || "Failed to reveal hint.");
    } finally {
      setRevealingHint(false);
    }
  }
  const progressLabel = activeTask ? `${activeTaskIndexInTimeline + 1} / ${timeline.length}` : "0 / 0";
  const canGoBack = activeTaskIndexInTimeline > 0;
  const canGoForward = activeTaskIndexInTimeline < timeline.length - 1;

  const handleHelp = () => {
    setShowHelpModal(true);
  };

  const handleReset = () => {
    setShowResetModal(true);
  };

  const confirmReset = async () => {
    try {
      if (sessionToken) {
        try {
          await deleteSession(sessionToken);
        } catch (err) {
          console.warn("Backend session deletion failed, clearing locally anyway:", err);
        }
        localStorage.removeItem(`answers_${sessionToken}`);
      }
      localStorage.removeItem("sessionToken");
      localStorage.setItem("justReset", "true");
      window.location.reload();
    } catch (error) {
      console.error("Failed to reset session:", error);
    }
  };

  return (
    <main className="app-shell">
      <Header onHelp={handleHelp} onReset={handleReset} />

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
              const progress = session?.moduleProgress?.find((p) => p.moduleId === module.id);
              const active = module.id === activeModuleId;
              const completed = progress 
                ? (progress.status === "mastered" || progress.status === "completed_bank" || progress.terminal) 
                : module.id < activeModuleId;
              const locked = progress 
                ? (progress.status === "not_started") 
                : module.id > activeModuleId;

              const score = completed && progress ? progress.moduleMastery : null;
              const friction = completed && progress ? progress.moduleFriction : null;

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
                      ) : locked ? (
                        <div className="circle locked">
                          <Lock size={12} />
                        </div>
                      ) : (
                        <div className="circle unlocked">
                          <Play size={11} fill="currentColor" style={{ marginLeft: "1.5px" }} />
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
                        <span className="score-pill">Score {score != null ? `${score}%` : "--%"}</span>
                        <span className="score-pill muted">Aggregate {friction != null ? `${friction}%` : "--%"}</span>
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
                  <span>
                    {activeModule?.title}
                  </span>
                </div>
                <div className="progress-pills">
                  {(() => {
                    const attempts = (session?.orderedAttempts || []).filter(att => att.moduleId == activeModuleId);
                    const activeProgress = session?.moduleProgress?.find((p) => p.moduleId === activeModuleId);
                    const isCompleted = activeProgress
                      ? (activeProgress.status === "mastered" || activeProgress.status === "completed_bank" || activeProgress.terminal)
                      : activeModuleId < session?.currentModuleId;
                    const pillCount = isCompleted ? attempts.length : 15;

                    return Array.from({ length: pillCount }).map((_, idx) => {
                      let activeIdx = attempts.length;
                      if (activeTask && session) {
                        if (activeTask.id !== session.currentTaskId) {
                          const foundIdx = attempts.findIndex(att => att.taskId === activeTask.id);
                          if (foundIdx !== -1) {
                            activeIdx = foundIdx;
                          }
                        }
                      }

                      const isActive = idx === activeIdx;
                      const isAttempted = idx < attempts.length;
                      const attempt = isAttempted ? attempts[idx] : null;
                      const isSubmitted = attempt && !attempt.skipped;
                      const isSkipped = attempt && attempt.skipped;

                      const statusClass = isActive
                        ? "active"
                        : isSubmitted
                        ? "submitted"
                        : isSkipped
                        ? "skipped"
                        : "";

                      return (
                        <div
                          key={idx}
                          className={`progress-pill ${statusClass}`}
                        />
                      );
                    });
                  })()}
                </div>
              </div>
            </div>

            <div className={`task-body-transition ${isTransitioning ? "transitioning" : ""}`} style={{ display: "flex", flexDirection: "column", flexGrow: 1 }}>
              <h2 className="task-prompt">{activeTask?.prompt ?? "Choose a module to load its first task."}</h2>

              <div className="task-meta">
                <span>{activeTask?.type?.toUpperCase() ?? "TASK"}</span>
                <span>{activeTask?.difficulty ?? "foundation"}</span>
                <span>{activeTask?.baselineTimeSeconds ?? 0}s baseline</span>
              </div>              {activeTask?.type === "mcq" ? (
                <div className="choices">
                  {(activeTask?.choices ?? []).map((choice) => (
                    <label key={choice} className={selectedChoice === choice ? "choice selected" : "choice"}>
                      <input
                        type="radio"
                        name="choice"
                        value={choice}
                        checked={selectedChoice === choice}
                        disabled={isReviewMode}
                        onChange={(event) => {
                          const val = event.target.value;
                          setSelectedChoice(val);
                          setLocalAnswers(prev => {
                            const updated = { ...prev, [activeTask.id]: val };
                            localStorage.setItem(`answers_${sessionToken}`, JSON.stringify(updated));
                            return updated;
                          });
                        }}
                      />
                      <span>{choice}</span>
                    </label>
                  ))}
                </div>
              ) : activeTask ? (
                <div className="code-answer">
                  <textarea
                    value={codeAnswer}
                    onChange={(event) => {
                      const val = event.target.value;
                      setCodeAnswer(val);
                      setLocalAnswers(prev => {
                        const updated = { ...prev, [activeTask.id]: val };
                        localStorage.setItem(`answers_${sessionToken}`, JSON.stringify(updated));
                        return updated;
                      });
                    }}
                    rows={11}
                    spellCheck="false"
                    disabled={isReviewMode}
                  />
                </div>
              ) : (
                <div className="empty-task-state">
                  Select a module to begin.
                </div>
              )}

              {/* Active task revealed hints */}
              {!isReviewMode && hintState?.revealedHints && hintState.revealedHints.length > 0 && (
                <div className="active-hints-panel">
                  <h3 className="active-hints-title">Revealed Hints</h3>
                  <div className="active-hints-content">
                    <ul>
                      {hintState.revealedHints.map((hint, idx) => (
                        <li key={idx} className="hint-item-row">
                          <strong className="hint-label-badge">{hint.label}:</strong>
                          <span className="hint-text-val">{hint.text}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Read-Only Review Details */}
              {isReviewMode && reviewItems[activeTask.id] && (
                <div className="review-panel">
                  <h3 className="review-panel-title">Review Analysis</h3>
                  <div className="review-panel-content">
                    {activeTask.type === "mcq" ? (
                      <p><strong>Correct Choice:</strong> <span className="correct-highlight">{reviewItems[activeTask.id].task.correctChoice}</span></p>
                    ) : (
                      <div className="review-answer-guide">
                        <strong>Answer Guide / Reference Code:</strong>
                        <pre className="code-guide"><code>{reviewItems[activeTask.id].task.answerGuide}</code></pre>
                      </div>
                    )}
                    <p className="review-explanation"><strong>Explanation:</strong> {reviewItems[activeTask.id].task.explanation}</p>
                    {reviewItems[activeTask.id].revealedHints && reviewItems[activeTask.id].revealedHints.length > 0 && (
                      <div className="review-hints">
                        <strong>Hints Used:</strong>
                        <ul>
                          {reviewItems[activeTask.id].revealedHints.map((hint, hIdx) => (
                            <li key={hIdx}>{hint.text}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
 
            <div className="task-footer">
              {!isReviewMode && (
                <div className="task-footer-meta">
                  <Clock3 size={16} />
                  <span className="timer-text">{elapsedSeconds}s elapsed</span>
                </div>
              )}
              <div className="task-navigation">
                <button type="button" onClick={goBack} disabled={!canGoBack}>
                  <ChevronLeft size={16} />
                  Back
                </button>
                {isReviewMode ? (
                  <button type="button" onClick={goForwardReview} disabled={!canGoForwardReview}>
                    Next
                    <ChevronRight size={16} />
                  </button>
                ) : (
                  <>
                    <button
                      type="button"
                      className="hint-btn"
                      onClick={requestHint}
                      disabled={revealingHint || hintState?.exhausted}
                    >
                      <HelpCircle size={16} />
                      {hintState?.exhausted ? "No hints left" : "Get Hint"}
                    </button>
                    <button type="button" onClick={skipTask} disabled={!activeTask}>
                      Skip
                      <ChevronRight size={16} />
                    </button>
                  </>
                )}
              </div>
              <button 
                className="primary-action" 
                type="button" 
                onClick={submitAnswer} 
                disabled={!activeTask || isReviewMode}
              >
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

          {(evaluation?.adaptation || evaluation?.inputSnapshot || evaluation?.engineTrace) && (
            <div className="trace-section">
              <button
                type="button"
                className="trace-toggle-btn"
                onClick={() => setShowTrace(!showTrace)}
              >
                <span>Fuzzy Engine Details</span>
                <span className="arrow">{showTrace ? "▲" : "▼"}</span>
              </button>

              {showTrace && (
                <div className="trace-content">
                  {evaluation?.adaptation && (
                    <div className="adaptation-info" style={{ marginTop: 0 }}>
                      <div className="adaptation-header">
                        <h3>Adaptation</h3>
                        <span className="difficulty-badge">
                          {evaluation.adaptation.selectedDifficulty?.toUpperCase()}
                        </span>
                      </div>
                      <p className="adaptation-reason">
                        {evaluation.adaptation.reason}
                      </p>
                    </div>
                  )}

                  {evaluation?.inputSnapshot && (
                    <div className="telemetry-snapshot">
                      <h3>Telemetry Inputs</h3>
                      <div className="telemetry-grid">
                        <div className="telemetry-item">
                          <span className="telemetry-label">Task Weight</span>
                          <span className="telemetry-value">{evaluation.inputSnapshot.taskMetricWeight}</span>
                        </div>
                        <div className="telemetry-item">
                          <span className="telemetry-label">Prior Mastery</span>
                          <span className="telemetry-value">{evaluation.inputSnapshot.historicalGradeAverage}%</span>
                        </div>
                        <div className="telemetry-item">
                          <span className="telemetry-label">Rel. Time</span>
                          <span className="telemetry-value">{evaluation.inputSnapshot.relativeResponseTime}x</span>
                        </div>
                        <div className="telemetry-item">
                          <span className="telemetry-label">Hints Used</span>
                          <span className="telemetry-value">{evaluation.inputSnapshot.assistanceInteractions}</span>
                        </div>
                        <div className="telemetry-item">
                          <span className="telemetry-label">Completion</span>
                          <span className="telemetry-value">{evaluation.inputSnapshot.completionRatio * 100}%</span>
                        </div>
                        <div className="telemetry-item">
                          <span className="telemetry-label">Task Type</span>
                          <span className="telemetry-value uppercase">{evaluation.inputSnapshot.taskType}</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {evaluation?.engineTrace?.anfis?.rules && (
                    <div className="engine-block">
                      <h4>ANFIS Rules (Mastery)</h4>
                      <div className="rules-list">
                        {evaluation.engineTrace.anfis.rules.map((r, i) => (
                          <div key={i} className="rule-item">
                            <span className="rule-name">{r.rule}</span>
                            <div className="rule-stats">
                              <span className="rule-badge strength">Strength: {r.strength}</span>
                              <span className="rule-badge consequent">Output: {r.output}%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}


                </div>
              )}
            </div>
          )}
        </aside>
      </section>

      {showSurveyModal && (
        <div className="survey-modal-overlay">
          <div className="survey-modal-card">
            <h2>Quick Feedback</h2>
            <p>Help us calibrate your tutoring experience. How did you feel about the last 5 tasks?</p>
            
            <form onSubmit={handleSurveySubmit}>
              <div className="survey-group">
                <label>Overall Satisfaction</label>
                <div className="rating-options">
                  {[1, 2, 3, 4, 5].map((val) => (
                    <button
                      key={val}
                      type="button"
                      className={`rating-btn ${satisfaction === val ? "active" : ""}`}
                      onClick={() => setSatisfaction(val)}
                    >
                      {val}
                    </button>
                  ))}
                </div>
              </div>

              <div className="survey-group">
                <label>Perceived Difficulty</label>
                <div className="rating-options">
                  {[1, 2, 3, 4, 5].map((val) => (
                    <button
                      key={val}
                      type="button"
                      className={`rating-btn ${perceivedDifficulty === val ? "active" : ""}`}
                      onClick={() => setPerceivedDifficulty(val)}
                    >
                      {val}
                    </button>
                  ))}
                </div>
              </div>

              <div className="survey-group">
                <label>Your Confidence Level</label>
                <div className="rating-options">
                  {[1, 2, 3, 4, 5].map((val) => (
                    <button
                      key={val}
                      type="button"
                      className={`rating-btn ${confidence === val ? "active" : ""}`}
                      onClick={() => setConfidence(val)}
                    >
                      {val}
                    </button>
                  ))}
                </div>
              </div>

              <div className="survey-group">
                <label>Additional Comments (Optional)</label>
                <textarea
                  value={feedbackComment}
                  onChange={(e) => setFeedbackComment(e.target.value)}
                  placeholder="Share any thoughts or suggestions..."
                  rows={3}
                />
              </div>

              <button
                className="survey-submit-btn"
                type="submit"
                disabled={submittingSurvey}
              >
                {submittingSurvey ? "Submitting..." : "Submit & Continue"}
              </button>
            </form>
          </div>
        </div>
      )}

      {showResetModal && (
        <div className="survey-modal-overlay">
          <div className="survey-modal-card">
            <h2>Reset Session</h2>
            <p>Are you sure you want to reset your tutoring session? All of your progress and answers will be deleted permanently.</p>
            <div className="modal-actions">
              <button
                type="button"
                className="modal-btn cancel-btn"
                onClick={() => setShowResetModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="modal-btn confirm-btn"
                onClick={confirmReset}
              >
                Yes, Reset
              </button>
            </div>
          </div>
        </div>
      )}

      {showHelpModal && (
        <div className="survey-modal-overlay">
          <div className="survey-modal-card help-modal-card">
            <h2>FuzzyTutor Guide</h2>
            <div className="help-modal-content">
              <div className="help-modal-section">
                <h3>What is FuzzyTutor?</h3>
                <p>
                  FuzzyTutor is an explainable, adaptive programming concepts tutor. 
                  It monitors your coding progress, answer patterns, response speeds, and hints usage in real-time. 
                  Using a built-in Fuzzy Logic engine (ANFIS for mastery and Mamdani for cognitive friction), 
                  it dynamically calibrates the difficulty of your tasks (Foundation, Intermediate, or Advanced) 
                  to align with your learning state.
                </p>
              </div>

              <div className="help-modal-section">
                <h3>Controls & Tools</h3>
                <ul>
                  <li>
                    <strong>Submit response:</strong> Submits your current answer to the Fuzzy Engine for evaluation. 
                    Correct answers increase your module mastery, while errors trigger recalibration.
                  </li>
                  <li>
                    <strong>Get Hint:</strong> Reveals incremental hints to assist you. 
                    <em> Note: Use hints sparingly, as heavy hint usage is interpreted by the fuzzy engine as a sign of cognitive strain (friction).</em>
                  </li>
                  <li>
                    <strong>Skip:</strong> Skips the task. Skipping signals the tutor that the task might be too challenging, which helps calibrate future task difficulty.
                  </li>
                  <li>
                    <strong>Reset:</strong> Located in the top header. Clears your entire session progress and answers, allowing you to restart the curriculum from scratch.
                  </li>
                  <li>
                    <strong>Back:</strong> Allows you to navigate back to previously attempted or skipped tasks. In this review mode, you can inspect the correct choice (or reference code) and see an explanation analyzing why it is correct.
                  </li>
                </ul>
              </div>

              <div className="help-modal-section">
                <h3>Progress Pills & Color Codes</h3>
                <ul>
                  <li>
                    <span className="help-pill-badge active"></span>
                    <strong>Blue (Glowing):</strong> Represents your active/current task.
                  </li>
                  <li>
                    <span className="help-pill-badge submitted"></span>
                    <strong>Green:</strong> Tasks that you have successfully submitted or completed.
                  </li>
                  <li>
                    <span className="help-pill-badge skipped"></span>
                    <strong>Orange:</strong> Tasks that you have skipped.
                  </li>
                  <li>
                    <span className="help-pill-badge unattempted"></span>
                    <strong>Gray:</strong> Future tasks remaining in the module's bank.
                  </li>
                </ul>
              </div>

              <div className="help-modal-section">
                <h3>Fast-Track Module Exit</h3>
                <p>
                  Each learning module contains a bank of up to 15 tasks. However, 
                  <strong> you may not need to complete all of them!</strong> 
                  If the fuzzy engine detects that your Knowledge Mastery is high and your Cognitive Friction is low over consecutive tasks, 
                  it will automatically fast-track/exit you from the module early and unlock the next module.
                </p>
              </div>
            </div>
            
            <button
              type="button"
              className="help-close-btn"
              onClick={() => setShowHelpModal(false)}
            >
              Close Guide
            </button>
          </div>
        </div>
      )}
    </main>
  );
}

export default TutorPage;
