import { useSelector } from "react-redux";

export function useRole() {
    const user = useSelector(state => state.auth?.user);
    const role = user?.role || null;
    return {
        role,
        isAdmin: role === "ADMIN",
        isOperator: role === "OPERATOR",
        isAuthenticated: !!role,
    };
}