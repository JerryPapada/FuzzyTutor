import API_URL from "../api/apiConfig";

export async function fetchModules() {
  const response = await fetch(`${API_URL}/learning/modules/`);
  return response.json();
}

export async function fetchTasks() {
  const response = await fetch(`${API_URL}/learning/tasks/`);
  return response.json();
}

export async function createSession() {
  const response = await fetch(`${API_URL}/learning/sessions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    throw new Error(`Session creation failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchSession(token) {
  const response = await fetch(`${API_URL}/learning/sessions/${token}/`);
  if (!response.ok) {
    throw new Error(`Session fetch failed: ${response.status}`);
  }
  return response.json();
}

export async function submitSubmission(data) {
  const response = await fetch(`${API_URL}/learning/submissions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || `Submission failed: ${response.status}`);
  }
  return response.json();
}

export async function submitMicroSurvey(data) {
  const response = await fetch(`${API_URL}/learning/micro-surveys/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || `Micro-survey failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchSessionReview(token) {
  const response = await fetch(`${API_URL}/learning/sessions/${token}/review/`);
  if (!response.ok) {
    throw new Error(`Session review fetch failed: ${response.status}`);
  }
  return response.json();
}