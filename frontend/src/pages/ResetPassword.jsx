import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Form, Input, Button, Typography, Alert, Result } from "antd";
import { LockOutlined } from "@ant-design/icons";
import { resetPassword } from "../api/auth";
import PasswordRequirements, { passwordValid } from "../components/PasswordRequirements";

const { Title, Text } = Typography;

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const pwValue = Form.useWatch("next", form);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const onFinish = async ({ next, confirm }) => {
    setError("");
    if (next !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setBusy(true);
    try {
      await resetPassword(token, next);
      setDone(true);
      setTimeout(() => navigate("/login"), 1800);
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not reset password");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="centered-page">
      <div className="login-card" style={{ maxWidth: 440 }}>
        {!token ? (
          <Result
            status="error"
            title="Invalid reset link"
            subTitle="This link is missing its token. Request a new one from the login page."
            extra={<Button type="primary" onClick={() => navigate("/forgot-password")}>Request new link</Button>}
          />
        ) : done ? (
          <Result status="success" title="Password updated" subTitle="Redirecting you to the login page…" />
        ) : (
          <>
            <Title level={3} style={{ marginBottom: 2 }}>Set a new password</Title>
            <Text type="secondary">Choose a new password for your account.</Text>
            <Form form={form} layout="vertical" onFinish={onFinish} requiredMark={false} style={{ marginTop: 24 }}>
              <Form.Item label="New password" name="next"
                rules={[
                  { required: true, message: "Enter a password" },
                  { validator: (_, v) => passwordValid(v) ? Promise.resolve() : Promise.reject(new Error("Password doesn't meet the requirements")) },
                ]}>
                <Input.Password size="large" prefix={<LockOutlined />} placeholder="Choose a strong password" autoFocus />
              </Form.Item>
              <PasswordRequirements value={pwValue} />
              <Form.Item label="Confirm password" name="confirm" style={{ marginTop: 12 }}
                rules={[{ required: true, message: "Re-enter your password" }]}>
                <Input.Password size="large" prefix={<LockOutlined />} />
              </Form.Item>
              {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />}
              <Button type="primary" htmlType="submit" size="large" block loading={busy}>
                Update password
              </Button>
            </Form>
          </>
        )}
      </div>
    </div>
  );
}
