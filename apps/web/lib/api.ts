const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://10.241.185.131:5000";

export type HealthResponse = { Health: string };
export type SummaryResponse = {
  data: {
    total_expense: number;
    total_income: number;
    savings: number;
    max_spending_category: string;
  };
};
export type HealthScoreResponse = { "Health Score": number };
export type UploadResponse = {
  message: string;
  filename: string;
  data?: Record<string, unknown>;
};
export type GoalRequest = {
  goal_name: string;
  target_amount: number;
  time_horizon_months: number;
  risk_level: "Low" | "Medium" | "High";
};
export type GoalResponse = {
  Decision: string;
  "Monthly Saving Required": number;
};

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function getSummary(): Promise<SummaryResponse> {
  const res = await fetch(`${API_BASE}/analytics/summary`);
  if (!res.ok) throw new Error("Failed to fetch summary");
  return res.json();
}

export async function getHealthScore(): Promise<HealthScoreResponse> {
  const res = await fetch(`${API_BASE}/analytics/health_score`);
  if (!res.ok) throw new Error("Failed to fetch health score");
  return res.json();
}

export async function uploadBankStatement(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/upload_bank_statement`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Failed to upload bank statement");
  return res.json();
}

export async function evaluateGoal(
  payload: GoalRequest
): Promise<GoalResponse> {
  const res = await fetch(`${API_BASE}/goal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to evaluate goal");
  return res.json();
}


