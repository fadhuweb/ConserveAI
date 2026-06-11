import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Form, Input, Button, Typography, Alert } from "antd";
import { LockOutlined } from "@ant-design/icons";
import { useAuth } from "../auth/AuthContext";
import * as authApi from "../api/auth";
import PasswordRequirements, { passwordValid } from "../components/PasswordRequirements";

const { Title, Text } = Typography;

export default function ChangePassword() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const pwValue = Form.useWatch("next", form);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const onFinish = async ({ current, next }) => {
    setError("");
    setBusy(true);
    try {
      await authApi.changePassword(current, next);
      // Backend clears the cookie and requires a fresh login with the new password.
      setDone(true);
      await logout();
      setTimeout(() => navigate("/login"), 1500);
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not change password");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="centered-page">
      <div className="login-card">
        {done ? (
          <>
            <Title level={3} style={{ marginBottom: 2 }}>Password changed</Title>
            <Text type="secondary">Please log in again with your new password…</Text>
          </>
        ) : (
          <>
            <Title level={3} style={{ marginBottom: 2 }}>Set your password</Title>
            <Text type="secondary">
              <b>{user?.username}</b> — you must set a new password on first login.
            </Text>
            <Form form={form} layout="vertical" onFinish={onFinish} requiredMark={false} style={{ marginTop: 24 }}>
              <Form.Item label="Current (temporary) password" name="current"
                rules={[{ required: true, message: "Enter your current password" }]}>
                <Input.Password size="large" prefix={<LockOutlined />} autoFocus />
              </Form.Item>
              <Form.Item label="New password" name="next"
                rules={[
                  { required: true, message: "Enter a password" },
                  { validator: (_, v) => passwordValid(v) ? Promise.resolve() : Promise.reject(new Error("Password doesn't meet the requirements")) },
                ]}>
                <Input.Password size="large" prefix={<LockOutlined />} placeholder="Choose a strong password" />
              </Form.Item>
              <PasswordRequirements value={pwValue} />
              {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />}
              <Button type="primary" htmlType="submit" size="large" block loading={busy}>
                Change password
              </Button>
            </Form>
          </>
        )}
      </div>
    </div>
  );
}
