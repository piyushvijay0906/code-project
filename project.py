/*
AI Financial Tool - Single-file React app (App.jsx)
Features:
- Automated expense categorization (keyword-based)
- Expense list with add/edit/remove (localStorage)
- Predictive spending (simple linear regression per category)
- Goal tracking & budget alerts
- Modern responsive dashboard with charts (Recharts)

How to run:
1. Create a React app (Vite or create-react-app). Example using Vite:
   npm create vite@latest my-finance-app --template react
   cd my-finance-app
2. Install dependencies:
   npm install recharts framer-motion
   (Tailwind: follow tailwind setup for your project OR use CDN in index.html for quick demo)
3. Replace src/App.jsx with this file, add Tailwind if available, then run:
   npm install
   npm run dev

This file is intentionally self-contained for demo purposes. For production, split components, add tests and secure the categorization/prediction using server-side models or APIs.
*/

import React, { useEffect, useMemo, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar, Legend } from "recharts";
import { motion } from "framer-motion";

// --- Helper: simple categorizer ---
const CATEGORY_KEYWORDS = {
  Groceries: ["groc", "market", "super", "walmart", "aldi", "pmt", "veg", "fruit"],
  Transport: ["uber", "ola", "taxi", "bus", "rail", "metro", "fuel", "petrol", "diesel"],
  Entertainment: ["netflix", "prime", "movie", "spotify", "concert", "game"],
  Bills: ["electric", "water", "internet", "gas", "bill", "phone", "rent"],
  Dining: ["cafe", "restaurant", "dine", "coffee", "cafe"],
  Health: ["doc", "pharm", "clinic", "hospital", "med", "fitness"],
  Shopping: ["amazon", "flipkart", "mall", "shirt", "clothes", "shoe", "store"],
  Others: [""]
};

function categorizeExpense(description) {
  const text = (description || "").toLowerCase();
  for (const [cat, keys] of Object.entries(CATEGORY_KEYWORDS)) {
    for (const k of keys) {
      if (!k) continue;
      if (text.includes(k)) return cat;
    }
  }
  // fallback using heuristics
  if (/\d+\s?km|journey|trip/.test(text)) return "Transport";
  return "Others";
}

// --- Simple Linear Regression to forecast next value ---
function linearForecast(values, monthsToForecast = 1) {
  // values: array of numbers ordered by time (old..new)
  const n = values.length;
  if (n === 0) return null;
  if (n === 1) return values[0];
  // x: 0..n-1
  const xs = Array.from({ length: n }, (_, i) => i);
  const xMean = xs.reduce((a, b) => a + b, 0) / n;
  const yMean = values.reduce((a, b) => a + b, 0) / n;
  let num = 0,
    den = 0;
  for (let i = 0; i < n; i++) {
    num += (xs[i] - xMean) * (values[i] - yMean);
    den += (xs[i] - xMean) * (xs[i] - xMean);
  }
  const slope = den === 0 ? 0 : num / den;
  const intercept = yMean - slope * xMean;
  // forecast next month(s)
  const nextX = n + (monthsToForecast - 1);
  return intercept + slope * nextX;
}

// --- Utilities ---
function formatCurrency(n) {
  return (typeof n === "number" ? n : 0).toLocaleString(undefined, { style: "currency", currency: "INR", maximumFractionDigits: 0 });
}

function monthKey(date) {
  const d = new Date(date);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

// sample starter data
const SAMPLE_EXPENSES = [
  { id: 1, date: "2025-05-02", amount: 4200, description: "Walmart Groceries" },
  { id: 2, date: "2025-05-10", amount: 199, description: "Metro Ride" },
  { id: 3, date: "2025-06-03", amount: 850, description: "Dinner at cafe" },
  { id: 4, date: "2025-06-06", amount: 1500, description: "Electric Bill" },
  { id: 5, date: "2025-07-11", amount: 1200, description: "Amazon Shopping - Shoes" },
  { id: 6, date: "2025-08-02", amount: 5200, description: "Monthly Groceries" },
  { id: 7, date: "2025-08-07", amount: 300, description: "Coffee" },
  { id: 8, date: "2025-08-19", amount: 1800, description: "Fuel" }
];

const COLORS = ["#4dc9f6", "#f67019", "#f53794", "#537bc4", "#acc236", "#166a8f", "#00a950", "#58595b"];

export default function App() {
  const [expenses, setExpenses] = useState(() => {
    try {
      const raw = localStorage.getItem("ai_fin_expenses");
      return raw ? JSON.parse(raw) : SAMPLE_EXPENSES;
    } catch (e) {
      return SAMPLE_EXPENSES;
    }
  });
  const [budget, setBudget] = useState(() => {
    const raw = localStorage.getItem("ai_fin_budget");
    return raw ? JSON.parse(raw) : { monthly: 30000, byCategory: { Groceries: 8000, Transport: 3000, Entertainment: 2000 } };
  });
  const [goal, setGoal] = useState(() => {
    const raw = localStorage.getItem("ai_fin_goal");
    return raw ? JSON.parse(raw) : { name: "Emergency Fund", target: 50000, saved: 12000 };
  });

  useEffect(() => localStorage.setItem("ai_fin_expenses", JSON.stringify(expenses)), [expenses]);
  useEffect(() => localStorage.setItem("ai_fin_budget", JSON.stringify(budget)), [budget]);
  useEffect(() => localStorage.setItem("ai_fin_goal", JSON.stringify(goal)), [goal]);

  // enrich expenses with categories
  const enriched = useMemo(() => {
    return expenses.map((e) => ({ ...e, category: e.category || categorizeExpense(e.description) }));
  }, [expenses]);

  // monthly totals per monthKey
  const monthlyTotals = useMemo(() => {
    const map = {};
    for (const e of enriched) {
      const k = monthKey(e.date);
      map[k] = (map[k] || 0) + e.amount;
    }
    // sort keys ascending
    const rows = Object.keys(map).sort().map((k) => ({ month: k, total: Math.round(map[k]) }));
    return rows;
  }, [enriched]);

  // category-wise totals
  const categoryTotals = useMemo(() => {
    const map = {};
    for (const e of enriched) {
      map[e.category] = (map[e.category] || 0) + e.amount;
    }
    return Object.entries(map).map(([name, value]) => ({ name, value }));
  }, [enriched]);

  // predictive analytics: forecast next month total & per-category
  const forecasts = useMemo(() => {
    // prepare time series per month
    const months = monthlyTotals.map((r) => r.month);
    const monthIndex = months.reduce((acc, m, i) => ((acc[m] = i), acc), {});
    // build category-time matrix
    const categories = Array.from(new Set(enriched.map((e) => e.category)));
    const catSeries = {};
    for (const c of categories) catSeries[c] = Array(months.length).fill(0);
    for (const e of enriched) {
      const m = monthKey(e.date);
      const idx = monthIndex[m];
      if (idx === undefined) continue;
      catSeries[e.category][idx] += e.amount;
    }
    const catForecast = {};
    for (const c of categories) {
      catForecast[c] = Math.max(0, Math.round(linearForecast(catSeries[c], 1) || 0));
    }
    const totalSeries = monthlyTotals.map((r) => r.total);
    const totalForecast = Math.max(0, Math.round(linearForecast(totalSeries, 1) || 0));
    return { totalForecast, catForecast };
  }, [monthlyTotals, enriched]);

  // budget alerts
  const alerts = useMemo(() => {
    const alertsList = [];
    // projected month: current month key
    // compare forecasts per category
    for (const [cat, proj] of Object.entries(forecasts.catForecast || {})) {
      const limit = budget.byCategory?.[cat];
      if (limit && proj > limit) alertsList.push({ type: "category", category: cat, projected: proj, limit });
    }
    if (forecasts.totalForecast > budget.monthly) alertsList.push({ type: "total", projected: forecasts.totalForecast, limit: budget.monthly });
    return alertsList;
  }, [forecasts, budget]);

  // add expense
  function addExpense({ date, amount, description }) {
    const id = Date.now();
    const category = categorizeExpense(description);
    setExpenses((s) => [{ id, date, amount: Number(amount), description, category }, ...s]);
  }

  function removeExpense(id) {
    setExpenses((s) => s.filter((x) => x.id !== id));
  }

  // quick stats
  const totalSpent = monthlyTotals.length ? monthlyTotals[monthlyTotals.length - 1].total : 0;

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8 font-sans">
      <div className="max-w-7xl mx-auto">
        <header className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold">AI Finance — Predictive Dashboard</h1>
            <p className="text-sm text-gray-600">Automated expense categorization, forecasts, and budget alerts</p>
          </div>
          <div className="text-right">
            <div className="text-gray-700">Monthly Budget</div>
            <div className="font-semibold text-lg">{formatCurrency(budget.monthly)}</div>
          </div>
        </header>

        <main className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column: controls + expense list */}
          <section className="col-span-1 lg:col-span-1 bg-white p-4 rounded-2xl shadow-sm">
            <h2 className="font-semibold mb-2">Add Expense</h2>
            <AddExpenseForm onAdd={addExpense} />

            <hr className="my-4" />

            <h3 className="font-semibold mb-2">Recent Expenses</h3>
            <div className="space-y-2 max-h-96 overflow-auto">
              {enriched.map((e) => (
                <motion.div key={e.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between border p-2 rounded">
                  <div>
                    <div className="font-medium">{e.description}</div>
                    <div className="text-xs text-gray-500">{new Date(e.date).toLocaleDateString()} • {e.category}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold">{formatCurrency(e.amount)}</div>
                    <button onClick={() => removeExpense(e.id)} className="text-xs text-red-500 hover:underline mt-1">Remove</button>
                  </div>
                </motion.div>
              ))}
            </div>
          </section>

          {/* Middle column: charts */}
          <section className="col-span-1 lg:col-span-2 bg-white p-4 rounded-2xl shadow-sm">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-2">
                <h3 className="font-semibold mb-2">Monthly Spending</h3>
                <div style={{ width: "100%", height: 220 }}>
                  <ResponsiveContainer>
                    <LineChart data={monthlyTotals}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" />
                      <YAxis />
                      <Tooltip />
                      <Line type="monotone" dataKey="total" stroke="#4dc9f6" strokeWidth={3} dot={{ r: 3 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-2 text-sm text-gray-600">Forecast next month: <strong>{formatCurrency(forecasts.totalForecast)}</strong></div>
              </div>

              <div className="p-2">
                <h3 className="font-semibold mb-2">Category Breakdown</h3>
                <div style={{ width: "100%", height: 220 }}>
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie data={categoryTotals} dataKey="value" nameKey="name" innerRadius={40} outerRadius={80} label>
                        {categoryTotals.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="md:col-span-2 p-2">
                <h3 className="font-semibold mb-2">Category Spending History</h3>
                <div style={{ width: "100%", height: 260 }}>
                  <ResponsiveContainer>
                    <BarChart data={buildCategoryHistory(enriched)}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      {Object.keys(buildCategoryHistory(enriched)[0] || {})
                        .filter((k) => k !== "month")
                        .map((cat, idx) => (
                          <Bar key={cat} dataKey={cat} stackId="a" fill={COLORS[idx % COLORS.length]} />
                        ))}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </section>

          {/* Bottom: analytics & alerts */}
          <section className="col-span-1 lg:col-span-3 bg-white p-4 rounded-2xl shadow-sm">
            <div className="md:flex md:items-center md:justify-between">
              <div>
                <h3 className="font-semibold">Predictive Analytics & Goals</h3>
                <p className="text-sm text-gray-600">Projected next month by category</p>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-500">Goal: {goal.name}</div>
                <div className="font-semibold">{formatCurrency(goal.saved)} / {formatCurrency(goal.target)}</div>
              </div>
            </div>

            <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(forecasts.catForecast || {}).map(([cat, val], i) => (
                <div key={cat} className="p-3 border rounded">
                  <div className="text-sm text-gray-600">{cat}</div>
                  <div className="font-bold text-xl">{formatCurrency(val)}</div>
                  <div className="text-xs text-gray-500 mt-1">Budget: {budget.byCategory?.[cat] ? formatCurrency(budget.byCategory[cat]) : "—"}</div>
                </div>
              ))}
            </div>

            <div className="mt-4">
              <h4 className="font-semibold">Alerts</h4>
              {alerts.length === 0 ? (
                <div className="text-sm text-green-600 mt-2">All good — your projected spending is within budgets.</div>
              ) : (
                <div className="space-y-2 mt-2">
                  {alerts.map((a, i) => (
                    <div key={i} className="p-3 rounded bg-red-50 border-l-4 border-red-400">
                      {a.type === "total" ? (
                        <div>
                          <div className="font-semibold">Projected total {formatCurrency(a.projected)} exceeds monthly budget {formatCurrency(a.limit)}</div>
                        </div>
                      ) : (
                        <div>
                          <div className="font-semibold">{a.category} projected {formatCurrency(a.projected)} exceeds category budget {formatCurrency(a.limit)}</div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="mt-4">
              <h4 className="font-semibold">Tune Budget / Goal</h4>
              <BudgetEditor budget={budget} setBudget={setBudget} goal={goal} setGoal={setGoal} />
            </div>
          </section>
        </main>

        <footer className="mt-8 text-center text-xs text-gray-500">Demo AI Financial Tool • Data stored locally in your browser</footer>
      </div>
    </div>
  );
}

// --- Add expense form ---
function AddExpenseForm({ onAdd }) {
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [amount, setAmount] = useState(0);
  const [description, setDescription] = useState("");
  return (
    <form onSubmit={(e) => { e.preventDefault(); onAdd({ date, amount: Number(amount), description }); setAmount(0); setDescription(""); }} className="space-y-2">
      <div className="grid grid-cols-3 gap-2">
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="col-span-1 p-2 border rounded" />
        <input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Amount" className="col-span-1 p-2 border rounded" />
        <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description e.g. Grocery at Walmart" className="col-span-1 p-2 border rounded" />
      </div>
      <div>
        <button className="px-4 py-2 rounded bg-blue-600 text-white hover:opacity-90">Add Expense</button>
      </div>
    </form>
  );
}

// --- Build category history across months for BarChart ---
function buildCategoryHistory(expenses) {
  // gather month keys
  const monthsSet = new Set();
  for (const e of expenses) monthsSet.add(monthKey(e.date));
  const months = Array.from(monthsSet).sort();
  const categories = Array.from(new Set(expenses.map((e) => e.category)));
  const rows = months.map((m) => {
    const row = { month: m };
    for (const c of categories) row[c] = 0;
    return row;
  });
  const monthIndex = months.reduce((acc, m, i) => ((acc[m] = i), acc), {});
  for (const e of expenses) {
    const m = monthKey(e.date);
    const idx = monthIndex[m];
    if (idx === undefined) continue;
    rows[idx][e.category] = (rows[idx][e.category] || 0) + e.amount;
  }
  return rows;
}

function BudgetEditor({ budget, setBudget, goal, setGoal }) {
  const [monthly, setMonthly] = useState(budget.monthly);
  const [goalSaved, setGoalSaved] = useState(goal.saved);
  useEffect(() => setMonthly(budget.monthly), [budget]);
  useEffect(() => setGoalSaved(goal.saved), [goal]);
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      <div className="p-2">
        <label className="text-xs text-gray-600">Monthly budget</label>
        <input type="number" value={monthly} onChange={(e) => setMonthly(Number(e.target.value))} className="w-full p-2 border rounded mt-1" />
        <button className="mt-2 px-3 py-1 bg-green-600 text-white rounded" onClick={() => setBudget((b) => ({ ...b, monthly }))}>Save</button>
      </div>
      <div className="p-2">
        <label className="text-xs text-gray-600">Goal saved</label>
        <input type="number" value={goalSaved} onChange={(e) => setGoalSaved(Number(e.target.value))} className="w-full p-2 border rounded mt-1" />
        <button className="mt-2 px-3 py-1 bg-indigo-600 text-white rounded" onClick={() => setGoal((g) => ({ ...g, saved: goalSaved }))}>Update Goal</button>
      </div>
      <div className="p-2">
        <label className="text-xs text-gray-600">Category budgets (JSON)</label>
        <textarea className="w-full p-2 border rounded h-28 mt-1" defaultValue={JSON.stringify(budget.byCategory, null, 2)} onBlur={(e) => {
          try {
            const parsed = JSON.parse(e.target.value);
            setBudget((b) => ({ ...b, byCategory: parsed }));
          } catch (err) {
            alert("Invalid JSON");
          }
        }} />
        <div className="text-xs text-gray-500 mt-1">Edit JSON and click outside box to save.</div>
      </div>
    </div>
  );
}
