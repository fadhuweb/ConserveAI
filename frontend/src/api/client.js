import axios from "axios";

// Shared axios instance. withCredentials sends/receives the httpOnly auth cookie.
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  withCredentials: true,
});

// If the session cookie is missing/expired, the API returns 401. Clear the stale
// stored user and send the person to login — except on a login attempt itself
// (there a 401 just means wrong credentials, handled by the form).
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const url = error?.config?.url || "";
    if (status === 401 && !url.includes("/auth/login")) {
      localStorage.removeItem("conserveai_user");
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default client;
