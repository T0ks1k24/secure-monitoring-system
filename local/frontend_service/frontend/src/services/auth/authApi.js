import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQueryWithRefresh } from "./baseQueryWithRefresh";

export const authApi = createApi({
  reducerPath: "authApi",
  baseQuery: baseQueryWithRefresh("/auth"),
  endpoints: (builder) => ({
    login: builder.mutation({
      query: (credentials) => ({
        url: "/login",
        method: "POST",
        body: credentials,
      }),
    }),
    createUser: builder.mutation({
      query: (userData) => ({
        url: "/users",
        method: "POST",
        body: userData,
      }),
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
  useCreateUserMutation, 
  useResetPasswordMutation 
} = authApi;