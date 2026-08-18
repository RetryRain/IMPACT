import {
  formatFeedDateLabel,
  todayIstDateString,
} from "@/lib/feed-dates";
import { FeedDateNavDropdown } from "./FeedDateNavDropdown";

type FeedDateNavProps = {
  basePath: string;
  dates: string[];
  selectedDate: string | null;
};

export function FeedDateNav({
  basePath,
  dates,
  selectedDate,
}: FeedDateNavProps) {
  const todayIst = todayIstDateString();
  const archiveDates = dates.filter((date) => date !== todayIst);

  const availableDates = new Set(dates);
  const resolvedDate =
    selectedDate && availableDates.has(selectedDate) ? selectedDate : null;
  const value = resolvedDate === todayIst || !resolvedDate ? "" : resolvedDate;

  const options = archiveDates.map((date) => ({
    value: date,
    label: formatFeedDateLabel(date),
  }));

  return (
    <FeedDateNavDropdown
      basePath={basePath}
      options={options}
      value={value}
    />
  );
}
