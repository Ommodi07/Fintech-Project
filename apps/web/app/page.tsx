"use client";

import { useState, useEffect } from "react";
import { Button } from "@repo/ui/components/button";
import { RequireAuth } from "@/components/require-auth";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@repo/ui/components/card";
import { Input } from "@repo/ui/components/input";
import { Label } from "@repo/ui/components/label";
import { Badge } from "@repo/ui/components/badge";
import { Progress } from "@repo/ui/components/progress";
import {
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from "@repo/ui/components/sidebar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@repo/ui/components/select";
import { AppSidebar } from "@/components/app-sidebar";
import {
  checkHealth,
  getSummary,
  getHealthScore,
  uploadBankStatement,
  evaluateGoal,
  type GoalRequest,
} from "@/lib/api";
import {
  TrendingUp,
  Wallet,
  PieChart,
  Loader2,
  CheckCircle2,
  XCircle,
  FileUp,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

const CHART_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

type View = "overview" | "upload" | "goal";

export default function FintechDashboard() {
  const [activeView, setActiveView] = useState<View>("overview");
  const [healthStatus, setHealthStatus] = useState<"ok" | "error" | "loading">(
    "loading",
  );
  const [summary, setSummary] = useState<{
    total_expense: number;
    total_income: number;
    savings: number;
    max_spending_category: string;
  } | null>(null);
  const [healthScore, setHealthScore] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);
  const [goalResult, setGoalResult] = useState<{
    decision: string;
    monthlySaving: number;
  } | null>(null);
  const [evaluatingGoal, setEvaluatingGoal] = useState(false);
  const [goalForm, setGoalForm] = useState<GoalRequest>({
    goal_name: "",
    target_amount: 0,
    time_horizon_months: 12,
    risk_level: "Medium",
  });

  const fetchHealth = async () => {
    setHealthStatus("loading");
    try {
      await checkHealth();
      setHealthStatus("ok");
    } catch {
      setHealthStatus("error");
    }
  };

  const fetchSummary = async () => {
    try {
      const res = await getSummary();
      setSummary(res.data);
    } catch {
      setSummary(null);
    }
  };

  const fetchHealthScore = async () => {
    try {
      const res = await getHealthScore();
      setHealthScore(res["Health Score"]);
    } catch {
      setHealthScore(null);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  useEffect(() => {
    if (healthStatus === "ok") {
      fetchSummary();
      fetchHealthScore();
    }
  }, [healthStatus]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadResult(null);
    try {
      await uploadBankStatement(file);
      setUploadResult(`Successfully processed ${file.name}`);
      await Promise.all([fetchSummary(), fetchHealthScore()]);
    } catch (err) {
      setUploadResult(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleGoalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goalForm.goal_name || !goalForm.target_amount) return;
    setEvaluatingGoal(true);
    setGoalResult(null);
    try {
      const res = await evaluateGoal(goalForm);
      setGoalResult({
        decision: res.Decision,
        monthlySaving: res["Monthly Saving Required"],
      });
    } catch (err) {
      setGoalResult({
        decision:
          err instanceof Error ? err.message : "Failed to evaluate goal",
        monthlySaving: 0,
      });
    } finally {
      setEvaluatingGoal(false);
    }
  };

  const summaryChartData = summary
    ? [
        { name: "Income", value: summary.total_income, fill: CHART_COLORS[1] },
        {
          name: "Expense",
          value: summary.total_expense,
          fill: CHART_COLORS[0],
        },
        { name: "Savings", value: summary.savings, fill: CHART_COLORS[2] },
      ]
    : [];

  const formattedCurrency = (n: number) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(n);

  return (
    <RequireAuth>
      <SidebarProvider>
        <AppSidebar activeView={activeView} onViewChange={setActiveView} />
      <SidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger className="-ml-1" />
          <div className="h-4 w-px bg-border" />
          <div className="flex flex-1 items-center justify-between">
            <h1 className="text-lg font-semibold">
              {activeView === "overview" && "Overview"}
              {activeView === "upload" && "Upload Statement"}
              {activeView === "goal" && "Goal Setter"}
            </h1>
            <div className="flex items-center gap-3">
              <Badge
                variant={healthStatus === "ok" ? "default" : "destructive"}
                className="gap-1.5"
              >
                {healthStatus === "loading" && (
                  <Loader2 className="size-3 animate-spin" />
                )}
                {healthStatus === "ok" && <CheckCircle2 className="size-3" />}
                {healthStatus === "error" && <XCircle className="size-3" />}
                {healthStatus === "ok"
                  ? "API Connected"
                  : healthStatus === "error"
                    ? "API Offline"
                    : "Connecting..."}
              </Badge>
              {healthStatus === "error" && (
                <Button variant="outline" size="sm" onClick={fetchHealth}>
                  Retry
                </Button>
              )}
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-4 md:p-6">
          {activeView === "overview" && (
            <div className="space-y-6">
              <div className="grid gap-4 md:grid-cols-3">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Total Income
                    </CardTitle>
                    <TrendingUp className="size-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {summary ? formattedCurrency(summary.total_income) : "—"}
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Total Expense
                    </CardTitle>
                    <PieChart className="size-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {summary ? formattedCurrency(summary.total_expense) : "—"}
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Savings
                    </CardTitle>
                    <Wallet className="size-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {summary ? formattedCurrency(summary.savings) : "—"}
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="grid gap-6 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Financial Health Score</CardTitle>
                    <CardDescription>
                      Based on volatility, savings rate & discretionary spending
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-end justify-between">
                        <span className="text-4xl font-bold">
                          {healthScore != null ? healthScore.toFixed(1) : "—"}
                        </span>
                        <span className="text-muted-foreground text-sm">
                          / 100
                        </span>
                      </div>
                      <Progress
                        value={healthScore != null ? healthScore : 0}
                        className="h-3"
                      />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Max Spending Category</CardTitle>
                    <CardDescription>
                      Category with highest expenditure
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-2">
                      <Badge
                        variant="secondary"
                        className="text-base px-3 py-1"
                      >
                        {summary?.max_spending_category ?? "—"}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {summary && summaryChartData.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Income vs Expense vs Savings</CardTitle>
                    <CardDescription>
                      Breakdown of your finances
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[300px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={summaryChartData}>
                          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                          <XAxis dataKey="name" />
                          <YAxis tickFormatter={(v) => `${(v ?? 0) / 1000}k`} />
                          <Tooltip
                            formatter={(v) =>
                              formattedCurrency(typeof v === "number" ? v : 0)
                            }
                          />
                          <Bar
                            dataKey="value"
                            name="Amount"
                            radius={[4, 4, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              )}

              {summary && summaryChartData.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Distribution</CardTitle>
                    <CardDescription>
                      Income, expense and savings as a pie chart
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[300px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <RechartsPieChart>
                          <Pie
                            data={summaryChartData}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={100}
                            paddingAngle={2}
                            dataKey="value"
                            nameKey="name"
                            label={({ name }) => name}
                          >
                            {summaryChartData.map((_, i) => (
                              <Cell key={i} fill={CHART_COLORS[i]} />
                            ))}
                          </Pie>
                          <Tooltip
                            formatter={(v) =>
                              formattedCurrency(typeof v === "number" ? v : 0)
                            }
                          />
                          <Legend />
                        </RechartsPieChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {activeView === "upload" && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Upload Bank Statement</CardTitle>
                  <CardDescription>
                    Upload a PDF bank statement to process and categorize
                    transactions
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-col items-center gap-4 rounded-lg border-2 border-dashed p-8">
                    <input
                      type="file"
                      accept=".pdf"
                      onChange={handleFileUpload}
                      disabled={uploading || healthStatus !== "ok"}
                      className="hidden"
                      id="bank-statement-upload"
                    />
                    <label
                      htmlFor="bank-statement-upload"
                      className="flex flex-col items-center gap-2 cursor-pointer"
                    >
                      <div className="rounded-full bg-muted p-4">
                        {uploading ? (
                          <Loader2 className="size-8 animate-spin text-muted-foreground" />
                        ) : (
                          <FileUp className="size-8 text-muted-foreground" />
                        )}
                      </div>
                      <span className="text-sm font-medium">
                        {uploading ? "Processing..." : "Click to upload PDF"}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        PDF files only
                      </span>
                    </label>
                    {uploadResult && (
                      <Badge
                        variant={
                          uploadResult.startsWith("Successfully")
                            ? "default"
                            : "destructive"
                        }
                      >
                        {uploadResult}
                      </Badge>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {activeView === "goal" && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Goal feasibility check</CardTitle>
                  <CardDescription>
                    Evaluate if your financial goal is achievable based on
                    current savings
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleGoalSubmit} className="space-y-4">
                    <div>
                      <Label htmlFor="goal_name">Goal Name</Label>
                      <Input
                        id="goal_name"
                        placeholder="e.g. Buy a Car"
                        value={goalForm.goal_name}
                        onChange={(e) =>
                          setGoalForm((p) => ({
                            ...p,
                            goal_name: e.target.value,
                          }))
                        }
                      />
                    </div>
                    <div>
                      <Label htmlFor="target_amount">Target Amount (₹)</Label>
                      <Input
                        id="target_amount"
                        type="number"
                        placeholder="20000"
                        value={goalForm.target_amount || ""}
                        onChange={(e) =>
                          setGoalForm((p) => ({
                            ...p,
                            target_amount: Number(e.target.value) || 0,
                          }))
                        }
                      />
                    </div>
                    <div>
                      <Label htmlFor="time_horizon_months">
                        Time Horizon (months)
                      </Label>
                      <Input
                        id="time_horizon_months"
                        type="number"
                        placeholder="24"
                        value={goalForm.time_horizon_months}
                        onChange={(e) =>
                          setGoalForm((p) => ({
                            ...p,
                            time_horizon_months: Number(e.target.value) || 12,
                          }))
                        }
                      />
                    </div>
                    <Button
                      type="submit"
                      disabled={
                        evaluatingGoal ||
                        !goalForm.goal_name ||
                        !goalForm.target_amount ||
                        healthStatus !== "ok"
                      }
                      className="w-full"
                    >
                      {evaluatingGoal ? (
                        <>
                          <Loader2 className="size-4 animate-spin mr-2" />
                          Evaluating...
                        </>
                      ) : (
                        "Evaluate Goal"
                      )}
                    </Button>
                  </form>

                  {goalResult && (
                    <div className="mt-6 p-4 rounded-lg bg-muted/50 space-y-2">
                      <p className="font-medium">{goalResult.decision}</p>
                      <p className="text-sm text-muted-foreground">
                        Monthly saving required:{" "}
                        {formattedCurrency(goalResult.monthlySaving)}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </main>
      </SidebarInset>
    </SidebarProvider>
    </RequireAuth>
  );
}
