import { CreateJsonRecordPage } from "../create/CreateJsonRecordPage";
import { createOkh, validateOkh } from "../../api/ohm/okh";

export function CreateOkhPage() {
  return (
    <CreateJsonRecordPage
      title="New design"
      listHref="/okh"
      listLabel="Designs"
      detailHref={(id) => `/okh/${id}`}
      validate={validateOkh}
      create={createOkh}
    />
  );
}
