import axios from "axios";

// Configuración base de la API
const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor para manejar errores
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error:", error);
    return Promise.reject(error);
  }
);

export const malwareAPI = {
  // Obtener todas las detecciones
  async getDetections(limit = 100) {
    try {
      const response = await api.get(`/detections?limit=${limit}`);
      return response.data;
    } catch (error) {
      throw new Error(`Error obteniendo detecciones: ${error.message}`);
    }
  },

  // Obtener una detección específica
  async getDetection(malwareId) {
    try {
      const response = await api.get(`/detections/${malwareId}`);
      return response.data;
    } catch (error) {
      throw new Error(`Error obteniendo detección: ${error.message}`);
    }
  },

  // Health check
  async getHealth() {
    try {
      const response = await api.get("/health");
      return response.data;
    } catch (error) {
      throw new Error(`Error en health check: ${error.message}`);
    }
  },

  // Iniciar demo
  async startDemo(pcapFile = "models/data/small/Malware/Zeus.pcap") {
    try {
      const response = await api.get("/demo/start");
      return response.data;
    } catch (error) {
      throw new Error(`Error iniciando demo: ${error.message}`);
    }
  },

  // Detener demo
  async stopDemo() {
    try {
      const response = await api.post("/demo/stop");
      return response.data;
    } catch (error) {
      throw new Error(`Error deteniendo demo: ${error.message}`);
    }
  },

  // Alternar demo
  async toggleDemo(pcapFile = "models/data/small/Malware/Zeus.pcap") {
    try {
      const response = await api.post("/demo/toggle", { pcap_file: pcapFile });
      return response.data;
    } catch (error) {
      throw new Error(`Error alternando demo: ${error.message}`);
    }
  },
};

export default api;
