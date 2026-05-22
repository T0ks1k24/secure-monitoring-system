import { configureStore } from '@reduxjs/toolkit';
import { zonesApi } from '../services/zonesApi';
import { camerasApi } from '../services/camerasApi';
import { authApi } from '../services/auth/authApi';
import authReducer from '../services/auth/authSlice';

export const store = configureStore({
    reducer: {
        auth: authReducer,
        [zonesApi.reducerPath]: zonesApi.reducer,
        [camerasApi.reducerPath]: camerasApi.reducer,
        [authApi.reducerPath]: authApi.reducer,
    },
    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware().concat(zonesApi.middleware, camerasApi.middleware, authApi.middleware),
});