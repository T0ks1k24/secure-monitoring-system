import { configureStore } from '@reduxjs/toolkit';
import { zonesApi } from '../services/zonesApi';
import { camerasApi } from '../services/camerasApi';

export const store = configureStore({
    reducer: {
        [zonesApi.reducerPath]: zonesApi.reducer,
        [camerasApi.reducerPath]: camerasApi.reducer,
    },

    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware().concat(zonesApi.middleware, camerasApi.middleware),
});