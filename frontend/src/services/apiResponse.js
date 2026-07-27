function errorDetail(data) {
  if (!data || typeof data !== "object") {
    return "";
  }
  if (typeof data.detail === "string") {
    return data.detail;
  }
  return Object.entries(data)
    .flatMap(([field, messages]) => {
      const values = Array.isArray(messages) ? messages : [messages];
      return values.map((message) => `${field}: ${message}`);
    })
    .join(" ");
}

export async function readJsonResponse(response, fallbackMessage) {
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(`${fallbackMessage}: invalid JSON response (${response.status})`);
  }

  if (!response.ok) {
    throw new Error(errorDetail(data) || `${fallbackMessage}: ${response.status}`);
  }

  return data;
}
