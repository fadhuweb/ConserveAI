import axios from "axios";

// Shared axios instance. withCredentials sends/receives the httpOnly auth cookie.
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  withCredentials: true,
});

export default client;
