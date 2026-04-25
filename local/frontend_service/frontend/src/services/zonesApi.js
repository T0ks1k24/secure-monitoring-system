import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { createBaseQueryWithRefresh } from './auth/baseQueryWithRefresh';

export const zonesApi = createApi({
    reducerPath: 'zonesApi',
    baseQuery: createBaseQueryWithRefresh(import.meta.env.VITE_API_URL || "http://localhost:8000"),
    tagTypes: ['Zones'],
    endpoints: (builder) => ({
        getZones: builder.query({
            query: (cameraId) => `zones/${cameraId}`,
            transformResponse: (response) => response.map(zone => ({
                id: zone.id,
                name: zone.name,
                zone_type: zone.zone_type,
                risk_weight: zone.risk_weight,
                max_people_allowed: zone.max_people_allowed,
                points: zone.polygon || [],
                base_mode: zone.base_mode,
                cooldown_seconds: zone.cooldown_seconds,
                risk_multipliers: zone.risk_multipliers,
                people_thresholds: zone.people_thresholds,
                accumulation: zone.accumulation,
                time_windows: zone.time_windows || [],
            })),
            providesTags: ['Zones'],
        }),

        addZone: builder.mutation({
            query: (payload) => ({
                url: 'zones/',
                method: 'POST',
                body: payload,
            }),
            invalidatesTags: ['Zones'],
        }),

        updateZone: builder.mutation({
            query: ({ id, ...payload }) => ({
                url: `zones/${id}`,
                method: 'PUT',
                body: payload,
            }),
            invalidatesTags: ['Zones'],
        }),

        deleteZone: builder.mutation({
            query: (id) => ({
                url: `zones/${id}`,
                method: 'DELETE',
            }),
            invalidatesTags: ['Zones'],
        }),
    }),
});

export const { 
    useGetZonesQuery, 
    useAddZoneMutation, 
    useUpdateZoneMutation, 
    useDeleteZoneMutation 
} = zonesApi;