import React from "react";

function ResetModal({ show, onCancel, onConfirm }) {
  if (!show) return null;

  return (
    <div className="survey-modal-overlay">
      <div className="survey-modal-card">
        <h2>Reset Session</h2>
        <p>
          Are you sure you want to reset your tutoring session? All of your
          progress and answers will be deleted permanently.
        </p>
        <div className="modal-actions">
          <button
            type="button"
            className="modal-btn cancel-btn"
            onClick={onCancel}
          >
            Cancel
          </button>
          <button
            type="button"
            className="modal-btn confirm-btn"
            onClick={onConfirm}
          >
            Yes, Reset
          </button>
        </div>
      </div>
    </div>
  );
}

export default ResetModal;
