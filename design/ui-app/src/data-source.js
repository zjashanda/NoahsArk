// Route data source selector.
//
// Fixture mode is the default and stays synchronous.  API mode is opt-in via
// ?api=1 (or localStorage) and never falls back to fixtures: a failed request
// returns an explicit error so the UI can show retry / switch-to-fixture.

import { apiGet, endpointForRoute, isApiMode } from "./api.js";
import { view as fixtureView } from "./fixtures.js";

export async function loadRouteView(routeId, params = {}) {
  if (!isApiMode()) {
    return { mode: "fixture", view: fixtureView() };
  }

  const endpoint = endpointForRoute(routeId, params);
  if (!endpoint) {
    return {
      mode: "api",
      endpoint: null,
      error: {
        code: "NO_ENDPOINT",
        message: `No read endpoint is mapped for route ${routeId}`,
        retryable: false,
        status: 0
      }
    };
  }

  const result = await apiGet(endpoint);
  if (!result.ok) {
    return {
      mode: "api",
      endpoint,
      error: { ...result.error, status: result.status }
    };
  }

  return { mode: "api", endpoint, payload: result.payload };
}
