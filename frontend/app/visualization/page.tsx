import { redirect } from "next/navigation";

// Supply trees are reached directly from their match; no browse list.
export default function Page() {
  redirect("/");
}
