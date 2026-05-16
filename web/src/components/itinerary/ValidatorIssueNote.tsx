import type { ValidatorIssue } from "@/lib/types"

export function ValidatorIssueNote({ issue }: { issue: ValidatorIssue }) {
  return (
    <div
      className={`rounded-md px-3 py-2 text-sm ${
        issue.severity === "error"
          ? "bg-red-50 text-red-800"
          : "bg-amber-50 text-amber-800"
      }`}
    >
      <strong>{issue.code}</strong>: {issue.message}
      {issue.suggested_action ? ` ${issue.suggested_action}` : ""}
    </div>
  )
}
