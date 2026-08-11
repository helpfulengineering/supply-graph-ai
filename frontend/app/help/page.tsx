import type { Metadata } from "next";
import { HelpView } from "@/features/help/HelpView";

export const metadata: Metadata = {
  title: "Help",
  description:
    "Where things are, the keyboard shortcuts, and the accessibility features of Open Hardware Manager.",
};

export default function Page() {
  return <HelpView />;
}
