import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import useElapsedTimer from "./useElapsedTimer";

describe("useElapsedTimer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T00:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("preserves the start time for edits and resets only for a new task id", () => {
    const { result, rerender } = renderHook(
      ({ task }) => useElapsedTimer(task),
      { initialProps: { task: { id: "task-a", answer: "" } } }
    );
    const firstStart = result.current.taskStartedAt.current;

    vi.setSystemTime(new Date("2026-01-01T00:00:05Z"));
    rerender({ task: { id: "task-a", answer: "edited" } });
    expect(result.current.taskStartedAt.current).toBe(firstStart);

    vi.setSystemTime(new Date("2026-01-01T00:00:10Z"));
    rerender({ task: { id: "task-b", answer: "" } });
    expect(result.current.taskStartedAt.current).toBe(
      new Date("2026-01-01T00:00:10Z").getTime()
    );
  });
});
