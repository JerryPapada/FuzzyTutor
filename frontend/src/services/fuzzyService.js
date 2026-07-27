import API_URL from "../api/apiConfig";
import { readJsonResponse } from "./apiResponse";

export async function submitEvaluation(data) {
  const response = await fetch(`${API_URL}/fuzzy/evaluate/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return readJsonResponse(response, "Fuzzy evaluation failed");
}
