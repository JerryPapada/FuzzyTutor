import React from "react";
import { Brain, Gauge, HelpCircle } from "lucide-react";
import StatCard from "./StatCard";

const RECOMMENDATION_LABELS = {
  increase_or_hold_high_tier: "Advance or Maintain High Difficulty Level",
  reduce_difficulty_and_show_support: "Reduce Difficulty Level and Provide Support",
  hold_current_tier: "Maintain Current Difficulty Level",
};

const DIRECTION_LABELS = {
  increase: "Increase difficulty",
  decrease: "Decrease difficulty",
  hold: "Hold difficulty",
};

function XAIPanel({ evaluation, showTrace, onToggleTrace }) {
  return (
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
          {evaluation?.adaptation
            ? `Applied next-task action: ${
                DIRECTION_LABELS[evaluation.adaptation.direction] ??
                evaluation.adaptation.direction
              }`
            : evaluation?.recommendation
            ? RECOMMENDATION_LABELS[evaluation.recommendation] ??
              evaluation.recommendation
            : "The next task will adapt after the first response."}
        </p>
        <strong>
          {evaluation?.supportMessage ??
            "Submit a response to see the fuzzy summary."}
        </strong>
      </div>

      {(evaluation?.adaptation ||
        evaluation?.inputSnapshot ||
        evaluation?.engineTrace) && (
        <div className="trace-section">
          <button
            type="button"
            className="trace-toggle-btn"
            onClick={onToggleTrace}
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
                  <p className="adaptation-reason">
                    Model request: {DIRECTION_LABELS[
                      evaluation.adaptation.requestedDirection
                    ] ?? evaluation.adaptation.requestedDirection}
                    {evaluation.adaptation.constraintApplied
                      ? ` · Constraint: ${evaluation.adaptation.constraintApplied.replaceAll(
                          "_",
                          " "
                        )}`
                      : ""}
                  </p>
                  <p className="adaptation-reason">
                    Raw recommendation: {RECOMMENDATION_LABELS[
                      evaluation.recommendation
                    ] ?? evaluation.recommendation}
                  </p>
                </div>
              )}

              {evaluation?.inputSnapshot && (
                <div className="telemetry-snapshot">
                  <h3>Telemetry Inputs</h3>
                  <div className="telemetry-grid">
                    <div className="telemetry-item">
                      <span className="telemetry-label">Task Weight</span>
                      <span className="telemetry-value">
                        {evaluation.inputSnapshot.taskMetricWeight}
                      </span>
                    </div>
                    <div className="telemetry-item">
                      <span className="telemetry-label">Prior Mastery</span>
                      <span className="telemetry-value">
                        {evaluation.inputSnapshot.historicalGradeAverage}%
                      </span>
                    </div>
                    <div className="telemetry-item">
                      <span className="telemetry-label">Rel. Time</span>
                      <span className="telemetry-value">
                        {evaluation.inputSnapshot.relativeResponseTime}x
                      </span>
                    </div>
                    <div className="telemetry-item">
                      <span className="telemetry-label">Hints Used</span>
                      <span className="telemetry-value">
                        {evaluation.inputSnapshot.assistanceInteractions}
                      </span>
                    </div>
                    <div className="telemetry-item">
                      <span className="telemetry-label">Completion</span>
                      <span className="telemetry-value">
                        {evaluation.inputSnapshot.completionRatio * 100}%
                      </span>
                    </div>
                    <div className="telemetry-item">
                      <span className="telemetry-label">Task Type</span>
                      <span className="telemetry-value uppercase">
                        {evaluation.inputSnapshot.taskType}
                      </span>
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
                          <span className="rule-badge strength">
                            Strength: {r.strength}
                          </span>
                          <span className="rule-badge consequent">
                            Output: {r.output}%
                          </span>
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
  );
}

export default XAIPanel;
