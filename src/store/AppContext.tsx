import React, { createContext, useContext, useMemo, useState } from "react";

type AppState = {
  lastGeneratedModule: string | null;
};

type AppContextValue = {
  state: AppState;
  setLastGeneratedModule: (moduleName: string) => void;
};

const AppContext = createContext<AppContextValue | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const [state, setState] = useState<AppState>({ lastGeneratedModule: null });

  const value = useMemo(
    () => ({
      state,
      setLastGeneratedModule: (moduleName: string) => {
        setState((prev) => ({ ...prev, lastGeneratedModule: moduleName }));
      },
    }),
    [state],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error("useAppContext must be used within AppProvider");
  }
  return ctx;
}
