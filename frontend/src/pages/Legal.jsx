import { useNavigate } from "react-router-dom";
import { Typography, Button } from "antd";
import { ArrowLeftOutlined, SafetyCertificateFilled } from "@ant-design/icons";
import AppShell from "../components/AppShell";
import { useAuth } from "../auth/AuthContext";

const { Title, Paragraph, Text } = Typography;

// End-User Licence Agreement and Privacy Policy for ConserveAI.
// The wording matches the project's Research Ethics submission so the deployed
// app carries the same terms the ethics application refers to.

const EULA_INTRO =
  "By accessing ConserveAI you agree to the terms below. ConserveAI is a research " +
  "prototype developed as an undergraduate Capstone project at the African Leadership University.";

const EULA = [
  ["1. Licence granted",
    "You are granted a non-exclusive, non-transferable, revocable licence to access " +
    "ConserveAI for conservation planning and evaluation purposes. The licence does not " +
    "transfer ownership of the software, the trained models, or the underlying source code."],
  ["2. Absence of warranty",
    "ConserveAI has been evaluated against historical satellite and climate records across " +
    "six Nigerian national parks. The software is provided as is, without warranty of " +
    "accuracy, fitness for a particular purpose, or uninterrupted availability. Forecast " +
    "performance varies by park and by threat: drought precision is 0.70, the weakest of the " +
    "three threats, and mean F2 falls from 0.96 in Sahel conditions to 0.77 in rainforest " +
    "conditions."],
  ["3. Decision support, not instruction",
    "Forecasts and budget recommendations produced by ConserveAI are advisory. They do not " +
    "constitute an instruction to act and do not replace the judgement of park management. " +
    "You remain responsible for every operational decision taken. A drought flag should be " +
    "treated as a prompt to verify against local knowledge rather than a direction to deploy " +
    "resources. Where the system displays the factors driving a forecast, you are expected to " +
    "inspect them before acting."],
  ["4. Permitted and prohibited use",
    "You may use ConserveAI outputs for conservation planning, resource allocation, reporting, " +
    "and research. You may not use the system or its outputs to locate, target, or harm " +
    "wildlife, to identify individuals, or for any purpose contrary to the National Park " +
    "Service Act. ConserveAI forecasts environmental threat at park and zone level and does " +
    "not produce animal or human location data. Attempting to derive such data from its " +
    "outputs is a breach of this agreement."],
  ["5. Third-party data and attribution",
    "ConserveAI is built on free, openly licensed public data, including Open-Meteo, NASA " +
    "POWER, NASA MODIS, and Google Earth Engine. Use of the system is subject to the terms of " +
    "those providers. All sources are attributed in the project documentation. ConserveAI does " +
    "not claim ownership of the underlying environmental data."],
  ["6. Account responsibilities",
    "You are responsible for maintaining the confidentiality of your credentials. Accounts are " +
    "scoped to specific parks, and you may not attempt to access data for parks outside your " +
    "assignment. Notify the administrator of any suspected unauthorised access."],
  ["7. Limitation of liability",
    "To the extent permitted by Nigerian law, the developer accepts no liability for loss, " +
    "damage, or cost arising from reliance on ConserveAI outputs, including missed threats, " +
    "false alarms, or allocation decisions informed by its recommendations. This limitation " +
    "reflects the advisory nature of the system's outputs and is the reason clause 3 places " +
    "decision authority with the user."],
  ["8. Modification and termination",
    "These terms may be updated as the system develops. Material changes will be notified " +
    "through the application. Access may be suspended where use breaches this agreement."],
];

const PRIVACY_INTRO =
  "This policy explains what personal data ConserveAI holds, why, and what rights you have. " +
  "It is written to align with the Nigeria Data Protection Act 2023.";

const PRIVACY = [
  ["1. What we collect, and what we do not",
    "ConserveAI stores manager account information only: a username, a password stored as a " +
    "bcrypt hash, and an email address. It does not collect or store data about individuals or " +
    "communities living in or around the national parks. It does not collect location data " +
    "about people. The environmental data the system processes describes conditions in " +
    "protected areas, not persons. This is data minimisation by design: the schema holds " +
    "nothing the system does not need to authenticate a user."],
  ["2. Why we hold it",
    "Account data is processed for one purpose: authenticating users and enforcing park-scoped " +
    "access so that a manager sees the parks assigned to them. It is not used for profiling, " +
    "marketing, or any secondary purpose, and it is not sold or shared with third parties."],
  ["3. How it is protected",
    "Passwords are never stored in readable form; they are hashed using bcrypt. Access to the " +
    "application interface is controlled through JSON Web Token authentication, scoped by park. " +
    "Access controls and authentication were tested as part of the system's test suite."],
  ["4. Automated processing and your right to human oversight",
    "ConserveAI produces forecasts and recommendations using machine learning models. No " +
    "decision affecting you is made solely by automated processing. Every recommendation is " +
    "advisory, the factors driving each forecast are displayed, and a human user retains the " +
    "decision. This reflects Section 37 of the Nigeria Data Protection Act 2023, which " +
    "restricts solely automated decision-making and preserves the right to human intervention " +
    "and to contest a decision."],
  ["5. Retention",
    "Account records are retained while the account remains active and are removed when an " +
    "account is deprovisioned. Environmental data and model outputs contain no personal data " +
    "and are retained for research and evaluation."],
  ["6. Your rights",
    "Under the Nigeria Data Protection Act 2023 you may request access to the personal data " +
    "held about you, request correction of inaccurate data, request deletion of your account " +
    "data, and object to processing. Requests are handled through the system administrator."],
  ["7. Research status and ethics review",
    "ConserveAI is a Capstone research project. A Research Ethics Application was submitted to " +
    "the African Leadership University Research Ethics Committee on 16 June 2026 and is under " +
    "review. Ethical clearance will be confirmed before any pilot deployment involving park " +
    "staff or any user testing begins."],
  ["8. Contact",
    "Questions about this policy or about data held may be directed to the project developer " +
    "through the contact details published in the application."],
];

function Clauses({ items }) {
  return items.map(([heading, body]) => (
    <div key={heading} style={{ marginBottom: 18 }}>
      <Title level={5} style={{ marginBottom: 4 }}>{heading}</Title>
      <Paragraph style={{ marginBottom: 0, color: "var(--muted, #475569)" }}>{body}</Paragraph>
    </div>
  ));
}

function LegalDocument() {
  return (
    <article style={{ maxWidth: 820, margin: "0 auto" }}>
      <Title level={2} style={{ marginTop: 0 }}>Terms of Use and Privacy Policy</Title>
      <Paragraph type="secondary" style={{ marginTop: -4 }}>
        ConserveAI — a research prototype. African Leadership University Capstone, 2026.
      </Paragraph>

      <Title level={3} style={{ marginTop: 28 }}>End-User Licence Agreement</Title>
      <Paragraph italic>{EULA_INTRO}</Paragraph>
      <Clauses items={EULA} />

      <Title level={3} style={{ marginTop: 32 }}>Privacy Policy</Title>
      <Paragraph italic>{PRIVACY_INTRO}</Paragraph>
      <Clauses items={PRIVACY} />
    </article>
  );
}

export default function Legal() {
  const { user } = useAuth();
  const navigate = useNavigate();

  // Logged-in users see the document inside the normal dashboard chrome.
  if (user) {
    return (
      <AppShell subtitle="Legal">
        <LegalDocument />
      </AppShell>
    );
  }

  // Logged-out (e.g. from the login page): a clean standalone document page.
  return (
    <div style={{ minHeight: "100vh", background: "#f8fafc" }}>
      <header
        style={{
          display: "flex", alignItems: "center", gap: 12, padding: "16px 24px",
          background: "#0f3d2e", color: "#fff",
        }}
      >
        <SafetyCertificateFilled style={{ fontSize: 22, color: "#10b981" }} />
        <span style={{ fontWeight: 700, fontSize: 18, flex: 1 }}>ConserveAI</span>
        <Button ghost icon={<ArrowLeftOutlined />} onClick={() => navigate("/login")}>
          Back to login
        </Button>
      </header>
      <main style={{ padding: "32px 24px 64px" }}>
        <LegalDocument />
      </main>
    </div>
  );
}
