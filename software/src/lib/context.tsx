import { createContext, useContext, useState, ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "./api";
import type { User } from "../types";
const AuthContext = createContext<{
  user: User | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}>({
  user: null,
  loading: true,
  refresh: async () => {},
  logout: async () => {},
});
const ToastContext = createContext<(message: string) => void>(() => {});
export function Providers({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  const [toast, setToast] = useState("");
  const me = useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      try {
        return await api<User>("/me");
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
    retry: false,
  });
  const refresh = async () => {
    await client.invalidateQueries({ queryKey: ["me"] });
  };
  const logout = async () => {
    await api("/auth/logout", { method: "POST" });
    client.clear();
    await refresh();
  };
  const notify = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 4500);
  };
  return (
    <AuthContext.Provider
      value={{ user: me.data ?? null, loading: me.isLoading, refresh, logout }}
    >
      <ToastContext.Provider value={notify}>
        {children}
        {toast && (
          <div className="toast" role="status">
            {toast}
            <button
              onClick={() => setToast("")}
              aria-label="Затвори известието"
            >
              ×
            </button>
          </div>
        )}
      </ToastContext.Provider>
    </AuthContext.Provider>
  );
}
export const useAuth = () => useContext(AuthContext);
export const useToast = () => useContext(ToastContext);
