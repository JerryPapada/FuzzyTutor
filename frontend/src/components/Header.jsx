import React from "react";
import { Terminal } from "lucide-react";

function Header() {
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">Programming Concepts Tutor</p>
        <div className="header-brand">
          <div className="header-logo-icon" aria-hidden="true">
            <Terminal size={22} strokeWidth={2.5} />
          </div>
          <h1>FuzzyTutor</h1>
        </div>
      </div>
    </header>
  );
}

export default Header;
