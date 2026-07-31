import { useState, useEffect, useMemo, useRef } from "react";
import useElapsedTimer from "./useElapsedTimer";
import { fetchHealth } from "../services/healthService";
import {
  fetchModules,
  fetchTasks,
  createSession,
  fetchSession,
  submitSubmission,
  submitMicroSurvey,
  fetchSessionReview,
  revealHint,
  deleteSession,
} from "../services/learningService";

export function normalizeCodeResponse(value) {
  return String(value ?? "")
    .replace(/\r\n?/g, "\n")
    .split("\n")
    .map((line) => line.trimEnd())
    .join("\n")
    .trim();
}

export function editableAnswersForTask(activeTask, storedAnswer = "") {
  return {
    selectedChoice: activeTask?.type === "mcq" ? storedAnswer : "",
    codeAnswer:
      activeTask?.type === "code"
        ? storedAnswer || activeTask.starterCode || ""
        : "",
  };
}

export function submissionPayloadFor({
  sessionToken,
  activeTask,
  elapsedTimeSeconds,
  selectedChoice,
  codeAnswer,
}) {
  return {
    sessionToken,
    taskId: activeTask.id,
    elapsedTimeSeconds,
    skipped: false,
    ...(activeTask.type === "mcq"
      ? { selectedChoice }
      : { answerText: codeAnswer }),
  };
}

export default function useTutorSession() {
  const [health, setHealth] = useState("checking");
  const [modules, setModules] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [activeModuleId, setActiveModuleId] = useState(null);
  const [taskIndexByModule, setTaskIndexByModule] = useState({});
  const [sessionToken, setSessionToken] = useState(null);
  const [session, setSession] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
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
  const [submittingTask, setSubmittingTask] = useState(false);
  const [showTrace, setShowTrace] = useState(false);
  const [hintState, setHintState] = useState(null);
  const [revealingHint, setRevealingHint] = useState(false);
  const [reviewItems, setReviewItems] = useState({});
  const [localAnswers, setLocalAnswers] = useState({});
  const notificationTimeoutRef = useRef(null);
  const submissionInProgressRef = useRef(false);

  useEffect(() => {
    if (session) {
      setHintState(session.hintState);
    }
  }, [session]);

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
    [modules, activeModuleId]
  );

  const moduleTasks = useMemo(
    () => tasks.filter((task) => task.moduleId === activeModuleId),
    [tasks, activeModuleId]
  );

  const activeTaskIndex =
    activeModuleId == null ? 0 : taskIndexByModule[activeModuleId] ?? 0;
  const activeTask = moduleTasks[activeTaskIndex] ?? null;

  const timeline = useMemo(() => {
    if (!session || !activeModuleId) return [];
    const attempts = (session.orderedAttempts || []).filter(
      (att) => att.moduleId == activeModuleId
    );
    return [...attempts.map((att) => att.taskId), session.currentTaskId].filter(
      Boolean
    );
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

  const { elapsedSeconds, taskStartedAt } = useElapsedTimer(activeTask);

  useEffect(() => {
    async function initApp() {
      try {
        const [healthResponse, moduleResponse, taskResponse] =
          await Promise.all([fetchHealth(), fetchModules(), fetchTasks()]);

        setHealth(healthResponse.status);
        const fetchedModules = moduleResponse.modules ?? [];
        const fetchedTasks = taskResponse.tasks ?? [];
        setModules(fetchedModules);
        setTasks(fetchedTasks);

        const storedToken = localStorage.getItem("sessionToken");
        const justReset = localStorage.getItem("justReset");
        let activeSession = null;

        if (storedToken) {
          try {
            activeSession = await fetchSession(storedToken);
          } catch (err) {
            console.warn(
              "Stored session invalid or expired, creating new one.",
              err
            );
          }
          if (justReset === "true") {
            localStorage.removeItem("justReset");
          }
        } else {
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

        const storedAnswers = localStorage.getItem(
          `answers_${activeSession.sessionToken}`
        );
        if (storedAnswers) {
          setLocalAnswers(JSON.parse(storedAnswers));
        }

        try {
          const reviewData = await fetchSessionReview(
            activeSession.sessionToken
          );
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

        const targetModuleId =
          activeSession.currentModuleId ?? fetchedModules[0]?.id ?? null;
        setActiveModuleId(targetModuleId);

        const initialIndices = Object.fromEntries(
          fetchedModules.map((module) => [module.id, 0])
        );

        if (targetModuleId != null) {
          const modTasks = fetchedTasks.filter(
            (t) => t.moduleId === targetModuleId
          );
          const taskIdx = modTasks.findIndex(
            (t) => t.id === activeSession.currentTaskId
          );
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
        (attempt) => attempt.taskId === activeTask.id
      );
      const learnerAnswer =
        reviewItems[activeTask.id]?.learnerAnswer ??
        persistedAttempt?.learnerAnswer ??
        {};
      const submittedVal =
        (activeTask.type === "mcq"
          ? learnerAnswer.selectedChoice
          : learnerAnswer.answerText) ??
        localAnswers[activeTask.id] ??
        "";
      setSelectedChoice(activeTask.type === "mcq" ? submittedVal : "");
      setCodeAnswer(activeTask.type === "code" ? submittedVal : "");
    } else {
      const editableAnswers = editableAnswersForTask(
        activeTask,
        localAnswers[activeTask.id]
      );
      setSelectedChoice(editableAnswers.selectedChoice);
      setCodeAnswer(editableAnswers.codeAnswer);
    }
  }, [activeTask?.id, session?.currentTaskId, reviewItems, localAnswers]);

  useEffect(() => {
    setEvaluation(null);
  }, [activeModuleId]);

  function selectModule(moduleId) {
    const progress = session?.moduleProgress?.find(
      (p) => p.moduleId === moduleId
    );
    const isUnlocked = progress && progress.status !== "not_started";
    const isCurrent = session && moduleId === session.currentModuleId;

    if (!isUnlocked && !isCurrent) {
      triggerNotification(
        "This module is locked. Complete the current module tasks to unlock."
      );
      return;
    }

    setActiveModuleId(moduleId);

    setTaskIndexByModule((current) => {
      const selectedModuleTasks = tasks.filter((t) => t.moduleId === moduleId);
      let targetIdx = 0;
      if (session && moduleId === session.currentModuleId) {
        const currentTaskIdx = selectedModuleTasks.findIndex(
          (t) => t.id === session.currentTaskId
        );
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
    }, 200);
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
    if (
      activeModuleId == null ||
      moduleTasks.length === 0 ||
      timeline.length === 0 ||
      !activeTask
    ) {
      return;
    }

    const currentIndex = timeline.indexOf(activeTask.id);
    if (currentIndex === -1) return;

    const nextIndex =
      direction === "back" ? currentIndex - 1 : currentIndex + 1;
    if (nextIndex < 0 || nextIndex >= timeline.length) return;

    const targetTaskId = timeline[nextIndex];
    const targetIdxInModule = moduleTasks.findIndex(
      (t) => t.id === targetTaskId
    );

    if (targetIdxInModule !== -1) {
      setTaskIndexByModule((current) => ({
        ...current,
        [activeModuleId]: targetIdxInModule,
      }));
    }
  }

  function transitionToNextTask(nextTask) {
    if (!nextTask) return;

    const nextModuleTasks = tasks.filter((t) => t.moduleId === nextTask.moduleId);
    const nextTaskIdx = nextModuleTasks.findIndex((t) => t.id === nextTask.id);

    if (nextTask.moduleId !== activeModuleId) {
      setTimeout(() => {
        const nextModuleBtn = document.querySelector(
          `.module-item[data-id="${nextTask.moduleId}"]`
        );
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
    if (!activeTask || !sessionToken || submissionInProgressRef.current) {
      return;
    }

    submissionInProgressRef.current = true;
    setSubmittingTask(true);

    const responseTime = Math.max(
      0.1,
      (Date.now() - taskStartedAt.current) / 1000
    );

    try {
      const result = await submitSubmission({
        sessionToken,
        taskId: activeTask.id,
        elapsedTimeSeconds: responseTime,
        skipped: true,
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

      if (
        result.moduleDecision &&
        result.moduleDecision.outcome !== "continue"
      ) {
        if (result.moduleDecision.outcome === "mastery_exit") {
          triggerNotification("Congratulations! You mastered the module early!");
        } else if (result.moduleDecision.outcome === "bank_exhausted") {
          triggerNotification("Module completed. Moving to next module.");
        }
      }

      if (
        result.adaptation?.curriculumComplete ||
        result.session?.curriculumComplete
      ) {
        alert("Congratulations! You have completed all modules.");
      } else {
        transitionToNextTask(result.nextTask);
      }

      fetchSessionReview(sessionToken)
        .then((reviewData) => {
          const reviewMap = {};
          if (reviewData && reviewData.items) {
            reviewData.items.forEach((item) => {
              reviewMap[item.task.id] = item;
            });
          }
          setReviewItems(reviewMap);
        })
        .catch((reviewErr) => {
          console.warn(
            "Failed to fetch session review items after skip",
            reviewErr
          );
        });
    } catch (error) {
      console.error("Failed to skip task:", error);
      triggerNotification(error.message || "An error occurred while skipping the task.");
    } finally {
      submissionInProgressRef.current = false;
      setSubmittingTask(false);
    }
  }

  async function submitAnswer() {
    if (!activeTask || !sessionToken || submissionInProgressRef.current) {
      return;
    }

    if (activeTask.type === "mcq" && !selectedChoice.trim()) {
      triggerNotification("Select an answer or explicitly skip this task.");
      return;
    }
    if (activeTask.type === "code") {
      const normalizedAnswer = normalizeCodeResponse(codeAnswer);
      const normalizedStarter = normalizeCodeResponse(activeTask.starterCode);
      if (!normalizedAnswer) {
        triggerNotification("Enter a code response or explicitly skip this task.");
        return;
      }
      if (normalizedAnswer === normalizedStarter) {
        triggerNotification("Edit the starter code meaningfully or explicitly skip this task.");
        return;
      }
    }

    submissionInProgressRef.current = true;
    setSubmittingTask(true);
    const responseTime = Math.max(
      0.1,
      (Date.now() - taskStartedAt.current) / 1000
    );

    try {
      const result = await submitSubmission(submissionPayloadFor({
        sessionToken,
        activeTask,
        elapsedTimeSeconds: responseTime,
        selectedChoice,
        codeAnswer,
      }));

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

      if (
        result.moduleDecision &&
        result.moduleDecision.outcome !== "continue"
      ) {
        if (result.moduleDecision.outcome === "mastery_exit") {
          triggerNotification("Congratulations! You mastered the module early!");
        } else if (result.moduleDecision.outcome === "bank_exhausted") {
          triggerNotification("Module completed. Moving to next module.");
        }
      }

      if (
        result.adaptation?.curriculumComplete ||
        result.session?.curriculumComplete
      ) {
        alert("Congratulations! You have completed all modules.");
      } else {
        transitionToNextTask(result.nextTask);
      }

      fetchSessionReview(sessionToken)
        .then((reviewData) => {
          const reviewMap = {};
          if (reviewData && reviewData.items) {
            reviewData.items.forEach((item) => {
              reviewMap[item.task.id] = item;
            });
          }
          setReviewItems(reviewMap);
        })
        .catch((reviewErr) => {
          console.warn(
            "Failed to fetch session review items after submission",
            reviewErr
          );
        });
    } catch (error) {
      console.error("Submission failed:", error);
      triggerNotification(
        error.message || "An error occurred during submission."
      );
    } finally {
      submissionInProgressRef.current = false;
      setSubmittingTask(false);
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
    if (!activeTask || !sessionToken || revealingHint || submittingTask) return;

    const responseTime = Math.max(
      0.1,
      (Date.now() - taskStartedAt.current) / 1000
    );
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

  const progressLabel = activeTask
    ? `${activeTaskIndexInTimeline + 1} / ${timeline.length}`
    : "0 / 0";
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
          console.warn(
            "Backend session deletion failed, clearing locally anyway:",
            err
          );
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

  const onSelectedChoiceChange = (val) => {
    setSelectedChoice(val);
    setLocalAnswers((prev) => {
      const updated = { ...prev, [activeTask.id]: val };
      localStorage.setItem(`answers_${sessionToken}`, JSON.stringify(updated));
      return updated;
    });
  };

  const onCodeAnswerChange = (val) => {
    setCodeAnswer(val);
    setLocalAnswers((prev) => {
      const updated = { ...prev, [activeTask.id]: val };
      localStorage.setItem(`answers_${sessionToken}`, JSON.stringify(updated));
      return updated;
    });
  };

  return {
    health,
    modules,
    tasks,
    activeModuleId,
    sessionToken,
    session,
    evaluation,
    selectedChoice,
    codeAnswer,
    isTransitioning,
    submittedTaskIds,
    skippedTaskIds,
    notificationMsg,
    showNotification,
    surveyDue,
    showSurveyModal,
    showResetModal,
    showHelpModal,
    satisfaction,
    perceivedDifficulty,
    confidence,
    feedbackComment,
    submittingSurvey,
    submittingTask,
    showTrace,
    hintState,
    revealingHint,
    reviewItems,
    localAnswers,
    activeModule,
    moduleTasks,
    activeTask,
    timeline,
    activeTaskIndexInTimeline,
    isReviewMode,
    canGoBack,
    canGoForwardReview,
    selectModule,
    submitAnswer,
    skipTask,
    requestHint,
    goBack,
    goForwardReview,
    handleHelp,
    handleReset,
    confirmReset,
    handleSurveySubmit,
    onSelectedChoiceChange,
    onCodeAnswerChange,
    onToggleTrace: () => setShowTrace((prev) => !prev),
    setShowResetModal,
    setShowHelpModal,
    setSatisfaction,
    setPerceivedDifficulty,
    setConfidence,
    setFeedbackComment,
    progressLabel,
    canGoForward,
    elapsedSeconds,
  };
}
