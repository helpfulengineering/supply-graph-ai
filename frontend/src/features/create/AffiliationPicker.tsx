"use client";

import { useQuery } from "@tanstack/react-query";
import { listAffiliations } from "../../api/ohm/identity";
import { LABEL } from "../../components/ui/field";

interface Props {
  value: string;
  onChange: (spaceDid: string) => void;
  disabled?: boolean;
  className?: string;
}

export function AffiliationPicker({
  value,
  onChange,
  disabled,
  className,
}: Props) {
  const affiliations = useQuery({
    queryKey: ["identity", "affiliations"],
    queryFn: listAffiliations,
  });

  return (
    <label className={LABEL}>
      On behalf of
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className={className}
      >
        <option value="">None</option>
        {(affiliations.data ?? []).map((row) => (
          <option key={row.space_did} value={row.space_did}>
            {row.display_name}
          </option>
        ))}
      </select>
    </label>
  );
}
