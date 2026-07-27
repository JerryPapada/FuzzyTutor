import API_URL from "../api/apiConfig";
import { readJsonResponse } from "./apiResponse";

export async function fetchModules() {
  const response = await fetch(`${API_URL}/learning/modules/`);
  return readJsonResponse(response, "Module fetch failed");
}

export async function fetchTasks() {
  const response = await fetch(`${API_URL}/learning/tasks/`);
  return readJsonResponse(response, "Task fetch failed");
}

export async function createSession() {
  const response = await fetch(`${API_URL}/learning/sessions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  return readJsonResponse(response, "Session creation failed");
}

export async function fetchSession(token) {
  const response = await fetch(
    `${API_URL}/learning/sessions/${encodeURIComponent(token)}/`,
  );
  return readJsonResponse(response, "Session fetch failed");
}

export async function submitSubmission(data) {
  const response = await fetch(`${API_URL}/learning/submissions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return readJsonResponse(response, "Submission failed");
}

export async function submitMicroSurvey(data) {
  const response = await fetch(`${API_URL}/learning/micro-surveys/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return readJsonResponse(response, "Micro-survey failed");
}

export async function fetchSessionReview(token) {
  const response = await fetch(
    `${API_URL}/learning/sessions/${encodeURIComponent(token)}/review/`,
  );
  return readJsonResponse(response, "Session review fetch failed");
}

export async function revealHint(data) {
  const response = await fetch(`${API_URL}/learning/hints/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return readJsonResponse(response, "Hint request failed");
}
