import { ReactNode, useMemo } from "react";
import { Theme } from "@radix-ui/themes";
import { ApiProvider, type ApiClients } from "@llamaindex/ui";
import { Toaster } from "sonner";

import { createApiClients } from "@/lib/client";
import { ToolbarProvider } from "@/lib/ToolbarContext";

export function AppProviders({ children }: { children: ReactNode }) {
  const clients: ApiClients = useMemo(() => createApiClients(), []);

  return (
    <Theme>
      <ApiProvider clients={clients}>
        <ToolbarProvider>
          {children}
          <Toaster />
        </ToolbarProvider>
      </ApiProvider>
    </Theme>
  );
}

