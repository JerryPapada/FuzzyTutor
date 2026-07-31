import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import XAIPanel from "./XAIPanel";

describe("XAIPanel", () => {
  it("shows learner focus separately from the applied next-task action", () => {
    render(
      <XAIPanel
        evaluation={{
          knowledgeMastery: 80,
          systemCognitiveFriction: 30,
          focusState: "Needs Support",
          recommendation: "increase_or_hold_high_tier",
          supportMessage: "Advance while keeping a hint available.",
          adaptation: {
            direction: "increase",
            requestedDirection: "increase",
            constraintApplied: null,
            selectedDifficulty: "advanced",
            reason: "Strong evidence supports an increase.",
          },
        }}
        showTrace={false}
        onToggleTrace={vi.fn()}
      />
    );

    expect(screen.getByText("Needs Support")).toBeInTheDocument();
    expect(
      screen.getByText("Applied next-task action: Increase difficulty")
    ).toBeInTheDocument();
  });
});
