import { apiClient } from "../api/client";

export async function getDashboard() {
  const { data } = await apiClient.get("/dashboard");
  return data; // see app/schemas/dashboard.py's DashboardResponse
}
