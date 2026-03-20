/**
 * zustand/useDatasetStore.js
 * ──────────────────────────────────────────────────────────────────────────────
 * Manages the currently active dataset + schema.
 * Components call useDatasetStore() to read/set schema anywhere in the tree.
 */
import { create } from 'zustand'

export const useDatasetStore = create((set, get) => ({
  // The full schema object from GET /api/schema
  schema:    null,
  datasetId: null,   // UUID string
  datasets:  [],     // list of available datasets from GET /api/datasets

  // Actions
  setDatasets(datasets) {
    set({ datasets })
  },

  setSchema(schema) {
    set({ schema, datasetId: schema?.dataset_id ?? null })
  },

  clearSchema() {
    set({ schema: null, datasetId: null })
  },

  // Convenience getters
  get columns()    { return get().schema?.columns    ?? [] },
  get rowCount()   { return get().schema?.row_count  ?? 0  },
  get datasetName(){ return get().schema?.dataset_name ?? '' },
}))
