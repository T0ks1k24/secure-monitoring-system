import { useState } from "react";
import { useCreateUserMutation, useResetPasswordMutation } from "../../services/auth/authApi";

const ROLE_OPTIONS = [
    { value: "ADMIN", label: "Admin", desc: "Full system access" },
    { value: "OPERATOR", label: "Operator", desc: "View and monitor only" },
];

export default function AccessControl() {
    const [createUser] = useCreateUserMutation();
    const [resetPassword] = useResetPasswordMutation();

    const [createForm, setCreateForm] = useState({ username: "", password: "", role: "OPERATOR" });
    const [createStatus, setCreateStatus] = useState(null);
    const [createLoading, setCreateLoading] = useState(false);

    const [resetForm, setResetForm] = useState({ user_id: "", new_password: "" });
    const [resetStatus, setResetStatus] = useState(null);
    const [resetLoading, setResetLoading] = useState(false);

    const handleCreate = async (e) => {
        e.preventDefault();
        if (!createForm.username || !createForm.password) return;
        setCreateLoading(true);
        setCreateStatus(null);
        try {
            const res = await createUser(createForm).unwrap();
            setCreateStatus({ type: "success", msg: `User "${res.username}" created with role ${res.role}.` });
            setCreateForm({ username: "", password: "", role: "OPERATOR" });
        } catch (err) {
            setCreateStatus({ type: "error", msg: err?.data?.detail || "Failed to create user." });
        } finally {
            setCreateLoading(false);
        }
    };

    const handleReset = async (e) => {
        e.preventDefault();
        if (!resetForm.user_id || !resetForm.new_password) return;
        setResetLoading(true);
        setResetStatus(null);
        try {
            await resetPassword(resetForm).unwrap();
            setResetStatus({ type: "success", msg: "Password updated successfully." });
            setResetForm({ user_id: "", new_password: "" });
        } catch (err) {
            setResetStatus({ type: "error", msg: err?.data?.detail || "Failed to reset password." });
        } finally {
            setResetLoading(false);
        }
    };

    return (
        <div className="tab-content access-control">
            <h2>Access Control</h2>
            <p className="tab-desc">Manage system users and access permissions. Only administrators can create users or reset passwords.</p>

            <div className="ac-grid">
                {/* Create user */}
                <div className="ac-card">
                    <div className="ac-card-header">
                        <div className="ac-card-icon create">
                            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm2 1H6a4 4 0 0 0-4 4h12a4 4 0 0 0-4-4z"/>
                                <path d="M13.5 5.5v2m-1-1h2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                            </svg>
                        </div>
                        <div>
                            <h3>Create user</h3>
                            <p>Add a new operator or administrator</p>
                        </div>
                    </div>

                    <form onSubmit={handleCreate} className="ac-form">
                        <div className="ac-field">
                            <label>Username</label>
                            <input
                                type="text"
                                placeholder="e.g. operator_01"
                                value={createForm.username}
                                onChange={e => setCreateForm({ ...createForm, username: e.target.value })}
                            />
                        </div>
                        <div className="ac-field">
                            <label>Password</label>
                            <input
                                type="password"
                                placeholder="Minimum 6 characters"
                                value={createForm.password}
                                onChange={e => setCreateForm({ ...createForm, password: e.target.value })}
                            />
                        </div>
                        <div className="ac-field">
                            <label>Role</label>
                            <div className="role-selector">
                                {ROLE_OPTIONS.map(opt => (
                                    <button
                                        key={opt.value}
                                        type="button"
                                        className={`role-btn ${createForm.role === opt.value ? "active" : ""}`}
                                        onClick={() => setCreateForm({ ...createForm, role: opt.value })}
                                    >
                                        <span className="role-label">{opt.label}</span>
                                        <span className="role-desc">{opt.desc}</span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {createStatus && (
                            <div className={`ac-status ${createStatus.type}`}>{createStatus.msg}</div>
                        )}

                        <button type="submit" className="ac-submit" disabled={createLoading}>
                            {createLoading ? <span className="ac-spinner" /> : "Create user"}
                        </button>
                    </form>
                </div>

                {/* Reset password */}
                <div className="ac-card">
                    <div className="ac-card-header">
                        <div className="ac-card-icon reset">
                            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M8 1a4 4 0 0 1 4 4v1h1a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h1V5a4 4 0 0 1 4-4zm0 1.5A2.5 2.5 0 0 0 5.5 5v1h5V5A2.5 2.5 0 0 0 8 2.5z"/>
                            </svg>
                        </div>
                        <div>
                            <h3>Reset password</h3>
                            <p>Set a new password for an existing user</p>
                        </div>
                    </div>

                    <form onSubmit={handleReset} className="ac-form">
                        <div className="ac-field">
                            <label>User ID</label>
                            <input
                                type="text"
                                placeholder="Enter user UUID"
                                value={resetForm.user_id}
                                onChange={e => setResetForm({ ...resetForm, user_id: e.target.value })}
                            />
                            <span className="ac-hint">You can find the user ID after creating the user.</span>
                        </div>
                        <div className="ac-field">
                            <label>New password</label>
                            <input
                                type="password"
                                placeholder="Minimum 6 characters"
                                value={resetForm.new_password}
                                onChange={e => setResetForm({ ...resetForm, new_password: e.target.value })}
                            />
                        </div>

                        {resetStatus && (
                            <div className={`ac-status ${resetStatus.type}`}>{resetStatus.msg}</div>
                        )}

                        <button type="submit" className="ac-submit" disabled={resetLoading}>
                            {resetLoading ? <span className="ac-spinner" /> : "Reset password"}
                        </button>
                    </form>

                    <div className="ac-users-placeholder">
                        <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor" opacity="0.3">
                            <path d="M3 14s-1 0-1-1 1-4 6-4 6 3 6 4-1 1-1 1H3zm5-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/>
                        </svg>
                        <span>User list will appear here once the API endpoint is available</span>
                    </div>
                </div>
            </div>
        </div>
    );
}