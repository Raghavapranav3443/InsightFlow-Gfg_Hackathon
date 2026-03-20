/**
 * zustand/useUIStore.js
 * ──────────────────────────────────────────────────────────────────────────────
 * Global UI state: sidebar panel, theme, loading overlays, view mode.
 */
import { create } from 'zustand'

export const useUIStore = create((set) => ({
  // Sidebar
  sidebarOpen:  true,
  sidebarPanel: 'schema',   // 'schema' | 'history' | 'saved'

  // View mode in QueryExplorer
  viewMode: 'analytics',    // 'analytics' | 'data'

  // Global loading (e.g. dataset switch)
  globalLoading: false,

  // Actions
  toggleSidebar()          { set(s => ({ sidebarOpen: !s.sidebarOpen })) },
  setSidebarPanel(panel)   { set({ sidebarPanel: panel, sidebarOpen: true }) },
  setViewMode(mode)        { set({ viewMode: mode }) },
  setGlobalLoading(v)      { set({ globalLoading: v }) },
}))
