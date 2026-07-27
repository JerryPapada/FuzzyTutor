import React from "react";

function HelpModal({ show, onClose }) {
  if (!show) return null;

  return (
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
          onClick={onClose}
        >
          Close Guide
        </button>
      </div>
    </div>
  );
}

export default HelpModal;
