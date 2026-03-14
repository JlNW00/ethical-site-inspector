import { Navigate, Route, Routes } from "react-router-dom";

import { ComparePage } from "./pages/ComparePage";
import { HistoryPage } from "./pages/HistoryPage";
import { PersonaDiffPage } from "./pages/PersonaDiffPage";
import { ReportPage } from "./pages/ReportPage";
import { RunPage } from "./pages/RunPage";
import { SubmitPage } from "./pages/SubmitPage";
import { BenchmarkPage } from "./pages/BenchmarkPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<SubmitPage />} />
      <Route path="/history" element={<HistoryPage />} />
      <Route path="/compare" element={<ComparePage />} />
      <Route path="/audits/:auditId/run" element={<RunPage />} />
      <Route path="/audits/:auditId/report" element={<ReportPage />} />
      <Route path="/audits/:auditId/diff" element={<PersonaDiffPage />} />
      <Route path="/benchmarks/:benchmarkId" element={<BenchmarkPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
