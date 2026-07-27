import React from "react";
import { Terminal, HelpCircle, RotateCcw } from "lucide-react";

function Header({ onHelp, onReset }) {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <button type="button" className="header-btn help-btn" onClick={onHelp}>
          <HelpCircle size={18} />
          <span>Help</span>
        </button>
      </div>

      <div className="topbar-center">
        <p className="eyebrow">Programming Concepts Tutor</p>
        <div className="header-brand">
          <div className="header-logo-icon" aria-hidden="true">
            <Terminal size={22} strokeWidth={2.5} />
          </div>
          <h1>FuzzyTutor</h1>
        </div>
      </div>

      <div className="topbar-right">
        <button type="button" className="header-btn reset-btn" onClick={onReset}>
          <RotateCcw size={16} />
          <span>Reset</span>
        </button>
      </div>
    </header>
  );
}

export default Header;
