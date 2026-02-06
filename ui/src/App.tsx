import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "@llamaindex/ui";
import { Link } from "react-router-dom";
import { useToolbar } from "@/lib/ToolbarContext";
import { AppProviders } from "@/lib/AppProviders";

import ResearchPage from "./pages/ResearchPage";
import ResearchSessionPage from "./pages/ResearchSessionPage";

export default function App() {
  return (
    <AppProviders>
      <div className="grid grid-rows-[auto_1fr] h-screen">
        <Toolbar />
        <main className="overflow-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/research" replace />} />
            <Route path="/research" element={<ResearchPage />} />
            <Route path="/research/:researchId" element={<ResearchSessionPage />} />
            <Route path="*" element={<Navigate to="/research" replace />} />
          </Routes>
        </main>
      </div>
    </AppProviders>
  );
}

const Toolbar = () => {
  const { buttons, breadcrumbs } = useToolbar();

  return (
    <header className="sticky top-0 z-50 flex h-16 shrink-0 items-center gap-2 border-b px-4 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <Breadcrumb>
        <BreadcrumbList>
          {breadcrumbs.map((item, index) => (
            <React.Fragment key={index}>
              {index > 0 && <BreadcrumbSeparator />}
              <BreadcrumbItem>
                {item.href && !item.isCurrentPage ? (
                  <Link to={item.href} className="font-medium text-base">
                    {item.label}
                  </Link>
                ) : (
                  <span
                    className={`font-medium ${index === 0 ? "text-base" : ""}`}
                  >
                    {item.label}
                  </span>
                )}
              </BreadcrumbItem>
            </React.Fragment>
          ))}
        </BreadcrumbList>
      </Breadcrumb>
      {buttons}
    </header>
  );
};
