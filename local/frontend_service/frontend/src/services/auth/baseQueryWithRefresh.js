import { fetchBaseQuery } from "@reduxjs/toolkit/query/react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const baseQueryWithRefresh = (endpointPrefix = "") => {
  const rawBaseQuery = fetchBaseQuery({
    baseUrl: API_URL,
    prepareHeaders: (headers, { getState }) => {
      const token = getState().auth?.accessToken || localStorage.getItem("accessToken");
      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }
      return headers;
    },
  });

  return async (args, api, extraOptions) => {
    let modifiedArgs = args;
    if (typeof args === "string") {
      modifiedArgs = endpointPrefix + args;
    } else if (typeof args === "object") {
      modifiedArgs = { ...args, url: endpointPrefix + args.url };
    }

    let result = await rawBaseQuery(modifiedArgs, api, extraOptions);
    if (result?.error?.status === 401) {
      const refreshToken = localStorage.getItem("refreshToken");
      
      if (refreshToken) {
        const refreshResult = await rawBaseQuery(
          {
            url: "/auth/refresh",
            method: "POST",
            body: { refresh_token: refreshToken },
          },
          api,
          extraOptions
        );

        if (refreshResult?.data?.access_token) {
          const newAccessToken = refreshResult.data.access_token;
          api.dispatch({ 
            type: 'auth/setCredentials', 
            payload: { access_token: newAccessToken, refresh_token: refreshToken } 
          });
          result = await rawBaseQuery(modifiedArgs, api, extraOptions);
        } else {
          api.dispatch({ type: 'auth/logOut' });
        }
      }
    }

    return result;
  };
};