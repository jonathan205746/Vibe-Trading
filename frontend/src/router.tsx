import { createBrowserRouter } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";
import { Home } from "@/pages/Home";
import { Agent } from "@/pages/Agent";
import { RunDetail } from "@/pages/RunDetail";
import { Compare } from "@/pages/Compare";

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Home /> },
      { path: "/agent", element: <Agent /> },
      { path: "/runs/:runId", element: <RunDetail /> },
      { path: "/compare", element: <Compare /> },
    ],
  },
]);
