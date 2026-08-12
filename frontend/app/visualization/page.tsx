import { redirect } from "next/navigation";

// A supply tree is per-solution, so there is nothing to show at the bare path.
// It lands on the saved-solutions browse rather than Home: that list is the
// closest thing to an index of supply trees, and it is where someone who
// trimmed the id off the address was trying to get.
export default function Page() {
  redirect("/solutions");
}
