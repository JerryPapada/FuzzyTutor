import { describe, expect, it } from "vitest";
import {
  editableAnswersForTask,
  normalizeCodeResponse,
  submissionPayloadFor,
} from "./useTutorSession";

describe("tutor submission helpers", () => {
  it("starts an MCQ without an automatically selected choice", () => {
    expect(
      editableAnswersForTask(
        { id: "mcq-1", type: "mcq", choices: ["first", "second"] },
        ""
      ).selectedChoice
    ).toBe("");
  });

  it("normalizes unchanged starter code and detects meaningful edits", () => {
    const starter = "for item in items:\n    pass\n";
    expect(normalizeCodeResponse(`  ${starter}  `)).toBe(
      normalizeCodeResponse(starter)
    );
    expect(normalizeCodeResponse(`${starter}# learner edit`)).not.toBe(
      normalizeCodeResponse(starter)
    );
  });

  it("builds submission requests without client-derived completion", () => {
    const payload = submissionPayloadFor({
      sessionToken: "token",
      activeTask: { id: "mcq-1", type: "mcq" },
      elapsedTimeSeconds: 12,
      selectedChoice: "answer",
      codeAnswer: "",
    });

    expect(payload).toEqual({
      sessionToken: "token",
      taskId: "mcq-1",
      elapsedTimeSeconds: 12,
      skipped: false,
      selectedChoice: "answer",
    });
    expect(payload).not.toHaveProperty("completionRatio");
  });
});
