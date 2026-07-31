import React from "react";
import { ChevronLeft, ChevronRight, Clock3, HelpCircle, Play } from "lucide-react";

function TaskPanel({
  activeModule,
  activeModuleId,
  activeTask,
  session,
  timeline,
  activeTaskIndexInTimeline,
  isReviewMode,
  reviewItems,
  selectedChoice,
  onSelectedChoiceChange,
  codeAnswer,
  onCodeAnswerChange,
  isTransitioning,
  elapsedSeconds,
  canGoBack,
  onGoBack,
  canGoForwardReview,
  onGoForwardReview,
  revealingHint,
  submittingTask,
  onRequestHint,
  hintState,
  onSkip,
  onSubmit,
}) {
  return (
    <section className="task-panel">
      <div className="task-window">
        <div className="task-header">
          <div className="task-header-top">
            <div className="task-header-title">
              <span>{activeModule?.title}</span>
            </div>
            <div className="progress-pills">
              {(() => {
                const attempts = (session?.orderedAttempts || []).filter(
                  (att) => att.moduleId == activeModuleId
                );
                const activeProgress = session?.moduleProgress?.find(
                  (p) => p.moduleId === activeModuleId
                );
                const isCompleted = activeProgress
                  ? activeProgress.status === "mastered" ||
                    activeProgress.status === "completed_bank" ||
                    activeProgress.terminal
                  : activeModuleId < session?.currentModuleId;
                const pillCount = isCompleted ? attempts.length : 15;

                return Array.from({ length: pillCount }).map((_, idx) => {
                  let activeIdx = attempts.length;
                  if (activeTask && session) {
                    if (activeTask.id !== session.currentTaskId) {
                      const foundIdx = attempts.findIndex(
                        (att) => att.taskId === activeTask.id
                      );
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
                    <div key={idx} className={`progress-pill ${statusClass}`} />
                  );
                });
              })()}
            </div>
          </div>
        </div>

        <div
          className={`task-body-transition ${
            isTransitioning ? "transitioning" : ""
          }`}
          style={{ display: "flex", flexDirection: "column", flexGrow: 1 }}
        >
          <h2 className="task-prompt">
            {activeTask?.prompt ?? "Choose a module to load its first task."}
          </h2>

          <div className="task-meta">
            <span>{activeTask?.type?.toUpperCase() ?? "TASK"}</span>
            <span>{activeTask?.difficulty ?? "foundation"}</span>
            <span>{activeTask?.baselineTimeSeconds ?? 0}s baseline</span>
          </div>

          {activeTask?.type === "mcq" ? (
            <div className="choices">
              {(activeTask?.choices ?? []).map((choice) => (
                <label
                  key={choice}
                  className={
                    selectedChoice === choice ? "choice selected" : "choice"
                  }
                >
                  <input
                    type="radio"
                    name="choice"
                    value={choice}
                    checked={selectedChoice === choice}
                    disabled={isReviewMode}
                    onChange={(event) => {
                      onSelectedChoiceChange(event.target.value);
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
                  onCodeAnswerChange(event.target.value);
                }}
                rows={11}
                spellCheck="false"
                disabled={isReviewMode}
              />
            </div>
          ) : (
            <div className="empty-task-state">Select a module to begin.</div>
          )}

          {/* Active task revealed hints */}
          {!isReviewMode &&
            hintState?.revealedHints &&
            hintState.revealedHints.length > 0 && (
              <div className="active-hints-panel">
                <h3 className="active-hints-title">Revealed Hints</h3>
                <div className="active-hints-content">
                  <ul>
                    {hintState.revealedHints.map((hint, idx) => (
                      <li key={idx} className="hint-item-row">
                        <strong className="hint-label-badge">
                          {hint.label}:
                        </strong>
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
                  <p>
                    <strong>Correct Choice:</strong>{" "}
                    <span className="correct-highlight">
                      {reviewItems[activeTask.id].task.correctChoice}
                    </span>
                  </p>
                ) : (
                  <div className="review-answer-guide">
                    <strong>Answer Guide / Reference Code:</strong>
                    <pre className="code-guide">
                      <code>{reviewItems[activeTask.id].task.answerGuide}</code>
                    </pre>
                  </div>
                )}
                <p className="review-explanation">
                  <strong>Explanation:</strong>{" "}
                  {reviewItems[activeTask.id].task.explanation}
                </p>
                {reviewItems[activeTask.id].revealedHints &&
                  reviewItems[activeTask.id].revealedHints.length > 0 && (
                    <div className="review-hints">
                      <strong>Hints Used:</strong>
                      <ul>
                        {reviewItems[activeTask.id].revealedHints.map(
                          (hint, hIdx) => (
                            <li key={hIdx}>{hint.text}</li>
                          )
                        )}
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
            <button type="button" onClick={onGoBack} disabled={!canGoBack}>
              <ChevronLeft size={16} />
              Back
            </button>
            {isReviewMode ? (
              <button
                type="button"
                onClick={onGoForwardReview}
                disabled={!canGoForwardReview}
              >
                Next
                <ChevronRight size={16} />
              </button>
            ) : (
              <>
                <button
                  type="button"
                  className="hint-btn"
                  onClick={onRequestHint}
                  disabled={revealingHint || submittingTask || hintState?.exhausted}
                >
                  <HelpCircle size={16} />
                  {hintState?.exhausted ? "No hints left" : "Get Hint"}
                </button>
                <button
                  type="button"
                  onClick={onSkip}
                  disabled={!activeTask || submittingTask}
                >
                  Skip
                  <ChevronRight size={16} />
                </button>
              </>
            )}
          </div>
          <button
            className="primary-action"
            type="button"
            onClick={onSubmit}
            disabled={!activeTask || isReviewMode || submittingTask}
          >
            <Play size={18} />
            {submittingTask ? "Submitting…" : "Submit response"}
          </button>
        </div>
      </div>
    </section>
  );
}

export default TaskPanel;
