import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import TaskPanel from "./TaskPanel";

describe("TaskPanel submission guard", () => {
  it("disables competing task actions while a submission is pending", () => {
    render(
      <TaskPanel
        activeTask={{
          id: "task-1",
          type: "mcq",
          choices: ["A", "B"],
          difficulty: "foundation",
          baselineTimeSeconds: 30,
          prompt: "Choose",
        }}
        session={{ currentTaskId: "task-1", orderedAttempts: [] }}
        timeline={["task-1"]}
        reviewItems={{}}
        selectedChoice=""
        onSelectedChoiceChange={vi.fn()}
        codeAnswer=""
        onCodeAnswerChange={vi.fn()}
        elapsedSeconds={1}
        onGoBack={vi.fn()}
        onGoForwardReview={vi.fn()}
        onRequestHint={vi.fn()}
        onSkip={vi.fn()}
        onSubmit={vi.fn()}
        submittingTask
      />
    );

    expect(screen.getByRole("button", { name: /submitting/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /skip/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /get hint/i })).toBeDisabled();
  });
});
