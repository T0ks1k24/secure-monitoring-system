import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  accessToken: localStorage.getItem("accessToken") || null,
  refreshToken: localStorage.getItem("refreshToken") || null,
  user: JSON.parse(localStorage.getItem("user") || "null"),
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setCredentials: (state, { payload }) => {
      const { access_token, refresh_token, user } = payload;
      state.accessToken = access_token;
      if (refresh_token) state.refreshToken = refresh_token;
      if (user) state.user = user;

      localStorage.setItem("accessToken", access_token);
      if (refresh_token) localStorage.setItem("refreshToken", refresh_token);
      if (user) localStorage.setItem("user", JSON.stringify(user));
    },
    logOut: (state) => {
      state.accessToken = null;
      state.refreshToken = null;
      state.user = null;
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      localStorage.removeItem("user");
    },
  },
});

export const { setCredentials, logOut } = authSlice.actions;
export default authSlice.reducer;