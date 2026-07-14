import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import axios from 'axios';

// Get API base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const ROOT_URL = API_BASE_URL.replace(/\/api\/?$/, '');

// Create customized axios instance for store
const storeApi = axios.create({
  baseURL: ROOT_URL,
});

storeApi.interceptors.request.use((config) => {
  let token = null;
  try {
    const raw = sessionStorage.getItem('my_data_platform_auth') || localStorage.getItem('my_data_platform_auth');
    if (raw) {
      token = JSON.parse(raw)?.token;
    }
  } catch (e) {
    console.error("Error reading auth token in storeApi", e);
  }
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

const useDataStore = create(
  persist(
    (set, get) => ({
  // State Variables
  rawData: [],
  cleanedData: [],
  columns: [],
  isLoading: false,
  progress: 0,
  healthScore: null,
  aiInsights: "",
  fileObject: null,

  // Additional Backend States
  analysis: null,
  domainData: null,
  qualityReport: null,
  mlResult: null,
  mlLoading: false,
  mlProgress: 0,
  mlStatus: "",
  schedulesList: [],

  // Actions (FastAPI Backend Calls)
  uploadData: async (file) => {
    set({ isLoading: true, progress: 10, fileObject: file });
    const formData = new FormData();
    formData.append("file", file);
    
    try {
      const response = await storeApi.post("/upload", formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      const data = response.data;
      const nullPercentage = data.analysis?.null_percentage || 0;
      const score = Math.max(10, Math.round(100 - nullPercentage));
      
      const mappedCols = data.analysis?.column_info 
        ? data.analysis.column_info.map(c => typeof c === 'object' && c !== null ? c.name || c.column_name : c).filter(Boolean)
        : Object.keys(data.grid_data[0] || {});

      set({ 
        rawData: data.grid_data || [], 
        columns: mappedCols,
        analysis: data.analysis || null,
        domainData: data.analysis?.domain_info || null,
        healthScore: {
          score: score,
          null_cells: data.analysis?.null_count || 0,
          duplicate_rows: data.analysis?.duplicate_count || 0,
        },
        isLoading: false,
        progress: 100 
      });
    } catch (error) {
      console.error("Upload failed", error);
      set({ isLoading: false });
    }
  },

  cleanAndEngineerData: async () => {
    const file = get().fileObject;
    if (!file) {
      console.error("No file object found for cleaning.");
      return;
    }
    
    set({ isLoading: true, progress: 20 });
    const formData = new FormData();
    formData.append("file", file);
    
    try {
      const response = await storeApi.post("/api/clean-background", formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const { task_id } = response.data;
      if (!task_id) {
        throw new Error("No task_id returned from clean endpoint.");
      }
      
      // Start polling
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await storeApi.get(`/api/task-status/${task_id}`);
          const { state, status, progress, result } = statusRes.data;
          
          if (state === "PROGRESS" || state === "STARTED") {
            set({ 
              progress: progress || get().progress,
              aiInsights: status || "Processing..."
            });
          } else if (state === "SUCCESS") {
            clearInterval(pollInterval);
            
            // Fetch catalog detail using catalog_id from task result
            const catalogId = result?.catalog_id;
            if (catalogId) {
              const catalogRes = await storeApi.get(`/api/catalog/${catalogId}`);
              const catalog = catalogRes.data;
              const engNotes = catalog.summary?.cleaning_stats?.engineering_notes || [];
              
              const mappedCols = catalog.summary?.column_info 
                ? catalog.summary.column_info.map(c => typeof c === 'object' && c !== null ? c.name || c.column_name : c).filter(Boolean)
                : Object.keys(catalog.preview_data[0] || {});

              set({
                cleanedData: catalog.preview_data || [],
                columns: mappedCols,
                analysis: catalog.summary || null,
                domainData: catalog.summary?.domain_info || null,
                aiInsights: engNotes.length > 0 
                  ? `Auto-Feature Engineering Complete: ${engNotes.join(' ')}`
                  : "Data cleaning complete.",
                isLoading: false,
                progress: 100
              });
            } else {
              set({
                cleanedData: get().rawData,
                aiInsights: "Data cleaning complete.",
                isLoading: false,
                progress: 100
              });
            }
          } else if (state === "FAILURE" || state === "REVOKED") {
            clearInterval(pollInterval);
            set({ isLoading: false, progress: 0, aiInsights: "Cleaning failed." });
          }
        } catch (pollError) {
          console.error("Error polling task status:", pollError);
          clearInterval(pollInterval);
          set({ isLoading: false });
        }
      }, 1000);
      
    } catch (error) {
      console.error("Cleaning trigger failed:", error);
      set({ isLoading: false });
    }
  },

  // 🏥 Data Quality report generation action
  getQualityReport: async () => {
    const dataRows = get().cleanedData.length > 0 ? get().cleanedData : get().rawData;
    if (!dataRows || dataRows.length === 0) return;

    try {
      const response = await storeApi.post("/api/quality/report", { rows: dataRows });
      set({ qualityReport: response.data.report || null });
    } catch (error) {
      console.error("Failed to generate quality report", error);
    }
  },

  // 🤖 AutoML Training Action
  runAutoML: async (targetColumn) => {
    const file = get().fileObject;
    if (!file || !targetColumn) return;

    set({ mlLoading: true, mlProgress: 10, mlStatus: "Starting AutoML Job...", mlResult: null });
    const formData = new FormData();
    formData.append("file", file);
    formData.append("target_column", targetColumn);

    try {
      const response = await storeApi.post("/api/predict-background", formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const { task_id, sync_result } = response.data;
      if (sync_result) {
        set({ mlResult: sync_result, mlLoading: false, mlProgress: 100, mlStatus: "Completed" });
        return;
      }

      if (!task_id) {
        throw new Error("No task_id returned from predict endpoint.");
      }

      // Poll ML Task
      const mlPollInterval = setInterval(async () => {
        try {
          const statusRes = await storeApi.get(`/api/task-status/${task_id}`);
          const { state, status, progress, result } = statusRes.data;

          if (state === "PROGRESS" || state === "STARTED") {
            set({ 
              mlProgress: progress || get().mlProgress, 
              mlStatus: status || "Training ML Models..." 
            });
          } else if (state === "SUCCESS") {
            clearInterval(mlPollInterval);
            set({ mlResult: result, mlLoading: false, mlProgress: 100, mlStatus: "Completed" });
          } else if (state === "FAILURE" || state === "REVOKED") {
            clearInterval(mlPollInterval);
            set({ mlLoading: false, mlStatus: "ML Training failed." });
          }
        } catch (pollError) {
          console.error("Error polling ML task status:", pollError);
          clearInterval(mlPollInterval);
          set({ mlLoading: false });
        }
      }, 1000);

    } catch (error) {
      console.error("AutoML failed", error);
      set({ mlLoading: false });
    }
  },

  // ⏰ Scheduled Exports Actions
  getSchedules: async () => {
    try {
      const response = await storeApi.get("/api/schedule/my-schedules");
      set({ schedulesList: response.data.schedules || [] });
    } catch (error) {
      console.error("Failed to fetch schedules", error);
    }
  },

  createSchedule: async (schedulePayload) => {
    try {
      await storeApi.post("/api/schedule/create", schedulePayload);
      get().getSchedules(); // Refresh the list
    } catch (error) {
      console.error("Failed to create schedule", error);
    }
  },

  deleteSchedule: async (scheduleId) => {
    try {
      await storeApi.delete(`/api/schedule/${scheduleId}`);
      get().getSchedules(); // Refresh the list
    } catch (error) {
      console.error("Failed to delete schedule", error);
    }
  },

  // Forecast state tracking
  forecastResult: null,
  setForecastResult: (result) => set({ forecastResult: result }),

  resetStore: () => set({
    rawData: [],
    cleanedData: [],
    columns: [],
    isLoading: false,
    progress: 0,
    healthScore: null,
    aiInsights: "",
    fileObject: null,
    analysis: null,
    domainData: null,
    qualityReport: null,
    mlResult: null,
    mlLoading: false,
    mlProgress: 0,
    mlStatus: "",
    schedulesList: [],
    forecastResult: null,
  })
  }),
  {
    name: 'my-data-platform-store',
    storage: createJSONStorage(() => sessionStorage),
    partialize: (state) => {
      const { fileObject, ...rest } = state;
      return rest;
    }
  }
));

export default useDataStore;
