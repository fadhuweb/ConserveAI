import { useEffect, useState } from "react";
import { Card, Table, Tag, Button, Modal, Form, Input, Select, Alert } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import AppShell from "../components/AppShell";
import { listUsers, createUser } from "../api/auth";
import { getParks } from "../api/forecasts";

export default function Managers() {
  const [users, setUsers] = useState([]);
  const [parks, setParks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState("");
  const [form] = Form.useForm();

  const load = () => {
    setLoading(true);
    Promise.all([listUsers(), getParks()])
      .then(([u, p]) => { setUsers(u); setParks(p); })
      .catch(() => {})
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const onCreate = async (vals) => {
    setBusy(true);
    try {
      await createUser({ ...vals, username: vals.full_name });
      setResult(`Account created — a temporary password was emailed to ${vals.email}. The manager sets their own password on first login.`);
      form.resetFields();
      setOpen(false);
      load();
    } catch (e) {
      Modal.error({ title: "Could not create account", content: e?.response?.data?.detail || "Something went wrong." });
    } finally {
      setBusy(false);
    }
  };

  const columns = [
    { title: "Username", dataIndex: "username", key: "username", render: (v) => <b>{v}</b> },
    { title: "Name", dataIndex: "full_name", key: "name", render: (v) => v || <span className="muted">—</span> },
    { title: "Email", dataIndex: "email", key: "email", render: (v) => v || <span className="muted">—</span> },
    { title: "Role", dataIndex: "role", key: "role",
      render: (r) => <Tag color={r === "admin" ? "gold" : "green"}>{r}</Tag> },
    { title: "Park", dataIndex: "park_id", key: "park",
      render: (v) => v ? (parks.find((p) => p.id === v)?.display_name || v) : <span className="muted">all parks</span> },
    { title: "Status", dataIndex: "must_change_password", key: "status",
      render: (m) => m ? <Tag color="orange">Pending first login</Tag> : <Tag color="green">Active</Tag> },
  ];

  return (
    <AppShell subtitle="Park Managers">
      {result && (
        <Alert type="success" message={result} showIcon closable
          style={{ marginBottom: 16, borderRadius: 12 }} onClose={() => setResult("")} />
      )}

      <Card
        title="Accounts"
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Add manager</Button>}
      >
        <Table rowKey="id" columns={columns} dataSource={users} loading={loading} pagination={false} />
      </Card>

      <Modal
        title="Add park manager"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={busy}
        okText="Add &amp; email password"
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={onCreate} requiredMark={false} initialValues={{ role: "manager" }}>
          <Form.Item label="Full name" name="full_name" rules={[{ required: true, message: "Enter the manager's name" }]}>
            <Input placeholder="e.g. Aisha Bello" />
          </Form.Item>
          <Form.Item label="Email" name="email" rules={[{ required: true, type: "email", message: "Enter a valid email" }]}>
            <Input placeholder="e.g. aisha@parks.gov.ng" />
          </Form.Item>
          <Form.Item label="Role" name="role">
            <Select options={[{ value: "manager", label: "Park Manager" }, { value: "admin", label: "Administrator" }]} />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.role !== cur.role}>
            {({ getFieldValue }) => getFieldValue("role") !== "admin" && (
              <Form.Item label="Park" name="park_id" rules={[{ required: true, message: "Select the manager's park" }]}>
                <Select placeholder="Select a park" options={parks.map((p) => ({ value: p.id, label: p.display_name }))} />
              </Form.Item>
            )}
          </Form.Item>
          <Form.Item label="Phone number" name="phone" rules={[
            { required: true, message: "Enter a phone number" },
            { pattern: /^(\+234|0)[7-9][0-1]\d{8}$/, message: "Enter a valid Nigerian number (e.g. 08012345678 or +2348012345678)" },
          ]}>
            <Input placeholder="e.g. 08012345678" />
          </Form.Item>
        </Form>
      </Modal>
    </AppShell>
  );
}
