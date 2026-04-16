import { useState } from "react";
import { useDispatch } from "react-redux";
import { useLoginMutation } from "../../services/auth/authApi";
import { setCredentials } from "../../services/auth/authSlice";
import "./Login.scss";

export default function Login() {
    const dispatch = useDispatch();
    const [login] = useLoginMutation();

    const [form, setForm] = useState({ username: "", password: "" });
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!form.username || !form.password) {
            setError("Enter username and password.");
            return;
        }
        setLoading(true);
        setError("");
        try {
            const data = await login(form).unwrap();
            dispatch(setCredentials({
                access_token: data.access_token,
                refresh_token: data.refresh_token,
            }));
        } catch {
            setError("Invalid credentials. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-page">
            <div className="login-card">
                <div className="login-logo">
                    <div className="login-logo-icon">
                        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                            <rect width="32" height="32" rx="8" fill="#2563eb"/>
                            <path d="M16 6L6 11v6c0 5 4.4 9.7 10 11 5.6-1.3 10-6 10-11v-6L16 6z" fill="white" opacity="0.9"/>
                            <path d="M13 16l2 2 4-4" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                    </div>
                    <div>
                        <h1>Security System</h1>
                        <p>Monitoring & Access Control</p>
                    </div>
                </div>

                <div className="login-divider" />

                <form onSubmit={handleSubmit} className="login-form">
                    <h2>Sign in</h2>
                    <p className="login-subtitle">Enter your credentials to access the system</p>

                    <div className="login-field">
                        <label>Username</label>
                        <div className="login-input-wrap">
                            <svg className="input-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm-5 6s-1 0-1-1 1-4 6-4 6 3 6 4-1 1-1 1H3z"/>
                            </svg>
                            <input
                                type="text"
                                placeholder="Enter username"
                                value={form.username}
                                onChange={e => setForm({ ...form, username: e.target.value })}
                                autoComplete="username"
                                autoFocus
                            />
                        </div>
                    </div>

                    <div className="login-field">
                        <label>Password</label>
                        <div className="login-input-wrap">
                            <svg className="input-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M8 1a4 4 0 0 1 4 4v1h1a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h1V5a4 4 0 0 1 4-4zm0 1.5A2.5 2.5 0 0 0 5.5 5v1h5V5A2.5 2.5 0 0 0 8 2.5z"/>
                            </svg>
                            <input
                                type="password"
                                placeholder="Enter password"
                                value={form.password}
                                onChange={e => setForm({ ...form, password: e.target.value })}
                                autoComplete="current-password"
                            />
                        </div>
                    </div>

                    {error && (
                        <div className="login-error">
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zm-.75 4h1.5v4h-1.5V5zm0 5h1.5v1.5h-1.5V10z"/>
                            </svg>
                            {error}
                        </div>
                    )}

                    <button type="submit" className="login-btn" disabled={loading}>
                        {loading ? (
                            <span className="login-spinner" />
                        ) : (
                            "Sign in"
                        )}
                    </button>
                </form>

                <div className="login-footer">
                    <span>Access restricted to authorized personnel only</span>
                </div>
            </div>
        </div>
    );
}