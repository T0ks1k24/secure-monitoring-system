import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { createBaseQueryWithRefresh } from "./auth/baseQueryWithRefresh";

const FRAME_API_BASE = (
  import.meta.env.VITE_FRAME_API_URL || "http://localhost:8100"
).replace(/\/+$/, "");

export const camerasApi = createApi({
  reducerPath: "camerasApi",
  baseQuery: createBaseQueryWithRefresh(`${FRAME_API_BASE}/api/v1`),
  tagTypes: ["Camera"],
  endpoints: (builder) => ({
    getCameras: builder.query({
      query: () => "/cameras",
      providesTags: ["Camera"],
      pollingInterval: 5000, 
    }),
    addCamera: builder.mutation({
      query: (body) => ({ url: "/cameras", method: "POST", body }),
      invalidatesTags: ["Camera"],
    }),
    updateCamera: builder.mutation({
      query: ({ id, ...patch }) => ({ url: `/cameras/${id}`, method: "PATCH", body: patch }),
      invalidatesTags: ["Camera"],
    }),
    deleteCamera: builder.mutation({
      query: (id) => ({ url: `/cameras/${id}`, method: "DELETE" }),
      invalidatesTags: ["Camera"],
    }),
    startCamera: builder.mutation({
      query: (id) => ({ url: `/cameras/${id}/start`, method: "POST" }),
      invalidatesTags: ["Camera"],
    }),
    stopCamera: builder.mutation({
      query: (id) => ({ url: `/cameras/${id}/stop`, method: "POST" }),
      invalidatesTags: ["Camera"],
    }),
  }),
});

export const {
  useGetCamerasQuery,
  useAddCameraMutation,
  useUpdateCameraMutation,
  useDeleteCameraMutation,
  useStartCameraMutation,
  useStopCameraMutation,
} = camerasApi;
