import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Form, Input, Button, Typography, Alert, Result } from "antd";
import { UserOutlined } from "@ant-design/icons";
import { forgotPassword } from "../api/auth";

const { Title, Text } = Typography;

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const onFinish = async ({ username }) => {
    setBusy(true);
    try {
      await forgotPassword(username);
    } catch (_) {
      /* endpoint always returns generic success; ignore errors */
    } finally {
      setBusy(false);
      setDone(true);   // always show the same confirmation (don't reveal if the account exists)
    }
  };

  return (
    <div className="centered-page">
      <div className="login-card" style={{ maxWidth: 440 }}>
        {done ? (
          <Result
            status="success"
            title="Check your email"
            subTitle="If that account exists, a reset link has been emailed to it. Open the link to set a new password (it expires in 30 minutes)."
            extra={<Button type="primary" onClick={() => navigate("/login")}>Back to login</Button>}
          />
        ) : (
          <>
            <Title level={3} style={{ marginBottom: 2 }}>Reset your password</Title>
            <Text type="secondary">
              Enter your username and we'll email a secure reset link to the address on file.
            </Text>
            <Form layout="vertical" onFinish={onFinish} requiredMark={false} style={{ marginTop: 24 }}>
              <Form.Item label="Username" name="username"
                rules={[{ required: true, message: "Enter your username" }]}>
                <Input size="large" prefix={<UserOutlined />} placeholder="e.g. manager_yankari" autoFocus />
              </Form.Item>
              <Button type="primary" htmlType="submit" size="large" block loading={busy}>
                Email me a reset link
              </Button>
              <div className="forgot-link" onClick={() => navigate("/login")}>Back to login</div>
            </Form>
          </>
        )}
      </div>
    </div>
  );
}
