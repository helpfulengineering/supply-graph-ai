import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Layout } from "./components/layout/Layout";
import { HomePage } from "./pages/HomePage";
import { OkhPage } from "./pages/OkhPage";
import { MatchPage } from "./pages/MatchPage";
import { VisualizationPage } from "./pages/VisualizationPage";
import { RfqPage } from "./pages/RfqPage";
import { PackagePage } from "./pages/PackagePage";
import { ThemeContext } from "./context/ThemeContext";
import { useDarkMode } from "./hooks/useDarkMode";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export function App() {
  const theme = useDarkMode();

  return (
    <ThemeContext.Provider value={theme}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<HomePage />} />
              <Route path="okh" element={<OkhPage />} />
              <Route path="okh/:id" element={<OkhPage />} />
              <Route path="match" element={<MatchPage />} />
              <Route path="visualization" element={<VisualizationPage />} />
              <Route path="visualization/:solutionId" element={<VisualizationPage />} />
              <Route path="rfq" element={<RfqPage />} />
              <Route path="packages" element={<PackagePage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeContext.Provider>
  );
}
