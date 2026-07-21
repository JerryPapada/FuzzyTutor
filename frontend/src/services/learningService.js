import API_URL from "../api/apiConfig";

export async function fetchModules() {
  const response = await fetch(`${API_URL}/learning/modules/`);
  return response.json();
}

export async function fetchTasks() {
  const response = await fetch(`${API_URL}/learning/tasks/`);
  return response.json();
}