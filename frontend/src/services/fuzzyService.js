import API_URL from "../api/apiConfig";

export async function submitEvaluation(data) {
  const response = await fetch(`${API_URL}/fuzzy/evaluate/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return response.json();
}
