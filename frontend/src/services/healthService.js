import API_URL from "../api/apiConfig";

export async function fetchHealth() {
  const response = await fetch(`${API_URL}/health/`);
  return response.json();
}
