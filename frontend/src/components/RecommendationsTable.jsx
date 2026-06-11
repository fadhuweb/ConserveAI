import { Table, Empty } from "antd";
import { fmtNGN } from "../lib/currency";

// Park-level recommended allocation: intervention, units, cost.
export default function RecommendationsTable({ recommendation }) {
  if (!recommendation) return <Empty description="Set a budget to generate a recommendation" />;

  const columns = [
    { title: "Intervention", dataIndex: "name", key: "name" },
    { title: "Units", dataIndex: "units", key: "units", align: "right" },
    { title: "Cost", dataIndex: "cost", key: "cost", align: "right",
      render: (c) => fmtNGN(c) },
  ];
  const data = (recommendation.allocation || []).map((a) => ({ ...a, key: a.id }));

  return (
    <>
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
