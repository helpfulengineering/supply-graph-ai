import { useParams } from "react-router-dom";
import { PackageListView } from "../features/package/PackageListView";
import {
  PackageDetailView,
  parsePackageRoute,
} from "../features/package/PackageDetailView";
import { ErrorMessage } from "../components/ui/ErrorMessage";

export function PackagePage() {
  const { org, project, version } = useParams();
  if (org || project || version) {
    const parsed = parsePackageRoute(org, project, version);
    if (!parsed) {
      return <ErrorMessage error={new Error("Invalid package URL")} />;
    }
    return <PackageDetailView {...parsed} />;
  }
  return <PackageListView />;
}
