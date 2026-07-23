import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchOkwDetail } from "../../api/ohm/okw";
import { LoadingState, ErrorState } from "../../components/ui/states";
import { FacilityForm } from "./FacilityForm";

export function EditOkwPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["okw-detail", id],
    queryFn: () => fetchOkwDetail(id!),
    enabled: Boolean(id),
  });

  if (!id) {
    return <ErrorState title="Missing facility id." />;
  }
  if (isLoading) return <LoadingState />;
  if (isError || !data) {
    return (
      <ErrorState
        title="Failed to load facility"
        description={error instanceof Error ? error.message : undefined}
        onRetry={() => void refetch()}
      />
    );
  }

  return <FacilityForm mode="edit" facilityId={id} initialFacility={data} />;
}
