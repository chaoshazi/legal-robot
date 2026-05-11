import { create } from "zustand";
import type { User } from "../types";
import { authApi } from "../api/auth";

interface AuthState {
  user: User | null;
  token: string | null;
  isRestoring: boolean;
  setAuth: (user: User, token: string) => void;
  logout: () => void;
  isLoggedIn: () => boolean;
  restoreUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem("access_token"),
  isRestoring: !!localStorage.getItem("access_token"),

  setAuth: (user, token) => {
    localStorage.setItem("access_token", token);
    set({ user, token });
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    set({ user: null, token: null });
  },

  isLoggedIn: () => {
    return !!get().token;
  },

  restoreUser: async () => {
    const token = get().token || localStorage.getItem("access_token");
    if (!token) {
      set({ isRestoring: false });
      return;
    }
    try {
      const { data } = await authApi.getProfile();
      set({ user: data.data ?? null, isRestoring: false, token });
    } catch {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      set({ user: null, token: null, isRestoring: false });
    }
  },
}));
