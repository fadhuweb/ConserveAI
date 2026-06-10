import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider } from "antd";
import { AuthProvider } from "./auth/AuthContext";
import App from "./App";
import "./index.css";

const theme = {
  token: {
    colorPrimary: "#1d6b4f",
    borderRadius: 8,
    fontFamily: "Inter, 'Segoe UI', Roboto, system-ui, sans-serif",
  },
};

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ConfigProvider theme={theme}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>
);
