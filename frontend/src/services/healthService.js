import API_URL from "../api/apiConfig";
import { readJsonResponse } from "./apiResponse";

export async function fetchHealth() {
  const response = await fetch(`${API_URL}/health/`);
  return readJsonResponse(response, "Health check failed");
}
