import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

export const zonesApi = createApi({
    reducerPath: 'zonesApi',
    baseQuery: fetchBaseQuery({ baseUrl: 'http://127.0.0.1:8000/' }),
    tagTypes: ['Zones'],
    endpoints: (builder) => ({
        getZones: builder.query({
            query: (cameraId) => `zones/${cameraId}`,
            transformResponse: (response) => response.map(zone => ({
                id: zone.id,
                name: zone.name,
                type: zone.zone_type,
                risk_weight: zone.risk_weight,
                max_people_allowed: zone.max_people_allowed,
                points: zone.polygon || []
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