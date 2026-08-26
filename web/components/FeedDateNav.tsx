import {
  formatFeedDateLabel,
  todayIstDateString,
} from "@/lib/feed-dates";
import { FEED_SORT_LATEST_OPTION, type FeedSort } from "@/lib/feed-sort";
import { Suspense } from "react";
import { CategoryFilter } from "./CategoryFilter";
import { FeedDateNavDropdown } from "./FeedDateNavDropdown";

type FeedDateNavProps = {
  basePath: string;
  dates: string[];
  selectedDate: string | null;
  selectedSort: FeedSort;
};

export function FeedDateNav({
  basePath,
  dates,
  selectedDate,
  selectedSort,
}: FeedDateNavProps) {
  const todayIst = todayIstDateString();
  const archiveDates = dates.filter((date) => date !== todayIst);

  const availableDates = new Set(dates);
  const resolvedDate =
    selectedDate && availableDates.has(selectedDate) ? selectedDate : null;

  let value = "";
  if (selectedSort === "latest") {
    value = FEED_SORT_LATEST_OPTION;
  } else if (resolvedDate && resolvedDate !== todayIst) {
    value = resolvedDate;
  }

  const options = archiveDates.map((date) => ({
    value: date,
    label: formatFeedDateLabel(date),
  }));

  return (
    <nav className="mb-6 flex flex-wrap items-center gap-2" aria-label="Browse feed">
      <FeedDateNavDropdown
        basePath={basePath}
        options={options}
        value={value}
      />
      <Suspense fallback={null}>
        <CategoryFilter />
      </Suspense>
    </nav>
  );
}
