import { createApi } from "@reduxjs/toolkit/query/react";
import { createBaseQueryWithRefresh } from "./baseQueryWithRefresh";

export const authApi = createApi({
    reducerPath: "authApi",
    baseQuery: createBaseQueryWithRefresh(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/auth`),
    tagTypes: ["Users"],
    endpoints: (builder) => ({
        login: builder.mutation({
            query: (credentials) => ({
                url: "/login",
                method: "POST",
                body: credentials,
            }),
        }),
        getUsers: builder.query({
            query: () => "/users",
            providesTags: ["Users"],
        }),
        getUserById: builder.query({
            query: (id) => `/users/${id}`,
        }),
        createUser: builder.mutation({
            query: (userData) => ({
                url: "/users",
                method: "POST",
                body: userData,
            }),
            invalidatesTags: ["Users"],
        }),
        resetPassword: builder.mutation({
            query: (data) => ({
                url: "/reset-password",
                method: "POST",
                body: data,
            }),
        }),
    }),
});

export const {
    useLoginMutation,
    useGetUsersQuery,
    useGetUserByIdQuery,
    useCreateUserMutation,
    useResetPasswordMutation,
} = authApi;