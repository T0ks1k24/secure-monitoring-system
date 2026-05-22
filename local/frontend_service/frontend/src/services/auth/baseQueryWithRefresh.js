import { fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { logOut, setCredentials } from "./authSlice.js";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const createBaseQueryWithRefresh = (baseUrl) => {
    const rawBaseQuery = fetchBaseQuery({
        baseUrl,
        prepareHeaders: (headers, { getState }) => {
            const token = getState().auth?.accessToken || localStorage.getItem("accessToken");
            if (token) headers.set("Authorization", `Bearer ${token}`);
            return headers;
        },
    });

    return async (args, api, extraOptions) => {
        let result = await rawBaseQuery(args, api, extraOptions);

        if (result?.error?.status === 401) {
            const refreshToken = localStorage.getItem("refreshToken");
            if (refreshToken) {
                const refreshResult = await rawBaseQuery(
                    { url: `${API_URL}/auth/refresh`, method: "POST", body: { refresh_token: refreshToken } },
                    api,
                    extraOptions
                );
                if (refreshResult?.data?.access_token) {
                    api.dispatch(setCredentials({
                        access_token: refreshResult.data.access_token,
                        refresh_token: refreshToken,
                    }));
                    result = await rawBaseQuery(args, api, extraOptions);
                } else {
                    api.dispatch(logOut());
                }
            } else {
                api.dispatch(logOut());
            }
        }
        return result;
    };
};