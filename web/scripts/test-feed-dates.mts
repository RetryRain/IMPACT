import { getFeedStoryDates, getFeedStories } from "../lib/queries";

async function main() {
  const dates = await getFeedStoryDates();
  const feed = await getFeedStories(undefined, 1);
  const latestFeed = await getFeedStories(undefined, 1, null, "latest");
  console.log("dates", dates.length, dates.slice(0, 5));
  console.log("feed", feed.total, "stories in last 24h (priority)");
  console.log("latest feed", latestFeed.total, "stories in last 24h (latest sort)");
  if (dates[0]) {
    const archive = await getFeedStories(undefined, 1, dates[0]);
    console.log(`archive ${dates[0]}`, archive.total);
  }
  console.log("OK");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
