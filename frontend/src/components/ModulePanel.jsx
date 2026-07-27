import React from "react";
import { Layers3, Check, Lock, Play } from "lucide-react";

function ModulePanel({ modules, session, activeModuleId, onSelectModule }) {
  return (
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
              onClick={() => onSelectModule(module.id)}
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
  );
}

export default ModulePanel;
