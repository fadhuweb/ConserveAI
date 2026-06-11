import client from "./client";

export const login = (username, password) =>
  client.post("/auth/login", { username, password }).then((r) => r.data);

export const logout = () =>
  client.post("/auth/logout").then((r) => r.data);

export const changePassword = (current_password, new_password) =>
  client.post("/auth/change-password", { current_password, new_password }).then((r) => r.data);

export const forgotPassword = (username) =>
  client.post("/auth/forgot-password", { username }).then((r) => r.data);

export const resetPassword = (token, new_password) =>
  client.post("/auth/reset-password", { token, new_password }).then((r) => r.data);

export const createUser = (payload) =>
  client.post("/auth/users", payload).then((r) => r.data);
