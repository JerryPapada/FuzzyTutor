import React from "react";

function SurveyModal({
  show,
  satisfaction,
  onSatisfactionChange,
  perceivedDifficulty,
  onPerceivedDifficultyChange,
  confidence,
  onConfidenceChange,
  feedbackComment,
  onFeedbackCommentChange,
  submittingSurvey,
  onSubmit,
}) {
  if (!show) return null;

  return (
    <div className="survey-modal-overlay">
      <div className="survey-modal-card">
        <h2>Quick Feedback</h2>
        <p>
          Help us calibrate your tutoring experience. How did you feel about the
          last 5 tasks?
        </p>

        <form onSubmit={onSubmit}>
          <div className="survey-group">
            <label>Overall Satisfaction</label>
            <div className="rating-options">
              {[1, 2, 3, 4, 5].map((val) => (
                <button
                  key={val}
                  type="button"
                  className={`rating-btn ${satisfaction === val ? "active" : ""}`}
                  onClick={() => onSatisfactionChange(val)}
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
                  className={`rating-btn ${
                    perceivedDifficulty === val ? "active" : ""
                  }`}
                  onClick={() => onPerceivedDifficultyChange(val)}
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
                  onClick={() => onConfidenceChange(val)}
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
              onChange={(e) => onFeedbackCommentChange(e.target.value)}
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
  );
}

export default SurveyModal;
