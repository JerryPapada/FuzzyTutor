import React from "react";

function StatCard({ icon: Icon, label, value, tone, hint, numericValue = 0 }) {
  return (
    <section className={`stat-card stat-card-${tone}`}>
      <div className="stat-header">
        <div className="stat-label">
          <Icon size={18} />
          <span>{label}</span>
        </div>
        <strong>{value}</strong>
      </div>
      <div className="stat-meter" aria-hidden="true">
        <span style={{ width: `${Math.max(0, Math.min(100, numericValue))}%` }} />
      </div>
      <p>{hint}</p>
    </section>
  );
}

export default StatCard;
