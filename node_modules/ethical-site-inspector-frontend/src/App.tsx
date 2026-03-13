import { Navigate, Route, Routes } from "react-router-dom";

import { ReportPage } from "./pages/ReportPage";
import { RunPage } from "./pages/RunPage";
import { SubmitPage } from "./pages/SubmitPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<SubmitPage />} />
      <Route path="/audits/:auditId/run" element={<RunPage />} />
      <Route path="/audits/:auditId/report" element={<ReportPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
