import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { queryClient, persistOptions } from "./queryClient";
import { Layout } from "./components/layout/Layout";
import { HomePage } from "./pages/HomePage";
import { OkhPage } from "./pages/OkhPage";
import { OkhFilePreviewPage } from "./features/okh/OkhFilePreviewPage";
import { OkwPage } from "./pages/OkwPage";
import { MatchPage } from "./pages/MatchPage";
import { VisualizationPage } from "./pages/VisualizationPage";
import { RfqPage } from "./pages/RfqPage";
import { PackagePage } from "./pages/PackagePage";
import { ThemeContext } from "./context/ThemeContext";
import { useDarkMode } from "./hooks/useDarkMode";

export function App() {
  const theme = useDarkMode();

  return (
    <ThemeContext.Provider value={theme}>
      <PersistQueryClientProvider client={queryClient} persistOptions={persistOptions}>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<HomePage />} />
              <Route path="okh" element={<OkhPage />} />
              <Route path="okh/:id/files/*" element={<OkhFilePreviewPage />} />
              <Route path="okh/:id" element={<OkhPage />} />
              <Route path="facilities" element={<OkwPage />} />
              <Route path="facilities/:id" element={<OkwPage />} />
              <Route path="match" element={<MatchPage />} />
              {/* Supply trees are reached directly from their match; no browse list. */}
              <Route path="visualization" element={<Navigate to="/" replace />} />
              <Route path="visualization/:solutionId" element={<VisualizationPage />} />
              <Route path="rfq" element={<RfqPage />} />
              <Route path="packages" element={<PackagePage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </PersistQueryClientProvider>
    </ThemeContext.Provider>
  );
}
