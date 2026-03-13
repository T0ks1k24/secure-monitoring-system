import { configureStore } from '@reduxjs/toolkit';
import { zonesApi } from '../services/zonesApi';

export const store = configureStore({
    reducer: {
        [zonesApi.reducerPath]: zonesApi.reducer,
    },

    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware().concat(zonesApi.middleware),
});