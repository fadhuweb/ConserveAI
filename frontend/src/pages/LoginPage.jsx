import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Form, Input, Button, Typography, Alert } from "antd";
import { UserOutlined, LockOutlined, EyeOutlined, EyeInvisibleOutlined } from "@ant-design/icons";
import { useAuth } from "../auth/AuthContext";

const { Title, Text } = Typography;

// Beautiful multi-path topographic elevation contour SVG for the brand side panel
const ContourPattern = () => (
  <svg className="login-pattern" viewBox="0 0 800 800" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <path d="M-50 150 C 200 100, 250 350, 500 300 C 750 250, 800 550, 1050 500" stroke="rgba(255,255,255,0.06)" strokeWidth="2.5" />
    <path d="M-50 230 C 230 180, 280 430, 530 380 C 780 330, 830 630, 1050 580" stroke="rgba(255,255,255,0.08)" strokeWidth="3" />
    <path d="M-50 310 C 260 260, 310 510, 560 460 C 810 410, 860 710, 1050 660" stroke="rgba(255,255,255,0.12)" strokeWidth="3.5" />
    <path d="M-50 390 C 290 340, 340 590, 590 540 C 840 490, 890 790, 1050 740" stroke="rgba(255,255,255,0.08)" strokeWidth="2.5" />
    <path d="M-50 470 C 320 420, 370 670, 620 620 C 870 570, 920 870, 1050 820" stroke="rgba(255,255,255,0.05)" strokeWidth="1.5" />
    
    {/* Oval ridge detail representing a plateau/peak contour */}
    <path d="M 520 220 C 620 240, 660 320, 610 400 C 560 480, 460 440, 430 370 C 400 300, 440 200, 520 220 Z" stroke="rgba(255,255,255,0.08)" strokeWidth="2" />
    <path d="M 520 250 C 590 265, 620 320, 590 380 C 560 430, 485 400, 465 355 C 445 310, 465 235, 520 250 Z" stroke="rgba(255,255,255,0.10)" strokeWidth="1.5" />
  </svg>
);

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const onFinish = async ({ username, password }) => {
    setError("");
    setBusy(true);
    try {
      const user = await login(username, password);
      if (user.must_change_password) navigate("/change-password");
      else navigate(user.role === "admin" ? "/national" : `/park/${user.park_id}`);
    } catch (_) {
      setError("Invalid username or password");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-bg"><div className="login-page">
      <aside className="login-left">
        <ContourPattern />
        
        <div className="login-left-inner animate-fade-in-up">
          <div className="logo-container">
            <div className="logo">🛡</div>
            <span className="wordmark">ConserveAI</span>
          </div>
          {/* Distraction-free clean branding */}
        </div>
      </aside>

      <main className="login-right">
        <div className="login-card animate-fade-in-up delay-1">
          <Title level={2} style={{ margin: 0 }}>Welcome back</Title>
          <Text className="sub">Sign in to your park management account</Text>

          <Form 
            layout="vertical" 
            onFinish={onFinish} 
            requiredMark={false} 
            style={{ marginTop: 8 }}
          >
            <Form.Item 
              label={<span style={{ fontWeight: 600, fontSize: 13, color: "var(--muted)" }}>USERNAME</span>}
              name="username"
              rules={[{ required: true, message: "Enter your username" }]}
            >
              <Input 
                size="large" 
                prefix={<UserOutlined />} 
                placeholder="e.g. manager_yankari" 
                autoFocus 
              />
            </Form.Item>

            <Form.Item 
              label={<span style={{ fontWeight: 600, fontSize: 13, color: "var(--muted)" }}>PASSWORD</span>}
              name="password"
              rules={[{ required: true, message: "Enter your password" }]}
            >
              <Input.Password 
                size="large" 
                prefix={<LockOutlined />} 
                placeholder="Enter your password" 
                iconRender={visible => (visible ? <EyeOutlined /> : <EyeInvisibleOutlined />)}
              />
            </Form.Item>

            {error && (
              <Alert 
                type="error" 
                message={error} 
                showIcon 
                style={{ marginBottom: 20, borderRadius: 10 }} 
              />
            )}

            <Button 
              type="primary" 
              htmlType="submit" 
              size="large" 
              block 
              loading={busy}
              style={{ marginTop: 8 }}
            >
              Log in
            </Button>
            <div className="forgot-link" onClick={() => navigate('/forgot-password')}>Forgot password?</div>
          </Form>
        </div>
      </main>
    </div></div>
  );
}
