import client from "./client";

export const getParks = () => client.get("/parks").then((r) => r.data);

export const getPark = (id) => client.get(`/parks/${id}`).then((r) => r.data);

export const getZones = (id) => client.get(`/parks/${id}/zones`).then((r) => r.data);

export const getCatalog = () => client.get("/catalog").then((r) => r.data);

export const getForecasts = (park, days = 60, order = "asc") =>
  client.get(`/forecasts/${park}`, { params: { days, order } }).then((r) => r.data);

export const getLatestForecast = (park) =>
  client.get(`/forecasts/${park}/latest`).then((r) => r.data);

export const getNationalOverview = () =>
  client.get("/national-overview").then((r) => r.data);

export const getNationalTrend = (days = 60) =>
  client.get("/national-trend", { params: { days } }).then((r) => r.data);

export const getDrivers = (park) =>
  client.get(`/forecasts/${park}/drivers`).then((r) => r.data);
