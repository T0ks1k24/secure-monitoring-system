import { useState } from "react";
import {
    useCreateUserMutation,
    useResetPasswordMutation,
    useGetUsersQuery,
} from "../../../services/auth/authApi";
import "./AccessControl.scss";

const ROLE_OPTIONS = [
    { value: "ADMIN",    label: "Admin",    desc: "Full system access"    },
    { value: "OPERATOR", label: "Operator", desc: "View and monitor only" },
];

const ROLE_BADGE = {
    ADMIN:    { bg: "rgba(37,99,235,0.15)",  color: "#60a5fa"  },
    OPERATOR: { bg: "rgba(34,197,94,0.15)",  color: "#4ade80"  },
};

function UserRow({ user, onResetSuccess }) {
    const [resetPassword] = useResetPasswordMutation();
    const [open, setOpen] = useState(false);
    const [newPwd, setNewPwd] = useState("");
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(false);
    const [showPwd, setShowPwd] = useState(false);

    const badge = ROLE_BADGE[user.role] || ROLE_BADGE.OPERATOR;

    const handleReset = async () => {
        if (!newPwd || newPwd.length < 6) {
            setStatus({ type: "error", msg: "Minimum 6 characters." });
            return;
        }
        setLoading(true);
        setStatus(null);
        try {
            await resetPassword({ user_id: user.id, new_password: newPwd }).unwrap();
            setStatus({ type: "success", msg: "Password updated." });
            setNewPwd("");
            setTimeout(() => { setOpen(false); setStatus(null); }, 1500);
        } catch (err) {
            setStatus({ type: "error", msg: err?.data?.detail || "Failed." });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={`user-row ${open ? "expanded" : ""}`}>
            <div className="user-row-main">
                <div className="user-row-info">
                    <div className="user-avatar">
                        {user.username[0].toUpperCase()}
                    </div>
                    <div>
                        <div className="user-username">{user.username}</div>
                        <div className="user-meta">
                            <span className="user-id-text">ID: {user.id.slice(0, 8)}…</span>
                            <span className="user-created">
                                {new Date(user.created_at).toLocaleDateString("uk-UA")}
                            </span>
                        </div>
                    </div>
                </div>
                <div className="user-row-right">
                    <span className="user-role-badge" style={{ background: badge.bg, color: badge.color }}>
                        {user.role}
                    </span>
                    <button
                        className="user-reset-btn"
                        onClick={() => { setOpen(p => !p); setStatus(null); setNewPwd(""); }}
                    >
                        {open ? "Cancel" : "Reset password"}
                    </button>
                </div>
            </div>

            {open && (
                <div className="user-reset-inline">
                    <div className="user-reset-full-id">
                        <span className="user-reset-id-label">User ID</span>
                        <code className="user-reset-id-value">{user.id}</code>
                    </div>
                    <div className="user-reset-form">
                        <div className="pwd-input-wrap">
                            <input
                                type={showPwd ? "text" : "password"}
                                placeholder="New password (min 6 chars)"
                                value={newPwd}
                                onChange={e => setNewPwd(e.target.value)}
                                onKeyDown={e => e.key === "Enter" && handleReset()}
                            />
                            <button
                                type="button"
                                className="pwd-toggle"
                                onClick={() => setShowPwd(p => !p)}
                                tabIndex={-1}
                            >
                                {showPwd ? (
                                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                                        <path d="M13.36 4.64a8.28 8.28 0 0 0-10.72 0A8.1 8.1 0 0 0 .5 8a8.1 8.1 0 0 0 2.14 3.36 8.28 8.28 0 0 0 10.72 0A8.1 8.1 0 0 0 15.5 8a8.1 8.1 0 0 0-2.14-3.36zM8 11.5A3.5 3.5 0 1 1 8 4.5a3.5 3.5 0 0 1 0 7zm0-5.5a2 2 0 1 0 0 4 2 2 0 0 0 0-4z" />
                                    </svg>
                                ) : (
                                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                                        <path d="M2.22 2.22a.75.75 0 0 0-1.06 1.06l1.5 1.5A8.12 8.12 0 0 0 .5 8a8.1 8.1 0 0 0 2.14 3.36 8.28 8.28 0 0 0 10.72 0l1.42 1.42a.75.75 0 1 0 1.06-1.06L2.22 2.22zm10 7.5-.02.02A3.5 3.5 0 0 1 7.3 5.4L5.9 4A6.77 6.77 0 0 1 8 3.6c2.42 0 4.52 1.37 5.86 3.36-.5.76-1.14 1.44-1.86 1.96l.22.22zM8 11.5c-.67 0-1.32-.13-1.92-.36l-1.1-1.1A3.5 3.5 0 0 0 9.96 6.14l-1.1-1.1c-.27-.06-.56-.04-.86-.04a3.5 3.5 0 0 0-3.5 3.5c0 .3.04.59.1.86l-1.04-1.04A6.5 6.5 0 0 0 2.14 8C3.48 10 5.58 11.5 8 11.5z" />
                                    </svg>
                                )}
                            </button>
                        </div>
                        <button className="user-reset-confirm" onClick={handleReset} disabled={loading}>
                            {loading ? <span className="ac-spinner" /> : "Confirm"}
                        </button>
                    </div>
                    {status && (
                        <div className={`ac-status ${status.type}`} style={{ marginTop: 8 }}>
                            {status.msg}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default function AccessControl() {
    const [createUser] = useCreateUserMutation();
    const { data: users = [], refetch } = useGetUsersQuery();

    const [createForm, setCreateForm] = useState({ username: "", password: "", role: "OPERATOR" });
    const [createStatus, setCreateStatus] = useState(null);
    const [createLoading, setCreateLoading] = useState(false);

    const handleCreate = async (e) => {
        e.preventDefault();
        if (!createForm.username || !createForm.password) return;
        setCreateLoading(true);
        setCreateStatus(null);
        try {
            const res = await createUser(createForm).unwrap();
            setCreateStatus({ type: "success", msg: `User "${res.username}" created.` });
            setCreateForm({ username: "", password: "", role: "OPERATOR" });
            refetch();
        } catch (err) {
            setCreateStatus({ type: "error", msg: err?.data?.detail || "Failed to create user." });
        } finally {
            setCreateLoading(false);
        }
    };

    return (
        <div className="tab-content access-control">
            <h2>Access Control</h2>
            <p className="tab-desc">
                Manage system users and access permissions. Only administrators can create users or reset passwords.
            </p>

            <div className="ac-top">
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
                            <input type="text" placeholder="e.g. operator_01"
                                value={createForm.username}
                                onChange={e => setCreateForm({ ...createForm, username: e.target.value })} />
                        </div>
                        <div className="ac-field">
                            <label>Password</label>
                            <input type="password" placeholder="Minimum 6 characters"
                                value={createForm.password}
                                onChange={e => setCreateForm({ ...createForm, password: e.target.value })} />
                        </div>
                        <div className="ac-field">
                            <label>Role</label>
                            <div className="role-selector">
                                {ROLE_OPTIONS.map(opt => (
                                    <button key={opt.value} type="button"
                                        className={`role-btn ${createForm.role === opt.value ? "active" : ""}`}
                                        onClick={() => setCreateForm({ ...createForm, role: opt.value })}>
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
            </div>

            {/* Users list */}
            <div className="users-section">
                <div className="users-section-header">
                    <h3>System users</h3>
                    <span className="users-count">{users.length} users</span>
                </div>
                <div className="users-list">
                    {users.length === 0 ? (
                        <div className="users-empty">No users found.</div>
                    ) : (
                        users.map(user => (
                            <UserRow key={user.id} user={user} />
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}