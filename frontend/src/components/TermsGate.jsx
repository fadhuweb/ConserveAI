import { useState } from "react";
import { Modal, Checkbox, Button, Typography } from "antd";
import { FileProtectOutlined } from "@ant-design/icons";

const { Paragraph, Link } = Typography;

// One-time Terms of Use / Privacy Policy acceptance shown on first login.
// Acceptance is remembered per username in localStorage, so a returning user
// is not asked again. This implements EULA clause 1 ("by accessing... you agree")
// at the first-login gate. Acceptance is stored client-side only, which is a
// deliberate limitation for a proof-of-concept.
const keyFor = (username) => `conserveai_terms_accepted_${username || "guest"}`;

export default function TermsGate({ username }) {
  const [accepted, setAccepted] = useState(() => localStorage.getItem(keyFor(username)) === "1");
  const [checked, setChecked] = useState(false);

  if (accepted) return null;

  const agree = () => {
    localStorage.setItem(keyFor(username), "1");
    setAccepted(true);
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
        <Button key="agree" type="primary" disabled={!checked} onClick={agree}>
          Continue
        </Button>,
      ]}
    >
      <Paragraph type="secondary">
        ConserveAI is a research prototype. Its forecasts and budget recommendations are
        advisory decision support, not instructions to act: you remain responsible for every
        operational decision, and accuracy varies by park and by threat. The system stores only
        your account details (username, hashed password, and email) and collects no data about
        individuals or communities.
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
