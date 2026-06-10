import client from "./client";

export const recommend = (payload) =>
  client.post("/recommend", payload).then((r) => r.data);

export const sensitivity = (payload) =>
  client.post("/sensitivity", payload).then((r) => r.data);

export const getRecommendations = (park) =>
  client.get(`/recommendations/${park}`).then((r) => r.data);
