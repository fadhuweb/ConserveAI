import { Table, Empty } from "antd";
import { fmtNGN } from "../lib/currency";

// Park-level recommended allocation: intervention, units, cost, plus the
// plain-language rationale for why the plan looks the way it does.
export default function RecommendationsTable({ recommendation }) {
  if (!recommendation) return <Empty description="Set a budget to generate a recommendation" />;

  const columns = [
    {
      title: "Intervention",
      dataIndex: "name",
      key: "name",
      render: (name, row) => (
        <div>
          <div>{name}</div>
          {row.reason && (
            <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{row.reason}</div>
          )}
        </div>
      ),
    },
    { title: "Units", dataIndex: "units", key: "units", align: "right" },
    { title: "Cost", dataIndex: "cost", key: "cost", align: "right",
      render: (c) => fmtNGN(c) },
  ];
  const data = (recommendation.allocation || []).map((a) => ({ ...a, key: a.id }));
  const rationale = recommendation.rationale;

  return (
    <>
      {rationale && (
        <div className="rec-rationale">
          <div className="rec-rationale-title">Why this plan</div>
          <p className="rec-rationale-summary">{rationale.summary}</p>
          {rationale.points?.length > 0 && (
            <ul className="rec-rationale-points">
              {rationale.points.map((p, i) => <li key={i}>{p}</li>)}
            </ul>
          )}
        </div>
      )}
      <Table columns={columns} dataSource={data} pagination={false} size="small"
        summary={() => (
          <Table.Summary.Row>
            <Table.Summary.Cell index={0}><b>Total</b></Table.Summary.Cell>
            <Table.Summary.Cell index={1} align="right">
              <b>{data.reduce((s, r) => s + r.units, 0)}</b>
            </Table.Summary.Cell>
            <Table.Summary.Cell index={2} align="right">
              <b>{fmtNGN(recommendation.total_cost)}</b>
            </Table.Summary.Cell>
          </Table.Summary.Row>
        )}
      />
    </>
  );
}
