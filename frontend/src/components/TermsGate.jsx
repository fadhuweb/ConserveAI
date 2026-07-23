import { useState } from "react";
import { Modal, Checkbox, Button, Typography, message } from "antd";
import { FileProtectOutlined } from "@ant-design/icons";
import { useAuth } from "../auth/AuthContext";

const { Paragraph, Link } = Typography;

// One-time Terms of Use / Privacy Policy acceptance shown on first login.
// Acceptance is recorded server-side against the user account (terms_accepted_at),
// so it is auditable and persists across devices and browsers. The gate appears
// only when the account has an explicit not-accepted status. This implements EULA
// clause 1 ("by accessing... you agree") at the first-login gate.
export default function TermsGate() {
  const { user, acceptTerms } = useAuth();
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);

  // Show only once we know the account has NOT accepted. While the status is
  // still loading (undefined right after login) we show nothing, avoiding a flash.
  if (!user || user.terms_accepted !== false) return null;

  const agree = async () => {
    setBusy(true);
    try {
      await acceptTerms();
    } catch (_) {
      message.error("Could not record your acceptance. Please try again.");
      setBusy(false);
    }
  };

  return (
    <Modal
      open
      closable={false}
      maskClosable={false}
      keyboard={false}
      title={<span><FileProtectOutlined style={{ color: "#10b981", marginRight: 8 }} />Terms of Use and Privacy Policy</span>}
      footer={[
        <Button key="view" onClick={() => window.open("/legal", "_blank")}>
          Read full terms
        </Button>,
        <Button key="agree" type="primary" disabled={!checked} loading={busy} onClick={agree}>
          Continue
        </Button>,
      ]}
    >
      <Paragraph type="secondary">
        ConserveAI's forecasts and budget recommendations are advisory decision support, not
        instructions to act: you remain responsible for every operational decision, and accuracy
        varies by park and by threat. The system stores only your account details (username,
        hashed password, and email) and collects no data about individuals or communities.
      </Paragraph>
      <Paragraph style={{ marginBottom: 12 }}>
        <Link onClick={() => window.open("/legal", "_blank")}>
          Read the full Terms of Use and Privacy Policy
        </Link>
      </Paragraph>
      <Checkbox checked={checked} onChange={(e) => setChecked(e.target.checked)}>
        I have read and agree to the Terms of Use and Privacy Policy.
      </Checkbox>
    </Modal>
  );
}
