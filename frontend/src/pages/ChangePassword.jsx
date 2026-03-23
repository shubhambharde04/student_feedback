import { useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api";

export default function ChangePassword() {
  const navigate = useNavigate();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  // Use the stored user information
  const userStr = localStorage.getItem("user");
  const user = userStr ? JSON.parse(userStr) : null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!oldPassword || !newPassword || !confirmPassword) {
      setError("Please fill in all fields.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }

    if (newPassword.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    setLoading(true);

    try {
      await API.post("/auth/change-password/", {
        old_password: oldPassword,
        new_password: newPassword,
      });
      
      setSuccess("Password changed successfully. Redirecting to dashboard...");
      
      // Update local user object
      if (user) {
        user.is_first_login = false;
        localStorage.setItem("user", JSON.stringify(user));
      }

      setTimeout(() => {
        if (user) {
          navigate(`/${user.role}-dashboard`);
        } else {
          navigate("/");
        }
      }, 2000);

    } catch (err) {
      setError(
        err.response?.data?.error ||
        err.response?.data?.detail ||
        err.message ||
        "Failed to change password. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-mesh flex items-center justify-center p-4 relative overflow-hidden">
      <div className="relative z-10 w-full max-w-md animate-fade-in glass-card p-8">
        
        <h2 className="text-2xl font-bold font-display text-surface-50 mb-2">Change Password Setup</h2>
        <p className="text-surface-400 text-sm mb-6">
          Since this is your first time logging in, you are required to change your password for security reasons.
        </p>

        {error && (
          <div className="mb-5 p-3 rounded-lg bg-accent-rose/10 border border-accent-rose/20 text-accent-rose text-sm font-medium">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-5 p-3 rounded-lg bg-accent-emerald/10 border border-accent-emerald/20 text-accent-emerald text-sm font-medium">
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-surface-300 mb-1">Current Password (Enrollment No.)</label>
            <input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              className="input-dark w-full"
              disabled={loading}
              placeholder="Enter current password"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-300 mb-1">New Password</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="input-dark w-full"
              disabled={loading}
              placeholder="Minimum 6 characters"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-300 mb-1">Confirm New Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="input-dark w-full"
              disabled={loading}
              placeholder="Confirm new password"
            />
          </div>

          <button
            type="submit"
            className="w-full btn-primary py-3 mt-4"
            disabled={loading}
          >
            {loading ? "Updating..." : "Update Password"}
          </button>
        </form>
      </div>
    </div>
  );
}
