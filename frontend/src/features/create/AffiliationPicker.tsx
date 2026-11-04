"use client";

import { useEffect, useRef } from "react";
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
  const applied = useRef(false);
  useEffect(() => {
    if (applied.current || !affiliations.data) return;
    applied.current = true;
    if (affiliations.data.length === 1 && value === "") {
      onChange(affiliations.data[0].space_did);
    }
  }, [affiliations.data, onChange, value]);

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
