import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, Brain, Gauge, GraduationCap, HelpCircle, Play } from "lucide-react";
import "./styles.css";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

function Metric({ icon: Icon, label, value, tone }) {
  return (
    <section className={`metric metric-${tone}`}>
      <div className="metric-heading">
        <Icon size={18} />
        <span>{label}</span>
      </div>
      <strong>{value}</strong>
    </section>
  );
}

function App() {
  const [health, setHealth] = useState("checking");
  const [modules, setModules] = useState([]);
  const [task, setTask] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [selectedChoice, setSelectedChoice] = useState("for loop");

  useEffect(() => {
    Promise.all([
      fetch(`${API_URL}/health/`).then((response) => response.json()),
      fetch(`${API_URL}/learning/modules/`).then((response) => response.json()),
      fetch(`${API_URL}/learning/next-task/`).then((response) => response.json()),
    ])
      .then(([healthResponse, moduleResponse, taskResponse]) => {
        setHealth(healthResponse.status);
        setModules(moduleResponse.modules);
        setTask(taskResponse);
      })
      .catch(() => setHealth("offline"));
  }, []);

  const activeModule = useMemo(
    () => modules.find((module) => module.id === task?.moduleId),
    [modules, task],
  );

  async function submitAnswer() {
    const response = await fetch(`${API_URL}/fuzzy/evaluate/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        taskMetricWeight: 35,
        historicalGradeAverage: 76,
        relativeResponseTime: 0.92,
        assistanceInteractions: 1,
        selectedChoice,
      }),
    });
    setEvaluation(await response.json());
  }

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
        <div className="task-panel">
          <div className="module-strip">
            {modules.map((module) => (
              <span key={module.id} className={module.id === task?.moduleId ? "active" : ""}>
                M{module.id}
              </span>
            ))}
          </div>

          <div className="task-header">
            <GraduationCap size={24} />
            <div>
              <p>{activeModule?.title ?? "Loading module"}</p>
              <h2>{task?.prompt ?? "Preparing the next task..."}</h2>
            </div>
          </div>

          <div className="choices">
            {(task?.choices ?? []).map((choice) => (
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

          <button className="primary-action" type="button" onClick={submitAnswer}>
            <Play size={18} />
            Submit response
          </button>
        </div>

        <aside className="xai-panel">
          <div className="panel-heading">
            <Brain size={22} />
            <div>
              <p>Explainable AI</p>
              <h2>Learning state</h2>
            </div>
          </div>

          <Metric
            icon={Gauge}
            label="Knowledge mastery"
            value={`${evaluation?.knowledgeMastery ?? "--"}%`}
            tone="mastery"
          />
          <Metric
            icon={HelpCircle}
            label="Cognitive friction"
            value={`${evaluation?.systemCognitiveFriction ?? "--"}%`}
            tone="friction"
          />

          <div className="recommendation">
            <span>{evaluation?.focusState ?? "Waiting for a submission"}</span>
            <p>{evaluation?.recommendation ?? "The next task will adapt after the first response."}</p>
          </div>
        </aside>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
