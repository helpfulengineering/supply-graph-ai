import { CreateJsonRecordPage } from "../create/CreateJsonRecordPage";
import { createOkw, validateOkw } from "../../api/ohm/okw";

export function CreateOkwPage() {
  return (
    <CreateJsonRecordPage
      title="New facility"
      listHref="/facilities"
      listLabel="Facilities"
      detailHref={(id) => `/facilities/${id}`}
      validate={validateOkw}
      create={createOkw}
    />
  );
}
